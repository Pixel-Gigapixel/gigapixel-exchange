<?php
declare(strict_types=1);
namespace Gigapixel\Visualsearch\Service;

use Gigapixel\Visualsearch\Domain\Model\SearchResult;
use TYPO3\CMS\Core\Database\ConnectionPool;
use TYPO3\CMS\Core\Log\LogManager;
use TYPO3\CMS\Core\Utility\GeneralUtility;

class KeSearchAdapter
{
    private const TABLE      = 'tx_cartgigapixels_domain_model_gigapixel';
    private const TRANS_TABLE = 'tx_gigapixels_translation';
    private const TRANS_SRC  = 'tx_cartgigapixels_domain_model_gigapixel';

    public function __construct(
        private readonly ConnectionPool $connectionPool
    ) {}

    public function searchByText(string $query, float $threshold = 0.0, int $languageId = 0): array
    {
        $q = trim($query);
        if ($q === '') return [];

        $conn = $this->connectionPool->getConnectionForTable(self::TABLE);

        $kwField   = $languageId !== 0 ? 'ai_keywords_en'    : 'ai_keywords_de';
        $descField = $languageId !== 0 ? 'ai_description_en' : 'ai_description_de';

        $langCode = match($languageId) { 2 => 'fr', 3 => 'ru', 4 => 'es', 5 => 'tr', 6 => 'pl', 7 => 'it', default => null };
        $hasTrans = $langCode !== null;

        // Split into individual words, ignore stopwords shorter than 2 chars
        $words = array_values(array_filter(
            preg_split('/\s+/', mb_strtolower($q)),
            fn(string $w) => mb_strlen($w) >= 2
        ));
        if (empty($words)) return [];
        $words = array_slice($words, 0, 5); // cap at 5 words to limit SQL size

        $params     = [];
        $scoreParts = [];
        $whereParts = [];

        foreach ($words as $i => $word) {
            $escaped        = str_replace(['\\', '%', '_'], ['\\\\', '\%', '\_'], $word);
            $like           = '%' . $escaped . '%';
            $params["wl$i"] = $like;
            $params["ww$i"] = $word;

            // Base DE/EN fields
            $score = "(CASE WHEN LOWER(g.title)          LIKE :wl$i THEN 5 ELSE 0 END)"
                   . " + (CASE WHEN g.keywords REGEXP CONCAT('[[:<:]]', :ww$i, '[[:>:]]') THEN 5 ELSE 0 END)"
                   . " + (CASE WHEN LOWER(g.keywords)    LIKE :wl$i THEN 2 ELSE 0 END)"
                   . " + (CASE WHEN g.$kwField REGEXP CONCAT('[[:<:]]', :ww$i, '[[:>:]]') THEN 4 ELSE 0 END)"
                   . " + (CASE WHEN g.$kwField            LIKE :wl$i THEN 1 ELSE 0 END)"
                   . " + (CASE WHEN LOWER(g.$descField)  LIKE :wl$i THEN 2 ELSE 0 END)"
                   . " + ROUND((CHAR_LENGTH(g.$descField)"
                   . "          - CHAR_LENGTH(REPLACE(LOWER(g.$descField), :ww$i, '')))"
                   . "         / GREATEST(CHAR_LENGTH(:ww$i), 1))";

            // Translated fields (FR/RU) — higher weight for exact-language match
            if ($hasTrans) {
                $score .= " + (CASE WHEN t_title.value IS NOT NULL AND LOWER(t_title.value) LIKE :wl$i THEN 6 ELSE 0 END)"
                        . " + (CASE WHEN t_kw.value    IS NOT NULL AND LOWER(t_kw.value)    LIKE :wl$i THEN 4 ELSE 0 END)"
                        . " + (CASE WHEN t_desc.value  IS NOT NULL AND LOWER(t_desc.value)  LIKE :wl$i THEN 3 ELSE 0 END)"
                        . " + ROUND((CHAR_LENGTH(COALESCE(t_desc.value, ''))"
                        . "          - CHAR_LENGTH(REPLACE(LOWER(COALESCE(t_desc.value, '')), :ww$i, '')))"
                        . "         / GREATEST(CHAR_LENGTH(:ww$i), 1))";
            }

            $scoreParts[] = $score;

            // AND-logic: every word must appear in at least one field
            $where = "(LOWER(g.title) LIKE :wl$i"
                   . " OR LOWER(g.keywords) LIKE :wl$i"
                   . " OR g.$kwField LIKE :wl$i"
                   . " OR LOWER(g.$descField) LIKE :wl$i";
            if ($hasTrans) {
                $where .= " OR (t_title.value IS NOT NULL AND LOWER(t_title.value) LIKE :wl$i)"
                        . " OR (t_kw.value    IS NOT NULL AND LOWER(t_kw.value)    LIKE :wl$i)"
                        . " OR (t_desc.value  IS NOT NULL AND LOWER(t_desc.value)  LIKE :wl$i)";
            }
            $where       .= ")";
            $whereParts[] = $where;
        }

        // Phrase bonus when all words appear consecutively
        $escapedPhrase    = str_replace(['\\', '%', '_'], ['\\\\', '\%', '\_'], mb_strtolower($q));
        $params['phrase'] = '%' . $escapedPhrase . '%';

        if ($hasTrans) {
            $phraseBonus = "(CASE"
                         . " WHEN (LOWER(g.title) LIKE :phrase"
                         . "    OR (t_title.value IS NOT NULL AND LOWER(t_title.value) LIKE :phrase)) THEN 10"
                         . " WHEN (LOWER(g.keywords) LIKE :phrase"
                         . "    OR (t_kw.value IS NOT NULL AND LOWER(t_kw.value) LIKE :phrase)) THEN 8"
                         . " WHEN (LOWER(g.$descField) LIKE :phrase"
                         . "    OR (t_desc.value IS NOT NULL AND LOWER(t_desc.value) LIKE :phrase)) THEN 5"
                         . " ELSE 0 END)";
        } else {
            $phraseBonus = "(CASE WHEN LOWER(g.title)    LIKE :phrase THEN 10"
                         . " WHEN LOWER(g.keywords)      LIKE :phrase THEN 8"
                         . " WHEN LOWER(g.$descField)    LIKE :phrase THEN 5 ELSE 0 END)";
        }

        $relevanceExpr = '(' . implode(' + ', $scoreParts) . ' + ' . $phraseBonus . ')';
        $whereExpr     = implode(' AND ', $whereParts);

        // LEFT JOINs to tx_gigapixels_translation for FR/RU
        $joinSql    = '';
        $descSelect = "g.$descField AS description_lang";
        if ($hasTrans) {
            $params['trans_lang'] = $langCode;
            $src                  = self::TRANS_SRC;
            $tt                   = self::TRANS_TABLE;
            $joinSql    = " LEFT JOIN $tt t_title ON t_title.source_table='$src'"
                        . "   AND t_title.source_uid=g.uid AND t_title.field='title' AND t_title.language=:trans_lang"
                        . " LEFT JOIN $tt t_kw    ON t_kw.source_table='$src'"
                        . "   AND t_kw.source_uid=g.uid    AND t_kw.field='keywords'   AND t_kw.language=:trans_lang"
                        . " LEFT JOIN $tt t_desc  ON t_desc.source_table='$src'"
                        . "   AND t_desc.source_uid=g.uid  AND t_desc.field='description' AND t_desc.language=:trans_lang";
            $descSelect = "COALESCE(t_desc.value, g.$descField) AS description_lang";
        }

        $sql = "SELECT g.uid, $descSelect, g.ai_scene_type, g.ai_primary_subject, g.path_segment,
                    g.photographer, g.format_width, g.format_height, g.format_file,
                    $relevanceExpr AS relevance
                FROM " . self::TABLE . " g"
             . $joinSql . "
                WHERE g.deleted = 0 AND g.hidden = 0
                  AND ($whereExpr)
                ORDER BY relevance DESC, g.uid DESC
                LIMIT 200";

        try {
            $rows = $conn->executeQuery($sql, $params)->fetchAllAssociative();
        } catch (\Throwable $e) {
            GeneralUtility::makeInstance(LogManager::class)
                ->getLogger(__CLASS__)
                ->warning('KeSearchAdapter::searchByText DB error: ' . $e->getMessage());
            return [];
        }

        if (empty($rows)) return [];

        $maxRel = (float)max(array_column($rows, 'relevance'));
        if ($maxRel <= 0.0) return [];

        return array_map(
            fn(array $r) => new SearchResult(
                uid:                (int)$r['uid'],
                score:              (float)$r['relevance'] / $maxRel,
                source:             'keyword',
                data:               [
                    'description'    => (string)($r['description_lang']   ?? ''),
                    'scene_type'     => (string)($r['ai_scene_type']       ?? ''),
                    'primary_subject'=> (string)($r['ai_primary_subject']  ?? ''),
                    'path_segment'   => (string)($r['path_segment']        ?? ''),
                    'photographer'   => (string)($r['photographer']        ?? ''),
                    'format_width'   => (int)($r['format_width']           ?? 0),
                    'format_height'  => (int)($r['format_height']          ?? 0),
                    'format_file'    => (string)($r['format_file']         ?? ''),
                ],
                imageCosineScore:   0.0,
                textRelevanceScore: (float)$r['relevance'] / $maxRel,
            ),
            $rows
        );
    }
}

<?php
declare(strict_types=1);
namespace Gigapixel\Visualsearch\Service;

use Gigapixel\Visualsearch\Domain\Model\SearchResult;
use TYPO3\CMS\Core\Database\ConnectionPool;
use TYPO3\CMS\Core\Utility\GeneralUtility;

class EmbeddingSearchService
{
    private const TABLE = 'tx_cartgigapixels_domain_model_gigapixel';
    private const BATCH = 500;
    private const DIM   = 1024;

    public function searchByEmbedding(array $queryEmb, float $threshold, string $source, int $languageId = 0): array
    {
        @ini_set('memory_limit', '256M');

        $conn   = GeneralUtility::makeInstance(ConnectionPool::class)
            ->getConnectionForTable(self::TABLE);
        $scored = [];
        $offset = 0;

        try {
        while (true) {
            $rows = $conn->executeQuery(
                'SELECT uid, ai_image_embedding, ai_description_de, ai_description_en,
                        ai_scene_type, ai_primary_subject, path_segment, title,
                        photographer, format_width, format_height, format_file
                   FROM ' . self::TABLE . '
                  WHERE deleted=0 AND ai_index_status=2 AND ai_image_embedding IS NOT NULL
                  LIMIT ' . self::BATCH . ' OFFSET ' . $offset
            )->fetchAllAssociative();

            if (!$rows) break;

            foreach ($rows as $row) {
                $iv  = array_values(unpack('f*', $row['ai_image_embedding']));
                $dot = $na = $nb = 0.0;
                for ($i = 0; $i < self::DIM; $i++) {
                    $dot += $queryEmb[$i] * $iv[$i];
                    $na  += $queryEmb[$i] ** 2;
                    $nb  += $iv[$i] ** 2;
                }
                unset($iv);
                $score = ($na && $nb) ? $dot / sqrt($na * $nb) : 0.0;
                if ($score >= $threshold) {
                    $desc = $languageId !== 0
                        ? (string)($row['ai_description_en'] ?: $row['ai_description_de'] ?? '')
                        : (string)($row['ai_description_de'] ?? '');
                    $scored[] = new SearchResult(
                        (int)$row['uid'], $score, $source,
                        [
                            'description'    => $desc,
                            'scene_type'     => (string)($row['ai_scene_type']      ?? ''),
                            'primary_subject'=> (string)($row['ai_primary_subject'] ?? ''),
                            'path_segment'   => (string)($row['path_segment']       ?? ''),
                            'title'          => (string)($row['title']              ?? ''),
                            'photographer'   => (string)($row['photographer']       ?? ''),
                            'format_width'   => (int)($row['format_width']          ?? 0),
                            'format_height'  => (int)($row['format_height']         ?? 0),
                            'format_file'    => (string)($row['format_file']        ?? ''),
                        ],
                        $source === 'image' ? $score : 0.0,
                        $source === 'text'  ? $score : 0.0,
                    );
                }
            }

            unset($rows);
            $offset += self::BATCH;
            if ($offset % 2000 === 0) gc_collect_cycles();
        }
        } catch (\Throwable) {
            return [];
        }

        usort($scored, fn($a, $b) => $b->score <=> $a->score);
        return $scored;
    }

    public function enrichLocalizedData(array $results, int $languageId): void
    {
        $langCode = match($languageId) {
            2 => 'fr',
            3 => 'ru',
            4 => 'es',
            default => null,
        };
        if ($langCode === null || empty($results)) return;

        $uids = array_map(fn($r) => $r->uid, $results);
        $conn = GeneralUtility::makeInstance(ConnectionPool::class)
            ->getConnectionForTable('tx_gigapixels_translation');

        $rows = $conn->executeQuery(
            'SELECT source_uid, field, value
               FROM tx_gigapixels_translation
              WHERE source_table = ?
                AND source_uid IN (' . implode(',', $uids) . ')
                AND language = ?
                AND field IN (\'description\', \'title\')',
            ['tx_cartgigapixels_domain_model_gigapixel', $langCode]
        )->fetchAllAssociative();

        $byUid = [];
        foreach ($rows as $row) {
            $byUid[(int)$row['source_uid']][$row['field']] = $row['value'];
        }

        foreach ($results as $r) {
            $trans = $byUid[$r->uid] ?? [];
            if (!empty($trans['description'])) {
                $r->data['description'] = $trans['description'];
            }
            if (!empty($trans['title'])) {
                $r->data['primary_subject'] = $trans['title'];
            }
        }
    }

    public function getEmbeddingByUid(int $uid): ?array
    {
        $conn = GeneralUtility::makeInstance(ConnectionPool::class)
            ->getConnectionForTable(self::TABLE);
        try {
            $row = $conn->executeQuery(
                'SELECT ai_image_embedding FROM ' . self::TABLE .
                ' WHERE uid = ? AND deleted = 0 AND ai_image_embedding IS NOT NULL',
                [$uid]
            )->fetchAssociative();
        } catch (\Throwable) {
            return null;
        }
        if (!$row || !$row['ai_image_embedding']) return null;
        return array_values(unpack('f*', $row['ai_image_embedding']));
    }

    public function enrichImageUrls(array $results): void
    {
        if (!$results) return;
        $uids = implode(',', array_map(fn($r) => (int)$r->uid, $results));
        $conn = GeneralUtility::makeInstance(ConnectionPool::class)
            ->getConnectionForTable('sys_file_reference');
        $rows = $conn->executeQuery(
            "SELECT sfr.uid_foreign AS uid, sf.uid AS file_uid, sf.identifier
               FROM sys_file_reference sfr
               JOIN sys_file sf ON sf.uid = sfr.uid_local
              WHERE sfr.uid_foreign IN ($uids)
                AND sfr.tablenames = '" . self::TABLE . "'
                AND sfr.fieldname='image' AND sfr.deleted=0"
        )->fetchAllAssociative();
        $paths    = [];
        $fileUids = [];
        foreach ($rows as $row) {
            $paths[(int)$row['uid']]    = '/fileadmin' . $row['identifier'];
            $fileUids[(int)$row['uid']] = (int)$row['file_uid'];
        }
        foreach ($results as $result) {
            $result->imgUrl  = $paths[$result->uid]    ?? '';
            $result->fileUid = $fileUids[$result->uid] ?? 0;
        }
    }
}

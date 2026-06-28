<?php
declare(strict_types=1);
namespace Datenglueck\CartGigapixels\Command;

use Datenglueck\CartGigapixels\Domain\Repository\TranslationRepository;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Input\InputOption;
use Symfony\Component\Console\Output\OutputInterface;
use TYPO3\CMS\Core\Utility\GeneralUtility;

/**
 * Scheduler-compatible command: translate Gigapixel records into the store.
 *
 * Finds records where title or keywords have no translation or the source changed
 * (MD5 mismatch). Translates via Anthropic API, writes to tx_gigapixels_translation.
 *
 * Usage:
 *   vendor/bin/typo3 gigapixels:translate --language=en --limit=200
 *   vendor/bin/typo3 gigapixels:translate --language=fr --limit=100
 *   vendor/bin/typo3 gigapixels:translate --language=en --dry-run
 *
 * Positional mapping: UIDs are NEVER sent to or expected from the model.
 * The code keeps the ordered uid list per batch and zips output lines by index.
 * Hard validation: output line count must equal input line count; on mismatch the
 * batch retries record-by-record. This prevents any uid misassignment regardless
 * of model behaviour.
 */
#[AsCommand(
    name: 'gigapixels:translate',
    description: 'Translate Gigapixel title/keywords into tx_gigapixels_translation',
)]
class TranslateRecordsCommand extends Command
{
    private const GP_TABLE    = 'tx_cartgigapixels_domain_model_gigapixel';
    private const BATCH_TITLE = 60;
    private const BATCH_KW    = 12;

    // ── Prompts ───────────────────────────────────────────────────────────────

    private const PROMPT_TITLE = <<<'PROMPT'
You translate German gigapixel photo titles into English for a professional image library.
One German title per input line — output exactly one English title per line, in the SAME ORDER.
Do NOT add line numbers, prefixes, explanations, or extra lines. One output line per input line.

Rules (STRICTLY follow):
1. "freigestellt" → "cut-out" (never "isolated").
2. Pure proper nouns / landmarks (Schloss X, Asamkirche, Burj Khalifa, bank/institution names)
   with NO generic German words around them → output the single word EMPTY.
3. Mixed titles: keep proper noun unchanged, translate ALL surrounding German words.
4. Geographic words: translate (Irland→Ireland, München→Munich, etc.)
   BUT keep place names unchanged (Tegernsee, Neuschwanstein, Karwendel, Ahornboden stay as-is).
5. "aus der Nähe"→"close-up", "Fernsicht"→"distant view", "Detailansicht der/des"→"Detail view of",
   "Vergrößerung"→"close-up", "Innenansicht"→"interior view", "Außenansicht"→"exterior view",
   "Baumgruppe"→"group of trees", "Ziegelwand"→"brick wall", "Fugen"→"mortar joints".
6. NEVER correct typos. If German input is empty → output EMPTY.
PROMPT;

    private const PROMPT_TITLE_FR = <<<'PROMPT'
You translate German gigapixel photo titles into French for a professional image library.
Each input line has format:  German title || English title
The English title is provided as reference context only — translate the GERMAN into French.
Output exactly one French title per input line, in the SAME ORDER.
Do NOT add line numbers, prefixes, explanations, or extra lines. One output line per input line.

Rules (STRICTLY follow):
1. Translate the GERMAN title into French.
2. If the English title is EMPTY, the German is a pure proper noun → output the single word EMPTY.
3. "freigestellt" → "découpé" (never "isolé").
4. Pure proper nouns / landmarks with NO surrounding descriptive German words → output EMPTY.
5. Mixed titles: keep proper nouns unchanged, translate surrounding words into French.
6. Geographic: Bayern→Bavière, Deutschland→Allemagne, Österreich→Autriche, München→Munich.
   BUT keep place names as-is: Tegernsee, Karwendel, Ahornboden, Zugspitze.
7. "Außenansicht"→"vue extérieure", "Innenansicht"→"vue intérieure", "Nahaufnahme"→"gros plan",
   "Fernsicht"→"vue lointaine", "Detailansicht"→"vue détaillée", "Baumgruppe"→"groupe d'arbres".
8. NEVER correct typos. If German title is empty → output EMPTY.
PROMPT;

    private const PROMPT_KW = <<<'PROMPT'
Translate photography keywords to English. One record per input line.

Input:  German keywords per line (comma- or space-separated)
Output: English keywords per line, comma-separated — one output line per input line, SAME ORDER.
Do NOT add line numbers, prefixes, explanations, extra lines, or blank lines between records.

Rules — follow exactly:
1. Each output term = ONE word or ONE fixed compound. Never paraphrase or add extra words.
   Bad: "Baum" → "a large tree"   Good: "Baum" → "tree"
2. Skip pure numbers, IDs, or gibberish tokens (e.g. "542674").
3. Proper nouns, place names, brand names → keep unchanged
   (Ahornboden, Karwendel, BMW, Zugspitze, etc.).
4. Geographic common nouns → translate (Bayern→Bavaria, Deutschland→Germany,
   München→Munich, Österreich→Austria).
5. "freigestellt"→"cut-out", "Nahaufnahme"→"close-up", "Weitwinkel"→"wide-angle",
   "menschenleer"→"deserted", "Spanndecke"→"suspended ceiling".
6. Do NOT correct typos. Do NOT add or invent terms not present in the source.
7. If a token is already English (and not garbled), keep it as-is.
PROMPT;

    private const PROMPT_KW_FR = <<<'PROMPT'
Translate photography keywords to French. One record per input line.

Input format:  DE keywords || EN keywords
Output: French keywords, comma-separated — one output line per input line, SAME ORDER.
Do NOT add line numbers, prefixes, explanations, extra lines, or blank lines between records.

Rules — follow exactly:
1. Translate each GERMAN keyword to French as ONE term or fixed compound.
2. Use the English keywords as anchor: if a German term is unclear, the English confirms it.
   CRITICAL: output must be FRENCH — no English words in the result.
3. Input terms may be space- or comma-separated; output is ALWAYS comma-separated.
4. Each output term = ONE word or fixed compound. No paraphrasing.
5. "freigestellt"→"découpé", "Nahaufnahme"→"gros plan", "Weitwinkel"→"grand angle",
   "menschenleer"→"désert", "Spanndecke"→"plafond tendu", "Baumkrone"→"cime d'arbre".
6. Proper nouns, place names, brands → keep unchanged (Ahornboden, BMW, Karwendel).
7. Geographic common nouns → translate (Bayern→Bavière, Deutschland→Allemagne,
   München→Munich, Österreich→Autriche, Schweiz→Suisse, Wien→Vienne).
8. Deduplicate: if translation of two terms collides, keep only one.
9. Do NOT correct typos. Do NOT add or invent terms.
PROMPT;

    private const PROMPT_TITLE_RU = <<<'PROMPT'
You translate German gigapixel photo titles into Russian for a professional image library.
Each input line has format:  German title || English title
The English title is provided as reference context only — translate the GERMAN into Russian.
Output exactly one Russian title per input line, in the SAME ORDER.
Do NOT add line numbers, prefixes, explanations, or extra lines. One output line per input line.

Rules (STRICTLY follow):
1. Translate the GERMAN title into Russian.
2. If the English title is EMPTY, the German is a pure proper noun → output the single word EMPTY.
3. "freigestellt" → "на белом фоне" (never "изолированный").
4. Pure proper nouns / landmarks with NO surrounding descriptive German words → output EMPTY.
5. Mixed titles: keep proper nouns unchanged (transliterate only if standard Russian exists),
   translate surrounding words into Russian.
6. Geographic: Bayern→Бавария, Deutschland→Германия, Österreich→Австрия, München→Мюнхен,
   Irland→Ирландия, Berlin→Берлин, Wien→Вена. Keep place names as-is: Tegernsee, Karwendel, Ahornboden, Zugspitze, Dingle, Conor Pass, Dubai.
7. "Außenansicht"→"вид снаружи", "Innenansicht"→"вид изнутри", "Nahaufnahme"→"крупный план",
   "Fernsicht"→"дальний вид", "Detailansicht"→"детальный вид", "Baumgruppe"→"группа деревьев",
   "Ziegelwand"→"кирпичная стена".
8. NEVER correct typos. If German title is empty → output EMPTY.
PROMPT;

    private const PROMPT_KW_RU = <<<'PROMPT'
Translate photography keywords to Russian. One record per input line.

Input format:  DE keywords || EN keywords
Output: Russian keywords, comma-separated — one output line per input line, SAME ORDER.
Do NOT add line numbers, prefixes, explanations, extra lines, or blank lines between records.

Rules — follow exactly:
1. Translate each GERMAN keyword to Russian as ONE term or fixed compound.
2. Use the English keywords as anchor: if a German term is unclear, the English confirms it.
   CRITICAL: output must be RUSSIAN — no German or English words in the result.
3. Input terms may be space- or comma-separated; output is ALWAYS comma-separated.
4. Each output term = ONE word or fixed compound (2–3 words max). No paraphrasing.
5. "freigestellt"→"на белом фоне", "Nahaufnahme"→"крупный план", "Weitwinkel"→"широкий угол",
   "menschenleer"→"безлюдный", "Spanndecke"→"натяжной потолок", "Baumkrone"→"крона дерева".
6. Proper nouns, place names, brands → keep in original Latin script (Ahornboden, BMW, Karwendel).
7. Geographic common nouns → translate to Russian (Bayern→Бавария, Deutschland→Германия,
   München→Мюнхен, Österreich→Австрия, Schweiz→Швейцария, Wien→Вена, Irland→Ирландия).
8. Deduplicate: if translation of two terms collides, keep only one.
9. Do NOT correct typos. Do NOT add or invent terms.
PROMPT;

    private const PROMPT_TITLE_ES = <<<'PROMPT'
You translate German gigapixel photo titles into Spanish for a professional image library.
Each input line has format:  German title || English title
The English title is reference context only — translate the GERMAN into Spanish.
Output exactly one Spanish title per input line, in the SAME ORDER.
Do NOT add line numbers, prefixes, explanations, or extra lines. One output line per input line.

Rules (STRICTLY follow):
1. Translate the GERMAN title into Spanish.
2. EMPTY rule — output the single word EMPTY ONLY when BOTH conditions hold:
   (a) the English reference is empty, AND
   (b) the German title is a SINGLE proper noun / place name with NO article, preposition or common noun.
   The English reference is the PRIMARY signal: if it is non-empty, the title is descriptive → ALWAYS translate.
3. "freigestellt" → "recortado" (never "aislado").
4. If EITHER signal points to descriptive content — English reference non-empty, OR the German contains any
   article/preposition/common noun (der/die/das/ein/eine/in/im/am/an/bei/von/vor/auf + Kirche/Dom/Schloss/
   Schiff/Brücke/Platz/Ort/Gebiet/Wand/Baum/Moschee/Galerie/Kathedrale…) — TRANSLATE, never EMPTY. When in doubt, translate.
5. Mixed titles: keep proper nouns unchanged, translate surrounding words into Spanish.
6. Geographic: Bayern→Baviera, Deutschland→Alemania, Österreich→Austria, München→Múnich,
   Schweiz→Suiza, Wien→Viena. BUT keep place names as-is: Tegernsee, Karwendel, Ahornboden, Zugspitze.
7. "Außenansicht"→"vista exterior", "Innenansicht"→"vista interior", "Nahaufnahme"→"primer plano",
   "Fernsicht"→"vista lejana", "Detailansicht"→"vista detallada", "Baumgruppe"→"grupo de árboles".
8. Terminology: generic noun "gigapíxel" (lowercase, with accent); brand/company "Gigapixel" capitalized.
   At the start of a title, capitalize the initial letter but keep the accent ("Gigapíxel…").
   "KI" → "IA". NEVER conflate PPI and DPI. Gigapixel photography = panorama photography
   (fotografía panorámica) where the term appears.
9. NEVER correct typos. If German title is empty → output EMPTY.
PROMPT;

    private const PROMPT_KW_ES = <<<'PROMPT'
Translate photography keywords to Spanish. One record per input line.

Input format:  DE keywords || EN keywords
Output: Spanish keywords, comma-separated — one output line per input line, SAME ORDER.
Do NOT add line numbers, prefixes, explanations, extra lines, or blank lines between records.

Rules — follow exactly:
1. Translate each GERMAN keyword to Spanish as ONE term or fixed compound (SEO-suitable).
2. Use the English keywords as anchor: if a German term is unclear, the English confirms it.
   CRITICAL: output must be SPANISH — no German or English words in the result.
3. Input terms may be space- or comma-separated; output is ALWAYS comma-separated.
4. Each output term = ONE word or fixed compound. No paraphrasing.
5. "freigestellt"→"recortado", "Nahaufnahme"→"primer plano", "Weitwinkel"→"gran angular",
   "menschenleer"→"despoblado", "Spanndecke"→"techo tensado", "Baumkrone"→"copa de árbol".
6. Proper nouns, place names, brands → keep unchanged (Ahornboden, BMW, Karwendel).
7. Geographic common nouns → translate (Bayern→Baviera, Deutschland→Alemania, München→Múnich,
   Österreich→Austria, Schweiz→Suiza, Wien→Viena).
8. Terminology: generic "gigapíxel" (lowercase, accent); brand "Gigapixel" capitalized. "KI"→"IA". PPI≠DPI.
9. Deduplicate: if translation of two terms collides, keep only one.
10. Do NOT correct typos. Do NOT add or invent terms.
11. Output count must NOT exceed the input keyword count. NEVER pad a short list with unrelated terms —
    every output term must derive from an input keyword. A short DE list yields a short ES list
    (after dedup possibly fewer, never more). Do not introduce themes absent from the input.
PROMPT;

    // ── Configuration ─────────────────────────────────────────────────────────

    protected function configure(): void
    {
        $this
            ->addOption('language', 'l', InputOption::VALUE_REQUIRED, 'Target language code', 'en')
            ->addOption('limit',    null, InputOption::VALUE_REQUIRED, 'Records per run (per field)', '200')
            ->addOption('fields',   null, InputOption::VALUE_REQUIRED, 'Comma-separated fields to process', 'title,keywords')
            ->addOption('force',    null, InputOption::VALUE_NONE,     'Re-translate even if source_hash matches')
            ->addOption('dry-run',  null, InputOption::VALUE_NONE,     'Show what would be written');
    }

    // ── Execute ───────────────────────────────────────────────────────────────

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $language = (string)$input->getOption('language');
        $limit    = (int)$input->getOption('limit');
        $dryRun   = (bool)$input->getOption('dry-run');
        $force    = (bool)$input->getOption('force');
        $fields   = array_filter(array_map('trim', explode(',', (string)$input->getOption('fields'))));

        $apiKey = $this->resolveApiKey();
        if ($apiKey === '') {
            $output->writeln('<error>No ANTHROPIC_API_KEY found (env or ~/.anthropic-api-key)</error>');
            return Command::FAILURE;
        }

        /** @var TranslationRepository $repo */
        $repo = GeneralUtility::makeInstance(TranslationRepository::class);

        $untranslated = $repo->findUntranslatedGigapixels($fields, $language, $limit, $force);
        $output->writeln(sprintf('Found %d record-field pairs to translate.', count($untranslated)));

        if (empty($untranslated)) {
            $output->writeln('Everything up to date.');
            return Command::SUCCESS;
        }

        $titleItems = array_values(array_filter($untranslated, fn($r) => $r['field'] === 'title'));
        $kwItems    = array_values(array_filter($untranslated, fn($r) => $r['field'] === 'keywords'));

        // For non-EN: load EN store values once as dual-source anchor
        $enCtrl = [];
        if ($language !== 'en') {
            foreach ($untranslated as $rec) {
                $en = $repo->get(self::GP_TABLE, (int)$rec['uid'], $rec['field'], 'en');
                $enCtrl[$rec['uid']][$rec['field']] = $en ?? '';
            }
        }

        $titlePrompt = match ($language) {
            'en'    => self::PROMPT_TITLE,
            'ru'    => self::PROMPT_TITLE_RU,
            'es'    => self::PROMPT_TITLE_ES,
            default => self::PROMPT_TITLE_FR,
        };
        $kwPrompt = match ($language) {
            'en'    => self::PROMPT_KW,
            'ru'    => self::PROMPT_KW_RU,
            'es'    => self::PROMPT_KW_ES,
            default => self::PROMPT_KW_FR,
        };

        $written = 0;

        // ── Title batches ──────────────────────────────────────────────────
        foreach (array_chunk($titleItems, self::BATCH_TITLE) as $batch) {
            $toApi     = [];
            $extracted = []; // uid → value (bilingual fast-path, EN only)

            if ($language === 'en') {
                foreach ($batch as $rec) {
                    $en = $this->extractBilingual($rec['source_value']);
                    if ($en !== null) {
                        $extracted[(int)$rec['uid']] = $en;
                    } else {
                        $toApi[] = $rec;
                    }
                }
            } else {
                $toApi = $batch;
            }

            $apiResults = [];
            if ($toApi) {
                $uids       = array_map('intval', array_column($toApi, 'uid'));
                $inputLines = array_map(
                    fn($r) => $this->buildInputLine($r, $language, $enCtrl, 'title'),
                    $toApi
                );
                $apiResults = $this->callDelimited($apiKey, $titlePrompt, $inputLines, $uids, 6000, $output);
            }

            $merged = $extracted + $apiResults; // + preserves integer uid keys; array_merge would re-index
            $srcMap = array_column($batch, 'source_value', 'uid');

            foreach ($merged as $uid => $value) {
                $value = ($value === 'EMPTY') ? '' : $value;
                $output->writeln(
                    sprintf('  [title] %5d | %s', $uid, mb_substr($value, 0, 60)),
                    OutputInterface::VERBOSITY_VERBOSE
                );
                if (!$dryRun) {
                    $repo->upsert(self::GP_TABLE, (int)$uid, 'title', $language, $value, md5($srcMap[$uid] ?? ''));
                    $written++;
                }
            }
            usleep(300_000);
        }

        // ── Keywords batches ───────────────────────────────────────────────
        foreach (array_chunk($kwItems, self::BATCH_KW) as $batch) {
            $uids       = array_map('intval', array_column($batch, 'uid'));
            $inputLines = array_map(
                fn($r) => $this->buildInputLine($r, $language, $enCtrl, 'keywords'),
                $batch
            );
            $apiResults = $this->callDelimited($apiKey, $kwPrompt, $inputLines, $uids, 10000, $output);
            $srcMap     = array_column($batch, 'source_value', 'uid');

            foreach ($apiResults as $uid => $value) {
                $value = $this->deduplicateTerms($value);
                $output->writeln(
                    sprintf('  [kw]    %5d | %s', $uid, mb_substr($value, 0, 60)),
                    OutputInterface::VERBOSITY_VERBOSE
                );
                if (!$dryRun) {
                    $repo->upsert(self::GP_TABLE, (int)$uid, 'keywords', $language, $value, md5($srcMap[$uid] ?? ''));
                    $written++;
                }
            }
            usleep(300_000);
        }

        $output->writeln($dryRun
            ? sprintf('[DRY-RUN] Would write %d translations.', count($untranslated))
            : sprintf('✓ Written %d translations.', $written));

        return Command::SUCCESS;
    }

    // ── Positional mapping ────────────────────────────────────────────────────

    /**
     * Builds one input line per record — no uid, only content.
     * EN: just the DE source value.
     * Other langs: "DE value || EN value" (dual-source anchor).
     */
    private function buildInputLine(array $rec, string $language, array $enCtrl, string $field): string
    {
        $de = $rec['source_value'];
        if ($language === 'en') {
            return $de;
        }
        $en = $enCtrl[$rec['uid']][$field] ?? '';
        return $de . ' || ' . $en;
    }

    /**
     * Positional API call: N lines in → N lines out, zipped by index to $uidList.
     * UIDs are never sent to or expected from the model — only line positions matter.
     * On count mismatch: retries each record individually (1 line in → 1 line out).
     *
     * @param int[] $uidList ordered UIDs matching $inputLines by index
     * @return array<int, string> uid → translated value (only UIDs from $uidList)
     */
    private function callPositional(
        string $apiKey,
        string $prompt,
        array $inputLines,
        array $uidList,
        int $maxTokens,
        OutputInterface $output
    ): array {
        $text     = $this->apiCall($apiKey, $prompt, implode("\n", $inputLines), $maxTokens);
        $outLines = $this->splitOutputLines($text);

        if (count($outLines) === count($inputLines)) {
            return $this->zipToUids($uidList, $outLines);
        }

        $output->writeln(sprintf(
            '<comment>  count mismatch: %d in / %d out — retrying %d records individually</comment>',
            count($inputLines), count($outLines), count($inputLines)
        ));

        $results = [];
        foreach ($inputLines as $i => $line) {
            $uid   = $uidList[$i];
            $text1 = $this->apiCall($apiKey, $prompt, $line, $maxTokens);
            $out1  = $this->splitOutputLines($text1);
            if (count($out1) === 1) {
                $results[$uid] = $out1[0];
            } else {
                $output->writeln(sprintf(
                    '<comment>  uid %d: single-record retry still bad (%d lines), skipped</comment>',
                    $uid, count($out1)
                ));
            }
            usleep(100_000);
        }
        return $results;
    }

    /**
     * I/O framing appended to the rules-prompt at call time (the PROMPT_* constants
     * stay untouched). Replaces the fragile "one output line per input line" contract
     * with explicit per-record delimiters — robust against comma/newline reflow in
     * keyword lists, which broke positional line-matching on nearly every batch.
     */
    private const DELIM_FRAMING = <<<'FRAMING'


────────────────────────────────────────
OUTPUT PROTOCOL — follow EXACTLY. This OVERRIDES any "one line per input" instruction above.
The input is a sequence of records, each wrapped as:
<<<REC n>>>
<source>
<<<END>>>
For EACH input record emit EXACTLY ONE output block with the SAME number n, in the same order:
<<<OUT n>>>
<the Spanish translation, applying all rules above>
<<<END>>>
The body MAY contain commas or any characters — ONLY the <<<OUT n>>> and <<<END>>> markers
delimit it. Emit NOTHING outside the blocks: no numbering, no commentary, no blank lines between
blocks. If the translation must be empty (e.g. EMPTY rule), leave the body empty.
FRAMING;

    /**
     * Delimited API call: each record wrapped in <<<REC n>>>…<<<END>>>, parsed back by
     * marker (not line position). Same signature/return as callPositional.
     * On any record missing from the parse: retries it individually.
     *
     * @param int[] $uidList ordered UIDs matching $inputLines by index
     * @return array<int, string> uid → translated value
     */
    private function callDelimited(
        string $apiKey,
        string $prompt,
        array $inputLines,
        array $uidList,
        int $maxTokens,
        OutputInterface $output
    ): array {
        $system = $prompt . self::DELIM_FRAMING;

        $build = static function (array $lines): string {
            $buf = '';
            foreach ($lines as $i => $line) {
                $buf .= "<<<REC $i>>>\n" . $line . "\n<<<END>>>\n";
            }
            return $buf;
        };

        $text   = $this->apiCall($apiKey, $system, $build($inputLines), $maxTokens);
        $parsed = $this->parseDelimited($text); // batch-index → value

        $results = [];
        $missing = [];
        foreach ($uidList as $i => $uid) {
            if (array_key_exists($i, $parsed)) {
                $results[$uid] = $parsed[$i];
            } else {
                $missing[$i] = $uid;
            }
        }

        if ($missing) {
            $output->writeln(sprintf(
                '<comment>  delimited: %d/%d parsed — retrying %d individually</comment>',
                count($parsed), count($inputLines), count($missing)
            ));
            foreach ($missing as $i => $uid) {
                $one = $this->apiCall($apiKey, $system, "<<<REC $i>>>\n" . $inputLines[$i] . "\n<<<END>>>\n", $maxTokens);
                $p   = $this->parseDelimited($one);
                if (array_key_exists($i, $p)) {
                    $results[$uid] = $p[$i];
                } else {
                    // last resort: a single record → the whole bare text is the translation
                    $bare = trim($one);
                    if ($bare !== '' && !str_contains($bare, '<<<')) {
                        $results[$uid] = $bare;
                    } else {
                        $output->writeln(sprintf('<comment>  uid %d: delimited retry still bad, skipped</comment>', $uid));
                    }
                }
                usleep(100_000);
            }
        }
        return $results;
    }

    /** Parse <<<OUT n>>> … <<<END>>> blocks → [batch-index => trimmed value]. */
    private function parseDelimited(string $text): array
    {
        $out = [];
        if (preg_match_all('/<<<OUT\s+(\d+)>>>(.*?)<<<END>>>/s', $text, $m, PREG_SET_ORDER)) {
            foreach ($m as $block) {
                $out[(int)$block[1]] = trim($block[2]);
            }
        }
        return $out;
    }

    /**
     * Zip uid list with output lines by index.
     * Only UIDs from $uidList can appear in the result (structural safety guard).
     *
     * @return array<int, string>
     */
    private function zipToUids(array $uidList, array $outputLines): array
    {
        $result = [];
        foreach ($uidList as $i => $uid) {
            $result[$uid] = trim($outputLines[$i] ?? '');
        }
        return $result;
    }

    /**
     * Split API output into lines. Trims each line; strips trailing empty lines
     * (models often end with \n). Preserves empty lines within the output so that
     * EMPTY-signal records don't break the line count.
     */
    private function splitOutputLines(string $text): array
    {
        $lines = array_map('trim', explode("\n", $text));
        while (count($lines) > 0 && end($lines) === '') {
            array_pop($lines);
        }
        return $lines;
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private function deduplicateTerms(string $value): string
    {
        $terms  = array_map('trim', explode(',', $value));
        $seen   = [];
        $result = [];
        foreach ($terms as $term) {
            if ($term === '') {
                continue;
            }
            $key = mb_strtolower($term);
            if (!isset($seen[$key])) {
                $seen[$key] = true;
                $result[]   = $term;
            }
        }
        return implode(', ', $result);
    }

    /**
     * Fast-path for EN titles: if the source contains "||", extract the EN part
     * (left side) without an API call. Returns null if not applicable.
     */
    private function extractBilingual(string $title): ?string
    {
        if (!str_contains($title, '||')) {
            return null;
        }
        $en = trim(explode('||', $title, 2)[0]);
        if (strlen($en) < 3) {
            return null;
        }
        if (preg_match('/\b(und|oder|der|die|das|ein|eine|von|bei|mit|für|über|auf)\b/i', $en)) {
            return null;
        }
        return $en;
    }

    private function apiCall(string $apiKey, string $systemPrompt, string $userContent, int $maxTokens): string
    {
        $payload = json_encode([
            'model'      => 'claude-haiku-4-5-20251001',
            'max_tokens' => $maxTokens,
            'system'     => $systemPrompt,
            'messages'   => [['role' => 'user', 'content' => $userContent]],
        ], JSON_UNESCAPED_UNICODE);

        $ch = curl_init('https://api.anthropic.com/v1/messages');
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POST           => true,
            CURLOPT_POSTFIELDS     => $payload,
            CURLOPT_TIMEOUT        => 120,
            CURLOPT_HTTPHEADER     => [
                'Content-Type: application/json',
                'x-api-key: ' . $apiKey,
                'anthropic-version: 2023-06-01',
            ],
        ]);
        $response = curl_exec($ch);
        curl_close($ch);

        if (!$response) {
            return '';
        }
        $data = json_decode($response, true);
        return (string)($data['content'][0]['text'] ?? '');
    }

    private function resolveApiKey(): string
    {
        $env = getenv('ANTHROPIC_API_KEY');
        if ($env) {
            return $env;
        }
        $keyFile = ($_SERVER['HOME'] ?? '') . '/.anthropic-api-key';
        if (is_file($keyFile)) {
            return trim((string)file_get_contents($keyFile));
        }
        return '';
    }
}

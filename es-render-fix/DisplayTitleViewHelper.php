<?php
declare(strict_types=1);
namespace Datenglueck\CartGigapixels\ViewHelpers;

use Datenglueck\CartGigapixels\Domain\Model\Gigapixel;
use Datenglueck\CartGigapixels\Domain\Repository\TranslationRepository;
use Psr\Http\Message\ServerRequestInterface;
use TYPO3\CMS\Core\Utility\GeneralUtility;
use TYPO3Fluid\Fluid\Core\ViewHelper\AbstractViewHelper;

/**
 * Language-aware title for a Gigapixel record.
 * Reads from tx_gigapixels_translation (warm-cached); falls back to title.
 *
 * Usage: {cartgigapixels:displayTitle(gigapixel: gigapixel)}
 */
class DisplayTitleViewHelper extends AbstractViewHelper
{
    public function initializeArguments(): void
    {
        parent::initializeArguments();
        $this->registerArgument('gigapixel', Gigapixel::class, 'Gigapixel record', true);
    }

    public function render(): string
    {
        /** @var Gigapixel $gp */
        $gp         = $this->arguments['gigapixel'];
        $languageId = $this->currentLanguageId();

        if ($languageId !== 0) {
            try {
                $lang  = $this->languageCode($languageId);
                $store = GeneralUtility::makeInstance(TranslationRepository::class);
                $val   = $store->get('tx_cartgigapixels_domain_model_gigapixel', $gp->getUid(), 'title', $lang);
                if ($val !== null && $val !== '') {
                    return $val;
                }
            } catch (\Throwable $e) {
                // TranslationRepository unavailable — fall through to DE title
            }
        }
        return $gp->getTitle();
    }

    private function currentLanguageId(): int
    {
        $request = $GLOBALS['TYPO3_REQUEST'] ?? null;
        if ($request instanceof ServerRequestInterface) {
            $lang = $request->getAttribute('language');
            if ($lang !== null) {
                return (int)$lang->getLanguageId();
            }
        }
        return 0;
    }

    private function languageCode(int $languageId): string
    {
        return match ($languageId) {
            1 => 'en',
            2 => 'fr',
            3 => 'ru',
            4 => 'es',
            default => 'en',
        };
    }
}

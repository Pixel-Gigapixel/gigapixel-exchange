<?php

declare(strict_types=1);

namespace Datenglueck\CartGigapixels\ViewHelpers;

use Datenglueck\CartGigapixels\Domain\Model\Gigapixel;
use Datenglueck\CartGigapixels\Domain\Repository\TranslationRepository;
use Psr\Http\Message\ServerRequestInterface;
use TYPO3\CMS\Core\MetaTag\MetaTagManagerRegistry;
use TYPO3\CMS\Core\Site\Entity\SiteInterface;
use TYPO3\CMS\Core\Utility\GeneralUtility;
use TYPO3Fluid\Fluid\Core\ViewHelper\AbstractViewHelper;

/**
 * Sets og:image, og:title, og:description, twitter:image for the current PDP
 * via MetaTagManagerRegistry — overrides generic site-level og: tags.
 *
 * Usage in Show.html:
 *   <cartgigapixels:ogTags gigapixel="{gigapixel}" languageId="{currentLanguageId}" />
 */
class OgTagsViewHelper extends AbstractViewHelper
{
    protected $escapeOutput = false;

    public function initializeArguments(): void
    {
        parent::initializeArguments();
        $this->registerArgument('gigapixel', Gigapixel::class, 'gigapixel model', true);
        $this->registerArgument('languageId', 'int', '0=DE 1=EN', false, 0);
    }

    private function langCode(int $languageId): string
    {
        return match ($languageId) {
            1 => 'en',
            2 => 'fr',
            3 => 'ru',
            4 => 'es',
            default => 'de',
        };
    }

    public function render(): string
    {
        /** @var Gigapixel $gp */
        $gp         = $this->arguments['gigapixel'];
        $languageId = (int)($this->arguments['languageId'] ?? 0);

        if ($gp === null) {
            return '';
        }

        $request = $GLOBALS['TYPO3_REQUEST'] ?? null;
        $baseUrl  = 'https://gigapixel.gmbh';
        if ($request instanceof ServerRequestInterface) {
            $site = $request->getAttribute('site');
            if ($site instanceof SiteInterface) {
                $baseUrl = rtrim((string)$site->getBase(), '/');
            }
        }

        $rawTitle = $gp->getTitle();
        $store = null;
        if ($languageId !== 0) {
            $store = GeneralUtility::makeInstance(TranslationRepository::class);
            $trans = $store->get('tx_cartgigapixels_domain_model_gigapixel', $gp->getUid(), 'title', $this->langCode($languageId));
            if ($trans !== null && $trans !== '') {
                $rawTitle = $trans;
            }
        }
        $title = htmlspecialchars_decode(strip_tags($rawTitle), ENT_QUOTES);

        if ($languageId === 0) {
            $description = (string)$gp->getAiDescriptionDe();
        } elseif ($languageId === 1) {
            $description = (string)($gp->getAiDescriptionEn() ?: $gp->getAiDescriptionDe());
        } else {
            $store ??= GeneralUtility::makeInstance(TranslationRepository::class);
            $trans = $store->get('tx_cartgigapixels_domain_model_gigapixel', $gp->getUid(), 'description', $this->langCode($languageId));
            $description = ($trans !== null && $trans !== '') ? $trans : (string)$gp->getAiDescriptionDe();
        }
        $description = mb_substr(strip_tags($description), 0, 200);

        /** @var MetaTagManagerRegistry $registry */
        $registry = GeneralUtility::makeInstance(MetaTagManagerRegistry::class);

        if ($title !== '') {
            $registry->getManagerForProperty('og:title')->addProperty('og:title', $title, [], true);
        }
        if ($description !== '') {
            $registry->getManagerForProperty('description')->addProperty('description', $description, [], true);
            $registry->getManagerForProperty('og:description')->addProperty('og:description', $description, [], true);
        }

        $firstImage = $gp->getFirstImage();
        if ($firstImage !== null) {
            $fileResource = $firstImage->getOriginalResource();
            if ($fileResource !== null) {
                $imageUrl = $baseUrl . '/' . ltrim($fileResource->getPublicUrl() ?? '', '/');
                $altText  = $languageId === 1
                    ? $title . ' – genuine gigapixel photo'
                    : $title . ' – Gigapixel-Foto';
                $registry->getManagerForProperty('og:image')->addProperty('og:image', $imageUrl, [], true);
                $registry->getManagerForProperty('og:image:alt')->addProperty('og:image:alt', $altText, [], true);
                $registry->getManagerForProperty('twitter:image')->addProperty('twitter:image', $imageUrl, [], true);
            }
        }

        return '';
    }
}

<?php
declare(strict_types=1);
namespace Datenglueck\CartGigapixels\ViewHelpers;
use Datenglueck\CartGigapixels\Domain\Model\Gigapixel;
use Datenglueck\CartGigapixels\Domain\Repository\TranslationRepository;
use Psr\Http\Message\ServerRequestInterface;
use TYPO3\CMS\Core\Utility\GeneralUtility;
use TYPO3Fluid\Fluid\Core\ViewHelper\AbstractViewHelper;
class SchemaViewHelper extends AbstractViewHelper
{
    protected $escapeOutput = false;

    public function initializeArguments(): void
    {
        parent::initializeArguments();
        $this->registerArgument('gigapixel', Gigapixel::class, 'gigapixel', true);
        $this->registerArgument('languageId', 'int', 'current language uid (0=DE, 1=EN)', false, 0);
    }

    private function langCode(int $languageId): string
    {
        return match ($languageId) {
            1 => 'en',
            2 => 'fr',
            3 => 'ru',
            4 => 'es',
            default => 'en',
        };
    }

    public function render(): string
    {
        /** @var Gigapixel $gigapixel */
        $gigapixel  = $this->arguments['gigapixel'] ?? null;
        $languageId = (int)($this->arguments['languageId'] ?? 0);

        if ($gigapixel === null) {
            return '';
        }

        // url / acquireLicensePage / license zeigen auf den kanonischen non-www-Host
        $baseUrl = 'https://gigapixel.gmbh';

        $requestUri = '/';
        $request    = $GLOBALS['TYPO3_REQUEST'] ?? null;
        if ($request instanceof ServerRequestInterface) {
            $np = $request->getAttribute('normalizedParams');
            if ($np !== null) {
                $requestUri = $np->getRequestUri();
            }
        } else {
            $requestUri = $_SERVER['REQUEST_URI'] ?? '/';
        }
        $pageUrl = $baseUrl . explode('?', $requestUri, 2)[0];

        $name = $gigapixel->getTitle() ?: $gigapixel->getName();
        if ($languageId !== 0) {
            $store   = GeneralUtility::makeInstance(TranslationRepository::class);
            $gpTable = 'tx_cartgigapixels_domain_model_gigapixel';
            $lCode   = $this->langCode($languageId);
            $trans   = $store->get($gpTable, $gigapixel->getUid(), 'title', $lCode);
            if ($trans !== null && $trans !== '') {
                $name = $trans;
            }
        }

        $description = $languageId === 0
            ? trim($gigapixel->getAiDescriptionDe())
            : trim($gigapixel->getAiDescriptionEn());
        if ($languageId !== 0) {
            $store     ??= GeneralUtility::makeInstance(TranslationRepository::class);
            $lCode     ??= $this->langCode($languageId);
            $transDesc   = $store->get('tx_cartgigapixels_domain_model_gigapixel',
                                       $gigapixel->getUid(), 'description', $lCode);
            if ($transDesc !== null && $transDesc !== '') {
                $description = $transDesc;   // es/fr/ru aus dem Store (inkl. korrigierter Maße); EN nur Fallback
            }
        }
        if ($description === '') {
            $notes       = trim((string)($gigapixel->getNotes() ?? ''));
            $description = $notes !== '' ? substr(strip_tags($notes), 0, 300) : (string)$name;
        }

        $schema = [
            '@context'    => 'https://schema.org',
            '@type'       => 'Product',
            'name'        => $name,
            'description' => $description,
            'url'         => $pageUrl,
            'brand'       => ['@type' => 'Brand', 'name' => 'Gigapixel GmbH'],
        ];

        // --- verschachteltes ImageObject -----------------------------------------
        $imageNode = ['@type' => 'ImageObject'];

        try {
            $firstImage = $gigapixel->getFirstImage();
            if ($firstImage) {
                $originalFile = $firstImage->getOriginalResource()->getOriginalFile();
                $publicUrl    = $originalFile->getPublicUrl();
                if ($publicUrl) {
                    $imageNode['contentUrl'] = $this->makeAbsolute($publicUrl, $baseUrl);
                }
            }
        } catch (\Throwable $e) {}

        $w = (int)$gigapixel->getFormatWidth();
        $h = (int)$gigapixel->getFormatHeight();
        if ($w > 0) { $imageNode['width']  = $w; }
        if ($h > 0) { $imageNode['height'] = $h; }

        $photographer = trim((string)$gigapixel->getPhotographer());
        if ($photographer !== '') {
            $imageNode['creator']         = ['@type' => 'Person', 'name' => $photographer];
            $imageNode['creditText']      = $photographer;
            $imageNode['copyrightNotice'] = '© ' . $photographer . ' / Gigapixel GmbH';
        }

        $encodingFormat = $this->mimeFromFormat((string)$gigapixel->getformatFile());
        if ($encodingFormat !== '') {
            $imageNode['encodingFormat'] = $encodingFormat;
        }

        $imageNode['acquireLicensePage'] = $pageUrl;
        $imageNode['license']            = $baseUrl . '/lizenzen';

        $schema['image'] = $imageNode;

        // --- sku -----------------------------------------------------------------
        $sku = trim((string)$gigapixel->getSku());
        if ($sku !== '') {
            $schema['sku'] = $sku;
        }

        // --- keywords (sprachabhängig, Store-Quelle) ----------------------------
        $keywords = trim((string)$gigapixel->getKeywords());
        if ($languageId !== 0) {
            $store ??= GeneralUtility::makeInstance(TranslationRepository::class);
            $lCode ??= $this->langCode($languageId);
            $transKw  = $store->get('tx_cartgigapixels_domain_model_gigapixel',
                                    $gigapixel->getUid(), 'keywords', $lCode);
            if ($transKw !== null && $transKw !== '') {
                $keywords = $transKw;
            }
        }
        if ($keywords !== '') {
            $schema['keywords'] = $keywords;
        }

        // --- Offer — Option A: einzelnes Offer mit Einstiegspreis ----------------
        // Motivklasse-0-Guard: price 0 → Offer komplett weglassen (kein price:0!)
        $price = (float)$gigapixel->getPrice();
        if ($price > 0.0) {
            $priceFormatted  = number_format($price, 2, '.', '');
            $schema['offers'] = [
                '@type'              => 'Offer',
                'price'              => $priceFormatted,
                'priceCurrency'      => 'EUR',
                'availability'       => 'https://schema.org/InStock',
                'url'                => $pageUrl,
                'seller'             => ['@type' => 'Organization', 'name' => 'Gigapixel GmbH'],
                'priceSpecification' => [
                    '@type'                 => 'PriceSpecification',
                    'price'                 => $priceFormatted,
                    'priceCurrency'         => 'EUR',
                    'valueAddedTaxIncluded' => false,
                ],
            ];
        }

        $json = json_encode($schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
        return $json !== false ? $json : '';
    }

    private function makeAbsolute(string $url, string $baseUrl): string
    {
        if ($url === '') {
            return '';
        }
        if (str_starts_with($url, 'http://') || str_starts_with($url, 'https://')) {
            return $url;
        }
        return $baseUrl . '/' . ltrim($url, '/');
    }

    private function mimeFromFormat(string $format): string
    {
        $map = [
            'JPG'  => 'image/jpeg',
            'JPEG' => 'image/jpeg',
            'PNG'  => 'image/png',
            'TIF'  => 'image/tiff',
            'TIFF' => 'image/tiff',
            'WEBP' => 'image/webp',
        ];
        return $map[strtoupper(trim($format))] ?? '';
    }
}

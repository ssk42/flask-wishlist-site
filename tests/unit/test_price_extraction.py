"""Tests for the price extraction module."""
import pytest
from unittest.mock import Mock, MagicMock
from bs4 import BeautifulSoup

from services.price_extraction.parser import (
    parse_price,
    get_domain,
    is_amazon_url,
    is_walmart_url,
    is_target_url,
    is_bestbuy_url,
    is_etsy_url
)
from services.price_extraction.extractors.base import BasePriceExtractor
from services.price_extraction.extractors.etsy import EtsyPriceExtractor
from services.price_extraction.extractors.generic import GenericPriceExtractor


class TestParsePrice:
    """Tests for the parse_price() function."""

    # Basic currency formats
    def test_parse_price_us_dollars(self):
        """Should parse US dollar format."""
        assert parse_price('$19.99') == 19.99

    def test_parse_price_uk_pounds(self):
        """Should parse UK pounds format."""
        assert parse_price('\u00a319.99') == 19.99  # £19.99

    def test_parse_price_euros(self):
        """Should parse euro format."""
        assert parse_price('\u20ac19.99') == 19.99  # EUR19.99

    def test_parse_price_no_symbol(self):
        """Should parse price without currency symbol."""
        assert parse_price('29.99') == 29.99

    # Integer prices
    def test_parse_price_integer(self):
        """Should parse integer price."""
        assert parse_price('$100') == 100.0

    def test_parse_price_integer_input(self):
        """Should handle integer input directly."""
        assert parse_price(100) == 100.0

    def test_parse_price_float_input(self):
        """Should handle float input directly."""
        assert parse_price(29.99) == 29.99

    # European decimal format
    def test_parse_price_european_decimal(self):
        """Should parse European decimal format (comma as decimal)."""
        assert parse_price('19,99') == 19.99

    def test_parse_price_european_thousands(self):
        """Should parse European thousands format."""
        assert parse_price('1.234,56') == 1234.56

    # US thousands format
    def test_parse_price_us_thousands(self):
        """Should parse US thousands separator."""
        assert parse_price('$1,234.56') == 1234.56

    def test_parse_price_large_number(self):
        """Should parse large prices with multiple commas."""
        assert parse_price('$12,345.67') == 12345.67

    # Price ranges
    def test_parse_price_range_with_dash(self):
        """Should return first price from range."""
        assert parse_price('$10 - $20') == 10.0

    def test_parse_price_range_with_to(self):
        """Should return first price from 'to' range."""
        assert parse_price('$10 to $20') == 10.0

    def test_parse_price_range_en_dash(self):
        """Should handle en-dash in price range."""
        assert parse_price('$10 \u2013 $20') == 10.0

    # Currency codes
    def test_parse_price_with_usd(self):
        """Should parse price with USD prefix."""
        assert parse_price('USD 19.99') == 19.99

    def test_parse_price_with_eur(self):
        """Should parse price with EUR prefix."""
        assert parse_price('EUR 19,99') == 19.99

    # Edge cases
    def test_parse_price_empty_string(self):
        """Should return None for empty string."""
        assert parse_price('') is None

    def test_parse_price_none(self):
        """Should return None for None input."""
        assert parse_price(None) is None

    def test_parse_price_no_numbers(self):
        """Should return None for text with no numbers."""
        assert parse_price('Price not available') is None

    def test_parse_price_negative(self):
        """Should return None for negative prices."""
        assert parse_price('-$10.00') is None

    def test_parse_price_too_large(self):
        """Should return None for absurdly large prices."""
        assert parse_price('$10,000,000') is None

    def test_parse_price_with_whitespace(self):
        """Should handle whitespace around price."""
        assert parse_price('  $29.99  ') == 29.99

    def test_parse_price_cents_only(self):
        """Should parse prices under a dollar."""
        assert parse_price('$0.99') == 0.99

    def test_parse_price_multiple_spaces(self):
        """Should handle multiple prices (take first)."""
        assert parse_price('$19.99  $24.99') == 19.99

    def test_parse_price_comma_thousands_no_decimal(self):
        """Should parse thousands with comma, no decimal."""
        assert parse_price('$1,234') == 1234.0


class TestGetDomain:
    """Tests for the get_domain() function."""

    def test_get_domain_simple(self):
        """Should extract domain from simple URL."""
        assert get_domain('https://example.com/page') == 'example.com'

    def test_get_domain_removes_www(self):
        """Should remove www prefix."""
        assert get_domain('https://www.amazon.com/product') == 'amazon.com'

    def test_get_domain_subdomain(self):
        """Should preserve non-www subdomains."""
        assert get_domain('https://shop.example.com/') == 'shop.example.com'

    def test_get_domain_complex_path(self):
        """Should extract domain regardless of path."""
        assert get_domain('https://www.target.com/p/product-name/-/A-12345') == 'target.com'

    def test_get_domain_with_port(self):
        """Should include port in domain."""
        assert get_domain('http://localhost:5000/') == 'localhost:5000'

    def test_get_domain_http(self):
        """Should work with http URLs."""
        assert get_domain('http://example.com/page') == 'example.com'

    def test_get_domain_empty(self):
        """Should return None for empty URL."""
        assert get_domain('') is None

    def test_get_domain_none(self):
        """Should return None for None input."""
        assert get_domain(None) is None

    def test_get_domain_lowercase(self):
        """Should return lowercase domain."""
        assert get_domain('https://WWW.EXAMPLE.COM/') == 'example.com'


class TestUrlMatchers:
    """Tests for URL matching functions."""

    # Amazon
    def test_is_amazon_url_us(self):
        """Should match Amazon US URLs."""
        assert is_amazon_url('https://www.amazon.com/product/dp/B123') is True

    def test_is_amazon_url_uk(self):
        """Should match Amazon UK URLs."""
        assert is_amazon_url('https://www.amazon.co.uk/product') is True

    def test_is_amazon_url_de(self):
        """Should match Amazon DE URLs."""
        assert is_amazon_url('https://www.amazon.de/product') is True

    def test_is_amazon_url_false(self):
        """Should not match non-Amazon URLs."""
        assert is_amazon_url('https://www.ebay.com/product') is False

    # Walmart
    def test_is_walmart_url_true(self):
        """Should match Walmart URLs."""
        assert is_walmart_url('https://www.walmart.com/ip/Product/123') is True

    def test_is_walmart_url_false(self):
        """Should not match non-Walmart URLs."""
        assert is_walmart_url('https://www.target.com/') is False

    # Target
    def test_is_target_url_true(self):
        """Should match Target URLs."""
        assert is_target_url('https://www.target.com/p/product/-/A-123') is True

    def test_is_target_url_false(self):
        """Should not match non-Target URLs."""
        assert is_target_url('https://www.walmart.com/') is False

    # Best Buy
    def test_is_bestbuy_url_true(self):
        """Should match Best Buy URLs."""
        assert is_bestbuy_url('https://www.bestbuy.com/site/product/123') is True

    def test_is_bestbuy_url_false(self):
        """Should not match non-Best Buy URLs."""
        assert is_bestbuy_url('https://www.newegg.com/') is False

    # Etsy
    def test_is_etsy_url_true(self):
        """Should match Etsy URLs."""
        assert is_etsy_url('https://www.etsy.com/listing/123/product') is True

    def test_is_etsy_url_false(self):
        """Should not match non-Etsy URLs."""
        assert is_etsy_url('https://www.amazon.com/') is False

    # Edge cases
    def test_url_matcher_empty(self):
        """Should return False for empty URL."""
        assert is_amazon_url('') is False
        assert is_walmart_url('') is False

    def test_url_matcher_none(self):
        """Should return False for None URL."""
        assert is_amazon_url(None) is False
        assert is_target_url(None) is False


class TestBasePriceExtractor:
    """Tests for the BasePriceExtractor class."""

    def test_matches_url_with_matching_domain(self):
        """Should return True when URL matches domain pattern."""
        class TestExtractor(BasePriceExtractor):
            domain_patterns = ['example.com']
            def extract_from_soup(self, soup):
                return None

        assert TestExtractor.matches_url('https://www.example.com/product') is True

    def test_matches_url_with_non_matching_domain(self):
        """Should return False when URL does not match domain pattern."""
        class TestExtractor(BasePriceExtractor):
            domain_patterns = ['example.com']
            def extract_from_soup(self, soup):
                return None

        assert TestExtractor.matches_url('https://www.other.com/product') is False

    def test_matches_url_with_multiple_patterns(self):
        """Should return True if any pattern matches."""
        class TestExtractor(BasePriceExtractor):
            domain_patterns = ['example.com', 'example.co.uk']
            def extract_from_soup(self, soup):
                return None

        assert TestExtractor.matches_url('https://www.example.co.uk/product') is True

    def test_extract_from_response(self):
        """Should parse HTML and call extract_from_soup."""
        class TestExtractor(BasePriceExtractor):
            domain_patterns = ['test.com']
            def extract_from_soup(self, soup):
                elem = soup.find('span', class_='price')
                return 29.99 if elem else None

        extractor = TestExtractor()
        response = Mock()
        response.text = '<html><span class="price">$29.99</span></html>'

        result = extractor.extract_from_response(response)
        assert result == 29.99

    def test_extract_metadata(self):
        """Should extract title, image, and price."""
        class TestExtractor(BasePriceExtractor):
            domain_patterns = ['test.com']
            def extract_from_soup(self, soup):
                return 19.99

        extractor = TestExtractor()
        html = '''
        <html>
            <head>
                <title>Test Product</title>
                <meta property="og:image" content="https://example.com/image.jpg">
            </head>
            <body></body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        metadata = extractor.extract_metadata(soup)

        assert metadata['title'] == 'Test Product'
        assert metadata['image'] == 'https://example.com/image.jpg'
        assert metadata['price'] == 19.99

    def test_extract_title_from_og_tag(self):
        """Should prefer og:title over regular title."""
        class TestExtractor(BasePriceExtractor):
            domain_patterns = ['test.com']
            def extract_from_soup(self, soup):
                return None

        extractor = TestExtractor()
        html = '''
        <html>
            <head>
                <title>Page Title | Site Name</title>
                <meta property="og:title" content="Product Name">
            </head>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        title = extractor._extract_title(soup)
        assert title == 'Product Name'

    def test_extract_title_fallback_to_title_tag(self):
        """Should use title tag when og:title not present."""
        class TestExtractor(BasePriceExtractor):
            domain_patterns = ['test.com']
            def extract_from_soup(self, soup):
                return None

        extractor = TestExtractor()
        html = '<html><head><title>Page Title</title></head></html>'
        soup = BeautifulSoup(html, 'html.parser')
        title = extractor._extract_title(soup)
        assert title == 'Page Title'

    def test_extract_image_from_og_tag(self):
        """Should extract image from og:image tag."""
        class TestExtractor(BasePriceExtractor):
            domain_patterns = ['test.com']
            def extract_from_soup(self, soup):
                return None

        extractor = TestExtractor()
        html = '<html><head><meta property="og:image" content="https://img.jpg"></head></html>'
        soup = BeautifulSoup(html, 'html.parser')
        image = extractor._extract_image(soup)
        assert image == 'https://img.jpg'

    def test_extract_image_returns_none_when_missing(self):
        """Should return None when no og:image tag."""
        class TestExtractor(BasePriceExtractor):
            domain_patterns = ['test.com']
            def extract_from_soup(self, soup):
                return None

        extractor = TestExtractor()
        html = '<html><head></head></html>'
        soup = BeautifulSoup(html, 'html.parser')
        image = extractor._extract_image(soup)
        assert image is None

    def test_static_parse_price(self):
        """Should provide parse_price as static method."""
        assert BasePriceExtractor.parse_price('$29.99') == 29.99


class TestEtsyPriceExtractor:
    """Tests for the EtsyPriceExtractor class."""

    def test_domain_patterns(self):
        """Should match Etsy domain."""
        assert 'etsy.com' in EtsyPriceExtractor.domain_patterns

    def test_matches_etsy_url(self):
        """Should match Etsy URLs."""
        assert EtsyPriceExtractor.matches_url('https://www.etsy.com/listing/123') is True

    def test_extract_from_buy_box_attribute(self):
        """Should extract price from data-buy-box-listing-price attribute."""
        extractor = EtsyPriceExtractor()
        html = '''
        <html>
            <span data-buy-box-listing-price="29.99">$29.99</span>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        price = extractor.extract_from_soup(soup)
        assert price == 29.99

    def test_extract_from_price_class(self):
        """Should extract price from common Etsy price classes."""
        extractor = EtsyPriceExtractor()
        html = '''
        <html>
            <p class="wt-text-title-03">$45.00</p>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        price = extractor.extract_from_soup(soup)
        assert price == 45.0

    def test_extract_from_json_ld(self):
        """Should extract price from JSON-LD structured data."""
        extractor = EtsyPriceExtractor()
        html = '''
        <html>
            <script type="application/ld+json">
            {
                "@type": "Product",
                "offers": {
                    "price": "35.50"
                }
            }
            </script>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        price = extractor.extract_from_soup(soup)
        assert price == 35.5

    def test_extract_from_json_ld_offers_list(self):
        """Should extract price from JSON-LD with offers as list."""
        extractor = EtsyPriceExtractor()
        html = '''
        <html>
            <script type="application/ld+json">
            {
                "@type": "Product",
                "offers": [{"price": "19.99"}]
            }
            </script>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        price = extractor.extract_from_soup(soup)
        assert price == 19.99

    def test_extract_returns_none_when_no_price(self):
        """Should return None when no price found."""
        extractor = EtsyPriceExtractor()
        html = '<html><body>No price here</body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        price = extractor.extract_from_soup(soup)
        assert price is None

    def test_extract_handles_exception(self):
        """Should return None on exception."""
        extractor = EtsyPriceExtractor()
        # Pass a mock that will cause issues
        price = extractor.extract_from_soup(None)
        assert price is None


class TestGenericPriceExtractor:
    """Tests for the GenericPriceExtractor class."""

    def test_matches_any_url(self):
        """Should match any URL as fallback extractor."""
        assert GenericPriceExtractor.matches_url('https://random-store.com/product') is True
        assert GenericPriceExtractor.matches_url('https://unknown-shop.io/item') is True

    def test_extract_from_og_price_meta(self):
        """Should extract price from og:price:amount meta tag."""
        extractor = GenericPriceExtractor()
        html = '''
        <html>
            <head>
                <meta property="og:price:amount" content="24.99">
            </head>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        price = extractor.extract_from_soup(soup)
        assert price == 24.99

    def test_extract_from_product_price_meta(self):
        """Should extract price from product:price:amount meta tag."""
        extractor = GenericPriceExtractor()
        html = '''
        <html>
            <head>
                <meta property="product:price:amount" content="39.99">
            </head>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        price = extractor.extract_from_soup(soup)
        assert price == 39.99

    def test_extract_from_json_ld(self):
        """Should extract price from JSON-LD structured data."""
        extractor = GenericPriceExtractor()
        html = '''
        <html>
            <script type="application/ld+json">
            {
                "@type": "Product",
                "offers": {
                    "@type": "Offer",
                    "price": "49.99"
                }
            }
            </script>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        price = extractor.extract_from_soup(soup)
        assert price == 49.99

    def test_extract_from_json_ld_low_price(self):
        """Should extract lowPrice from AggregateOffer."""
        extractor = GenericPriceExtractor()
        html = '''
        <html>
            <script type="application/ld+json">
            {
                "@type": "Product",
                "offers": {
                    "@type": "AggregateOffer",
                    "lowPrice": "29.99",
                    "highPrice": "59.99"
                }
            }
            </script>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        price = extractor.extract_from_soup(soup)
        assert price == 29.99

    def test_extract_from_microdata(self):
        """Should extract price from microdata itemprop."""
        extractor = GenericPriceExtractor()
        html = '''
        <html>
            <span itemprop="price" content="34.99">$34.99</span>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        price = extractor.extract_from_soup(soup)
        assert price == 34.99

    def test_extract_from_microdata_text_content(self):
        """Should extract price from microdata text when no content attr."""
        extractor = GenericPriceExtractor()
        html = '''
        <html>
            <span itemprop="price">$44.99</span>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        price = extractor.extract_from_soup(soup)
        assert price == 44.99

    def test_extract_from_price_class(self):
        """Should extract price from common .price class."""
        extractor = GenericPriceExtractor()
        html = '''
        <html>
            <div class="price">$54.99</div>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        price = extractor.extract_from_soup(soup)
        assert price == 54.99

    def test_extract_from_product_price_class(self):
        """Should extract price from .product-price class."""
        extractor = GenericPriceExtractor()
        html = '''
        <html>
            <span class="product-price">$64.99</span>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        price = extractor.extract_from_soup(soup)
        assert price == 64.99

    def test_extract_from_data_price_attribute(self):
        """Should extract price from data-price attribute."""
        extractor = GenericPriceExtractor()
        html = '''
        <html>
            <div class="price" data-price="74.99">$74.99</div>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        price = extractor.extract_from_soup(soup)
        assert price == 74.99

    def test_extract_returns_none_when_no_price(self):
        """Should return None when no price found."""
        extractor = GenericPriceExtractor()
        html = '<html><body>No price information</body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        price = extractor.extract_from_soup(soup)
        assert price is None

    def test_extract_ignores_zero_prices(self):
        """Should ignore zero prices from meta tags."""
        extractor = GenericPriceExtractor()
        html = '''
        <html>
            <head>
                <meta property="og:price:amount" content="0">
            </head>
            <span class="price">$29.99</span>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        price = extractor.extract_from_soup(soup)
        assert price == 29.99

    def test_extract_ignores_high_prices_from_css(self):
        """Should ignore absurdly high prices from CSS selectors."""
        extractor = GenericPriceExtractor()
        html = '''
        <html>
            <span class="price">$999,999.99</span>
            <span class="current-price">$49.99</span>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        price = extractor.extract_from_soup(soup)
        # Should skip the first one and get the second
        assert price == 49.99

    def test_extract_handles_invalid_json_ld(self):
        """Should handle invalid JSON-LD gracefully."""
        extractor = GenericPriceExtractor()
        html = '''
        <html>
            <script type="application/ld+json">
            { invalid json here
            </script>
            <span class="price">$39.99</span>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        price = extractor.extract_from_soup(soup)
        # Should fall back to CSS selector
        assert price == 39.99

    def test_extract_from_nested_json_ld(self):
        """Should find price in nested JSON-LD structure."""
        extractor = GenericPriceExtractor()
        html = '''
        <html>
            <script type="application/ld+json">
            {
                "@type": "WebPage",
                "mainEntity": {
                    "@type": "Product",
                    "offers": {
                        "price": "89.99"
                    }
                }
            }
            </script>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        price = extractor.extract_from_soup(soup)
        assert price == 89.99


class TestGenericPriceExtractorCSSSelectors:
    """Tests for CSS selector coverage in GenericPriceExtractor."""

    @pytest.fixture
    def extractor(self):
        return GenericPriceExtractor()

    def test_current_price_class(self, extractor):
        """Should find price in .current-price class."""
        html = '<div class="current-price">$29.99</div>'
        soup = BeautifulSoup(html, 'html.parser')
        assert extractor.extract_from_soup(soup) == 29.99

    def test_sale_price_class(self, extractor):
        """Should find price in .sale-price class."""
        html = '<span class="sale-price">$19.99</span>'
        soup = BeautifulSoup(html, 'html.parser')
        assert extractor.extract_from_soup(soup) == 19.99

    def test_woocommerce_price(self, extractor):
        """Should find price in WooCommerce .woocommerce-Price-amount class."""
        html = '<span class="woocommerce-Price-amount">$39.99</span>'
        soup = BeautifulSoup(html, 'html.parser')
        assert extractor.extract_from_soup(soup) == 39.99

    def test_product_id_selector(self, extractor):
        """Should find price in #product-price ID."""
        html = '<div id="product-price">$49.99</div>'
        soup = BeautifulSoup(html, 'html.parser')
        assert extractor.extract_from_soup(soup) == 49.99

    def test_data_product_price_attribute(self, extractor):
        """Should find price in data-product-price attribute."""
        html = '<div data-product-price="59.99">Price: $59.99</div>'
        soup = BeautifulSoup(html, 'html.parser')
        assert extractor.extract_from_soup(soup) == 59.99

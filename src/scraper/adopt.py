import logging


from core.scraper.typed import ProductType, AdoptPageType

from core.file.cloud_handler import CloudHandler
from core.utils.helper import CookiesProtocol
from core.utils.types import Gender

from core.scraper.base import (
    BaseScraper,
    BaseProduct,
    BaseProductPage,
    BaseProductVariant,
    DummyDriver,
    GenderType,
)

WOMEN = "P0100"
MEN = "P0200"
MIX = "P0300"

HOMEPAGE = "https://www.adopt.com"
PRODUCT_BASE_URL = f"{HOMEPAGE}/fr"

API_HOME_PATH = PRODUCT_BASE_URL
API_GET_PRODUCTS_TEMPLATE = (
    f"{API_HOME_PATH}/fr/parfum.html?" "p={currentPage}&is_scroll=1"
)

HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-US,e1n;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "User-Agent": "PostmanRuntime/7.30.0",
}

logger = logging.getLogger(__name__)


class AdoptProductVariant(BaseProductVariant):
    @property
    def link(self):
        return f"{self.product_parent.link}?contenance={int(self.volume)}+{self.iso_volume_unit}"


class AdoptProduct(BaseProduct):
    @property
    def link(self):
        return f"{self.raw_link}"


class AdoptProductPage(BaseProductPage):
    _total_pages = None
    _first_page: dict = None
    _loaded_pages: set[int] = set()

    @property
    def gender(self) -> GenderType:
        if self.category == WOMEN:
            return Gender.FEMALE
        elif self.category == MEN:
            return Gender.MALE
        else:
            return Gender.ALL

    @property
    def link(self):
        return f"{HOMEPAGE}/c/{self.id}"


class AdoptScraper(BaseScraper):
    def __init__(
        self,
        run_id: str,
        scraper_id: str,
        cloud_handler: CloudHandler,
        cookie_saver: CookiesProtocol,
        driver=DummyDriver(),
        execution_date=None,
        default_wait_seconds=10,
    ):
        super().__init__(
            driver=driver,
            run_id=run_id,
            scraper_id="adopt",
            otp_generator=None,
            cloud_handler=cloud_handler,
            cookie_saver=cookie_saver,
            execution_date=execution_date,
            default_wait_seconds=default_wait_seconds,
        )
        self._loaded_pages: dict[str, set[AdoptProductPage]] = {}
        self._all_loaded_products: set[AdoptProduct] = set()
        self._name = "adopts"

    def load_men_perfume(self):
        self._load_products_by_category(category=MEN)

    def load_women_perfume(self):
        self._load_products_by_category(category=WOMEN)

    def load_mix_perfume(self):
        self._load_products_by_category(category=MIX)

    def _get_page_url(self, page: AdoptProductPage):
        page_url = API_GET_PRODUCTS_TEMPLATE.format(
            categoryCode=page.category, currentPage=page.page_no
        )
        return page_url

    def _get_product_obj(self, page: AdoptProductPage, product: AdoptProduct):
        product_id = product["code"]
        name = product["rangeName"]
        brand = product["masterBrand"]["name"]
        category = product["name"]
        raw_link = product["url"]

        return AdoptProduct(
            source=HOMEPAGE,
            product_id=product_id,
            name=name,
            brand=brand,
            line=category,
            gender=page.gender,
            raw_link=raw_link,
        )

    def _load_products_by_page(self, page: AdoptProductPage):
        logger.info("Loading product for page: %s", page)
        page_url = self._get_page_url(page)
        page_data: AdoptPageType = self.get_json(page_url, headers=HEADERS)
        for product in page_data["products"]:
            marion_product = AdoptProduct(
                source=HOMEPAGE,
                product_id=product["code"],
                name=product.get(
                    "rangeName", product.get("masterBrand", {}).get("name", "unknown")
                ),
                brand=product.get("masterBrand", {}).get("name", "unknown"),
                line=product.get("productLine"),
                gender=page.gender,
                raw_link=product["url"],
            )
            self._all_loaded_products.add(marion_product)
            page.add_product(marion_product)
        return page

    def _load_products_by_category(self, category: str):
        logger.info("Loading products for category %s", category)
        first_page = AdoptProductPage(page_identifier=1, category=category)
        if first_page.category not in self._loaded_pages:
            self._loaded_pages[first_page.category] = set()

        pages = self._loaded_pages[first_page.category]

        page_url = self._get_page_url(first_page)
        page_data: AdoptPageType = self.get_json(page_url, headers=HEADERS)

        total_pages = page_data["pagination"]["totalPages"]
        logger.info("Category %s has %s pages", category, total_pages)

        for page_no in range(1, total_pages + 1):
            page = AdoptProductPage(page_identifier=page_no, category=category)
            if page in pages:
                logger.warning("Page already in page cached!")
                continue
            self._load_products_by_page(page)
            pages.add(page)

    def _load_product_variant(self, product: AdoptProduct):
        result: ProductType = self.get_json(product.api_link, headers=HEADERS)
        if not result:
            logger.error("Cannot find any variant!")
            return
        variants = result["variantMatrix"]
        for variant in variants:
            variant_id = variant["variantOption"]["code"]
            variant_name = variant["variantValueCategory"]["name"]
            variant_price = variant["variantOption"]["priceData"]["value"]
            variant_price_unit = variant["variantOption"]["priceData"]["currencyIso"]
            volume_text = variant["variantValueCategory"]["name"]
            volume, volume_unit = self._get_volume_from_code(volume_text)

            product.add_variant(
                AdoptProductVariant(
                    variant_id=variant_id,
                    variant_name=variant_name,
                    product_parent=product,
                    variant_price=variant_price,
                    variant_price_unit=variant_price_unit,
                    variant_volume=volume,
                    variant_volume_unit=volume_unit,
                )
            )

    def validate_all_products(self):
        self.load_men_perfume()
        self.load_women_perfume()
        self.load_mix_perfume()
        self.load_all_variants()

    def load_all_variants(self):
        for product in self._all_loaded_products:
            self._load_product_variant(product)

    def entry_main(self, **kwargs):
        self.login()
        self.to_json(**kwargs)

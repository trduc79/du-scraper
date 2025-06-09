import logging


from ..typed.base import ProductType
from ..typed.marionnaud import MarionnaudPageType

from ..file.cloud_handler import CloudHandler
from ..utils.helper import CookiesProtocol
from ..utils.types import Gender

from .base import (
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

HOMEPAGE = "https://www.marionnaud.fr"
PRODUCT_BASE_URL = f"{HOMEPAGE}/p"

API_HOME_PATH = "https://api.marionnaud.fr/api/v2/mfr"
API_GET_PRODUCTS_TEMPLATE = (
    f"{API_HOME_PATH}/search?"
    "currentPage={currentPage}&sort=new&categoryCode={categoryCode}&lang=fr_FR&curr=EUR"
)

API_GET_PRODUCT_DETAIL_TEMPLATE = (
    f"{API_HOME_PATH}/products"
    "/{productCode}?fields=FULL,couponCodeValue&lang=fr_FR&curr=EUR"
)

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "User-Agent": "PostmanRuntime/7.30.0",
}

logger = logging.getLogger(__name__)


class MarionnaudProductVariant(BaseProductVariant):
    @property
    def link(self):
        return f"{self.product_parent.link}?varSel={self.id}"


class MarionnaudProduct(BaseProduct):
    @property
    def link(self):
        if self.id == "-1":
            return f"{HOMEPAGE}/{self.raw_link}"
        return f"{PRODUCT_BASE_URL}/{self.id}"

    @property
    def api_link(self):
        return API_GET_PRODUCT_DETAIL_TEMPLATE.format(productCode=self.id)


class MarionnaudProductPage(BaseProductPage):
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


class MarionnaudScraper(BaseScraper):
    def __init__(
        self,
        run_id: str,
        cloud_handler: CloudHandler,
        cookie_saver: CookiesProtocol,
        driver=DummyDriver(),
        execution_date=None,
        default_wait_seconds=10,
    ):
        super().__init__(
            driver=driver,
            run_id=run_id,
            scraper_id="marionnaud",
            otp_generator=None,
            cloud_handler=cloud_handler,
            cookie_saver=cookie_saver,
            execution_date=execution_date,
            default_wait_seconds=default_wait_seconds,
        )
        self._loaded_pages: dict[str, set[MarionnaudProductPage]] = {}
        self._all_loaded_products: set[MarionnaudProduct] = set()
        self._name = "marionnaud"

    def load_men_perfume(self):
        self._load_products_by_category(category=MEN)

    def load_women_perfume(self):
        self._load_products_by_category(category=WOMEN)

    def load_mix_perfume(self):
        self._load_products_by_category(category=MIX)

    def _get_page_url(self, page: MarionnaudProductPage):
        page_url = API_GET_PRODUCTS_TEMPLATE.format(
            categoryCode=page.category, currentPage=page.page_no
        )
        return page_url

    def _get_product_obj(self, page: MarionnaudProductPage, product: MarionnaudProduct):
        product_id = product["code"]
        name = product["rangeName"]
        brand = product["masterBrand"]["name"]
        line = product["rangeName"]
        raw_link = product["url"]

        return MarionnaudProduct(
            source=HOMEPAGE,
            product_id=product_id,
            name=name,
            brand=brand,
            line=line,
            gender=page.gender,
            raw_link=raw_link,
        )

    def _load_products_by_page(self, page: MarionnaudProductPage):
        logger.info("Loading product for page: %s", page)
        page_url = self._get_page_url(page)
        page_data: MarionnaudPageType = self.get_json(page_url, headers=HEADERS)
        for product in page_data["products"]:
            marion_product = MarionnaudProduct(
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
        first_page = MarionnaudProductPage(page_identifier=1, category=category)
        if first_page.category not in self._loaded_pages:
            self._loaded_pages[first_page.category] = set()

        pages = self._loaded_pages[first_page.category]

        page_url = self._get_page_url(first_page)
        page_data: MarionnaudPageType = self.get_json(page_url, headers=HEADERS)

        total_pages = page_data["pagination"]["totalPages"]
        logger.info("Category %s has %s pages", category, total_pages)

        for page_no in range(1, total_pages + 1):
            page = MarionnaudProductPage(page_identifier=page_no, category=category)
            if page in pages:
                logger.warning("Page already in page cached!")
                continue
            self._load_products_by_page(page)
            pages.add(page)

    def _load_product_variant(self, product: MarionnaudProduct):
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
                MarionnaudProductVariant(
                    variant_id=variant_id,
                    variant_name=variant_name,
                    product_parent=product,
                    variant_price=variant_price,
                    variant_price_unit=variant_price_unit,
                    variant_volume=volume,
                    variant_volume_unit=volume_unit,
                )
            )
        product.added_all_variants()

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

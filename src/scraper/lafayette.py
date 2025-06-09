import logging


from core.typed.lafayette import LafayettePageType, LafayetteProductType

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

ALL_PERFUME = r"%2Fc%2Fbeaute%2Fparfums%2Ftri%2Fnew-desc"
WOMEN_PERFUME = r"%2Fc%2Fbeaute%2Fparfums%2Ffgenre%2F2%2F3%2Ftri%2Fnew-desc"
MEN_PERFUME = r"%2Fc%2Fbeaute%2Fparfums%2Ffgenre%2F1%2F3%2Ftri%2Fnew-desc"

HOMEPAGE = "https://www.galerieslafayette.com"
PRODUCT_BASE_URL = f"{HOMEPAGE}/p"

API_HOME_PATH = "https://sapapi.galerieslafayette.com/occ/v2/gl-fr"
API_GET_PRODUCTS_TEMPLATE = (
    f"{API_HOME_PATH}/products/search?"
    "query={categoryCode}&currentPage={currentPage}&lang=fr&curr=EUR&pageSize=100&sort=new-desc"
)


API_GET_PRODUCT_DETAIL_TEMPLATE = (
    f"{API_HOME_PATH}/products" "/{productCode}?lang=fr&curr=EUR"
)


logger = logging.getLogger(__name__)


class LafayetteProductVariant(BaseProductVariant):
    @property
    def link(self):
        if self.id == "-1":
            logger.info("Cannot find id, return parent link")
            return self.product_parent.link
        return f"{PRODUCT_BASE_URL}/{self.id}"


class LafayetteProduct(BaseProduct):
    @property
    def link(self):
        if self.id == "-1":
            return f"{HOMEPAGE}/{self.raw_link}"
        return f"{PRODUCT_BASE_URL}/{self.id}"

    @property
    def api_link(self):
        return API_GET_PRODUCT_DETAIL_TEMPLATE.format(productCode=self.id)


class LafayetteProductPage(BaseProductPage):
    _total_pages = None
    _first_page: dict = None
    _loaded_pages: set[int] = set()

    @property
    def gender(self) -> GenderType:
        if self.category == "P0100":
            return Gender.FEMALE
        elif self.category == "P0200":
            return Gender.MALE
        else:
            return Gender.ALL

    @property
    def link(self):
        return f"{HOMEPAGE}/c/{self.id}"


class LafayetteScraper(BaseScraper):
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
            scraper_id="lafayette",
            otp_generator=None,
            cloud_handler=cloud_handler,
            cookie_saver=cookie_saver,
            execution_date=execution_date,
            default_wait_seconds=default_wait_seconds,
        )
        self._loaded_pages: dict[str, set[LafayetteProductPage]] = {}
        self._all_loaded_products: set[LafayetteProduct] = set()
        self._name = "lafayette"

    def load_men_perfume(self):
        self._load_products_by_category(category=MEN_PERFUME)

    def load_women_perfume(self):
        self._load_products_by_category(category=WOMEN_PERFUME)

    def load_all_perfume(self):
        self._load_products_by_category(category=ALL_PERFUME)

    def _get_page_url(self, page: LafayetteProductPage):
        page_url = API_GET_PRODUCTS_TEMPLATE.format(
            categoryCode=page.category, currentPage=page.page_no
        )
        return page_url

    def _get_product_obj(
        self, page: LafayetteProductPage, product: LafayetteProductType
    ):
        product_id = product["baseProduct"]
        name = product["name"]
        brand = product["brand"]["name"]
        line = product["productLine"]
        raw_link = product["url"]

        return LafayetteProduct(
            source=HOMEPAGE,
            product_id=product_id,
            name=name,
            brand=brand,
            line=line,
            gender=page.gender,
            raw_link=raw_link,
        )

    def _load_products_by_page(self, page: LafayetteProductPage):
        logger.info("Loading product for page: %s", page)
        page_url = self._get_page_url(page)
        page_data: LafayettePageType = self.get_json(page_url)
        for product in page_data["products"]:
            marion_product = LafayetteProduct(
                source=HOMEPAGE,
                product_id=product["baseProduct"],
                name=product.get(
                    "name", product.get("brand", {}).get("name", "unknown")
                ),
                brand=product.get("brand", {}).get("name", "unknown"),
                line=product["name"],
                gender=product.get("gender", {}).get("name", "U")[:1].upper(),
                raw_link=product["url"],
            )
            self._all_loaded_products.add(marion_product)
            page.add_product(marion_product)
        return page

    def _load_products_by_category(self, category: str):
        logger.info("Loading products for category %s", category)
        first_page = LafayetteProductPage(page_identifier=1, category=category)
        if first_page.category not in self._loaded_pages:
            self._loaded_pages[first_page.category] = set()

        pages = self._loaded_pages[first_page.category]

        page_url = self._get_page_url(first_page)
        page_data: LafayettePageType = self.get_json(page_url)

        total_pages = page_data["pagination"]["totalPages"]
        logger.info("Category %s has %s pages", category, total_pages)

        for page_no in range(1, total_pages + 1):
            page = LafayetteProductPage(page_identifier=page_no, category=category)
            if page in pages:
                logger.warning("Page already in page cached!")
                continue
            self._load_products_by_page(page)
            pages.add(page)

    def _load_product_variant(self, product: LafayetteProduct):
        result: LafayetteProductType = self.get_json(product.api_link)
        if not result:
            logger.error("Cannot find any variant!")
            return
        variants = result["variantOptions"]
        for variant in variants:
            variant_id = variant["code"]
            variant_name = ""
            price_data = variant.get("priceData") or {"value": None}
            variant_price = price_data.get("value")
            variant_price_unit = price_data.get("currencyIso")
            for qualifier in variant["variantOptionQualifiers"]:
                if qualifier["qualifier"] == "capacity":
                    variant_name = qualifier["value"]
                    break
            volume, volume_unit = self._get_volume_from_code(variant_name)

            product.add_variant(
                LafayetteProductVariant(
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
        self.load_all_perfume()
        self.load_all_variants()

    def load_all_variants(self):
        for product in self._all_loaded_products:
            self._load_product_variant(product)

    def entry_main(self, **kwargs):
        self.login()
        self.to_json(**kwargs)

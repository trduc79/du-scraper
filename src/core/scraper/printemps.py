import logging


from ..typed.base import Hit, Result
from ..typed.printemps import PrintempsPageType, PrintempsProductType

from ..file.cloud_handler import CloudHandler
from ..utils.helper import CookiesProtocol


from .base import (
    BaseScraper,
    BaseProduct,
    BaseProductPage,
    BaseProductVariant,
    DummyDriver,
    GenderType,
)

ALL_PERFUME = r"parfum"

HOMEPAGE = "https://www.printemps.com"
PRODUCT_BASE_URL = f"{HOMEPAGE}/fr/fr"

API_HOME_PATH = f"{HOMEPAGE}"
API_GET_PRODUCTS_TEMPLATE = f"{API_HOME_PATH}/ajax.php"
API_GET_PRODUCT_DETAIL_TEMPLATE = (
    f"{API_HOME_PATH}/ajax.php?" "pid={productCode}&do=getLstRefDispo"
)


logger = logging.getLogger(__name__)


class PrintempsProductVariant(BaseProductVariant):
    @property
    def link(self):
        return self.raw_link


class PrintempsProduct(BaseProduct):
    @property
    def link(self):
        return self.raw_link

    @property
    def api_link(self):
        return API_GET_PRODUCT_DETAIL_TEMPLATE.format(productCode=self.id)


class PrintempsProductPage(BaseProductPage):
    _total_pages = None
    _first_page: dict = None
    _loaded_pages: set[int] = set()

    @property
    def gender(self) -> GenderType:
        if self.category == "P0100":
            return "female"
        elif self.category == "P0200":
            return "male"
        else:
            return "unisex"

    @property
    def link(self):
        return f"{HOMEPAGE}/c/{self.id}"


class PrintempsScraper(BaseScraper):
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
            scraper_id="printemps",
            otp_generator=None,
            cloud_handler=cloud_handler,
            cookie_saver=cookie_saver,
            execution_date=execution_date,
            default_wait_seconds=default_wait_seconds,
        )
        self._loaded_pages: dict[str, set[PrintempsProductPage]] = {}
        self._all_loaded_products: set[PrintempsProduct] = set()
        self._name = "printemps"

    def load_all_perfume(self):
        self._load_products_by_category(category=ALL_PERFUME)

    def _get_body_payload(self, page: PrintempsProductPage, hits_per_page: int = 200):
        body_payload = {
            "do": "search",
            "action": "search",
            "requests[0][indexName]": "parfum",
            "requests[0][params][hitsPerPage]": hits_per_page,
            "requests[0][params][page]": page.page_no,
        }
        return body_payload

    def _get_page_url(self, page: PrintempsProductPage = ""):
        logger.debug("Page URL: %s", page.link)
        return API_GET_PRODUCTS_TEMPLATE


    def _get_product_obj(
        self, page: PrintempsProductPage, product: PrintempsProductType
    ):
        product_id = product["baseProduct"]
        name = product["name"]
        brand = product["brand"]["name"]
        line = product["productLine"]
        raw_link = product["url"]

        return PrintempsProduct(
            source=HOMEPAGE,
            product_id=product_id,
            name=name,
            brand=brand,
            line=line,
            gender=page.gender,
            raw_link=raw_link,
        )

    def _load_products_by_page(
        self, page: PrintempsProductPage, hits_per_page: int = 200
    ):
        logger.info("Loading product for page: %s", page)
        page_url = self._get_page_url(page)
        body_payload = self._get_body_payload(page=page, hits_per_page=hits_per_page)
        page_data: PrintempsPageType = self.post_form(page_url, data=body_payload)
        result: Result = page_data["results"][0]
        products: list[Hit] = result["hits"]

        for product in products:
            printemps_product = PrintempsProduct(
                source=HOMEPAGE,
                product_id=product["objectID"],
                name=product.get("itemLabel", product.get("itemName")),
                brand=product.get("mark", "unknown"),
                line=product["mark"],
                gender=product.get("gender", {}).get("name", "U")[:1].upper(),
                raw_link=product.get("ficheProduitUrl"),
            )
            self._all_loaded_products.add(printemps_product)
            page.add_product(printemps_product)
        return page

    def _load_products_by_category(self, category: str, hits_per_page=200):
        logger.info("Loading products for category %s", category)
        first_page = PrintempsProductPage(page_identifier=1, category=category)
        if first_page.category not in self._loaded_pages:
            self._loaded_pages[first_page.category] = set()

        pages = self._loaded_pages[first_page.category]

        page_url = self._get_page_url(first_page)
        body_payload = self._get_body_payload(
            page=first_page, hits_per_page=hits_per_page
        )
        page_data: PrintempsPageType = self.post_form(page_url, data=body_payload)
        result: Result = page_data["results"][0]

        total_pages = result["nbPages"]
        logger.info("Category %s has %s pages", category, total_pages)

        for page_no in range(1, total_pages + 1):
            page = PrintempsProductPage(page_identifier=page_no, category=category)
            if page in pages:
                logger.warning("Page already in page cached!")
                continue
            self._load_products_by_page(page)
            pages.add(page)

    def _load_product_variant(self, product: PrintempsProduct):
        result: PrintempsProductType = self.get_json(product.api_link)
        if not result:
            logger.error("Cannot find any variant!")
            return
        for variant_id, variant in result.items():
            variant_name = variant["label"]
            variant_price = variant["pxAff"]
            price_with_unit = variant["pxAffFormatted"].replace(";", "").upper()
            variant_price_unit = (
                "EUR"
                if "EURO" in price_with_unit
                else price_with_unit.split("&")[-1].upper()
            )
            volume, volume_unit = self._get_volume_from_code(variant_name)
            total_stock = variant.get("stock", {}).get("total_stock", 0)

            product.add_variant(
                PrintempsProductVariant(
                    variant_id=variant_id,
                    variant_name=variant_name,
                    product_parent=product,
                    variant_price=variant_price,
                    variant_price_unit=variant_price_unit,
                    variant_volume=volume,
                    variant_volume_unit=volume_unit,
                    variant_link=product.raw_link,
                    variant_stock=total_stock,
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

import logging

from .models import ScraperOutput
from .typed import SommelierProductType

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

HOMEPAGE = "https://sommelierduparfum.com"
PRODUCT_BASE_URL = f"{HOMEPAGE}en/product/"

API_HOME_PATH = f"{HOMEPAGE}"
API_GET_PRODUCTS_TEMPLATE = f"{API_HOME_PATH}/scroll_pf_reco_list"
API_GET_PRODUCT_DETAIL_TEMPLATE = (
    f"{API_HOME_PATH}/get_perfume_page_from_slug"
    )


logger = logging.getLogger(__name__)

def get_gender(raw_gender: str) -> GenderType:
    gender_mapping = {
        "women and men": Gender.ALL,
        "women": Gender.FEMALE,
        "men": Gender.MALE,
    }
    return gender_mapping.get(raw_gender, Gender.ALL)

class SommelierProductVariant(BaseProductVariant):
    @property
    def link(self):
        return self.product_parent.link


class SommelierProduct(BaseProduct):
    @property
    def link(self):
        return f"{PRODUCT_BASE_URL}/{self.raw_link}"

    @property
    def api_link(self):
        return API_GET_PRODUCT_DETAIL_TEMPLATE


class SommelierProductPage(BaseProductPage):
    _total_pages = None
    _first_page: dict = None
    _loaded_pages: set[int] = set()

    @property
    def gender(self) -> GenderType:
        if self.category == "P0100":
            return Gender.MALE
        elif self.category == "P0200":
            return "male"
        else:
            return GenderType

    @property
    def link(self):
        return f"{HOMEPAGE}/c/{self.id}"


class SommelierScraper(BaseScraper):
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
            scraper_id="sommelier",
            otp_generator=None,
            cloud_handler=cloud_handler,
            cookie_saver=cookie_saver,
            execution_date=execution_date,
            default_wait_seconds=default_wait_seconds,
        )
        self._loaded_pages: dict[str, set[SommelierProductPage]] = {}
        self._all_loaded_products: set[SommelierProduct] = set()
        self._name = "sommelier"

    def load_all_perfume(self):
        raise NotImplementedError()

    def _get_product_obj(
        self, page: SommelierProductPage, product: SommelierProductType
    ):
        product_id = product["id_sommelier"]
        name = product["name"]
        brand = product["brand"]["name"]
        line = product["productLine"]
        raw_link = product["url"]

        return SommelierProduct(
            source=HOMEPAGE,
            product_id=product_id,
            name=name,
            brand=brand,
            line=line,
            gender=page.gender,
            raw_link=raw_link,
        )

    def _load_product_variant(self, product: SommelierProduct):
        result: SommelierProductType = self.get_json(product.api_link)
        if not result:
            logger.error("Cannot find any variant!")
            return
        for variant_id, variant in result.items():
            variant_name = variant["label"]
            variant_price = variant["pxAff"]
            price_with_unit = variant["pxAffFormatted"].replace(";", "").upper()
            variant_price_unit = "EUR" if "EURO" in price_with_unit else price_with_unit.split("&")[-1].upper()
            volume, volume_unit = self._get_volume_from_code(variant_name)

            product.add_variant(
                SommelierProductVariant(
                    variant_id=variant_id,
                    variant_name=variant_name,
                    product_parent=product,
                    variant_price=variant_price,
                    variant_price_unit=variant_price_unit,
                    variant_volume=volume,
                    variant_volume_unit=volume_unit,
                    variant_link=product.raw_link,
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

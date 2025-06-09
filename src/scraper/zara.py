import logging
import re

from core.typed.zara import (
    ZaraProductType,
    ZaraCategoryProductType,
    ZaraCategoryType,
    ZaraProductType,
)

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

HOMEPAGE = "https://www.zara.com"
PRODUCT_BASE_URL = f"{HOMEPAGE}/fr/fr"

API_HOME_PATH = f"{PRODUCT_BASE_URL}"
API_GET_CATEGORY_TEMPLATE = f"{API_HOME_PATH}/categories"
API_GET_PRODUCTS_TEMPLATE = f"{API_HOME_PATH}/category/" "{categoryCode}/products"


HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "User-Agent": "PostmanRuntime/7.30.0",
}

PERFUME_KEYWORDS = (
    "PERFUME",
    "EAU DE PARFUM",
    "EAU DE TOILETTE",
    "EAU FRAICHE",
    "EAU DE PARFUM",
    "EAU DE COLOGNE",
    "PERFU-REG-PREM",
    "PERFU-MID-PREM",
    "PERFU",
)

logger = logging.getLogger(__name__)


class ZaraProductVariant(BaseProductVariant):
    @property
    def link(self):
        return f"{self.raw_link}"


class ZaraProduct(BaseProduct):
    def __init__(
        self,
        source: str,
        product_id: str,
        name: str,
        brand: str,
        line: str,
        gender=Gender.ALL,
        raw_link="",
    ):
        super().__init__(
            source=source,
            product_id=product_id,
            name=name,
            brand=brand,
            line=line,
            gender=gender,
            raw_link=raw_link,
        )
        self._is_variants_loaded = True

    @property
    def link(self):
        return self.raw_link


class ZaraProductCategory(BaseProductPage):
    def __init__(
        self,
        page_identifier: str,
        category: str,
        section_name: str = "",
    ):
        super().__init__(page_identifier=page_identifier, category=category)
        self.section_name = section_name
        self.category = category
        self.products: set[ZaraProduct] = set()
        self._loaded_pages = set()
        self._total_pages = None
        self._first_page = None
        self._loaded_pages = set()

    @property
    def gender(self) -> GenderType:
        if self.section_name.upper() == "WOMAN":
            return Gender.FEMALE
        elif self.category.upper() == "MAN":
            return Gender.MALE
        else:
            return Gender.ALL

    @property
    def link(self):
        return f"{PRODUCT_BASE_URL}/category/{self.id}/products"


class ZaraScraper(BaseScraper):
    def __init__(
        self,
        run_id: str,
        cloud_handler: CloudHandler,
        cookie_saver: CookiesProtocol,
        driver: DummyDriver = DummyDriver(),
        execution_date=None,
        default_wait_seconds=10,
    ):
        super().__init__(
            driver=driver,
            run_id=run_id,
            scraper_id="zara",
            otp_generator=None,
            cloud_handler=cloud_handler,
            cookie_saver=cookie_saver,
            execution_date=execution_date,
            default_wait_seconds=default_wait_seconds,
        )
        self._loaded_categories: set[ZaraProductCategory] = set()
        self._all_loaded_products: set[ZaraProduct] = set()
        self._name = "Zara"

    def _get_products_url(self, category: ZaraProductCategory):
        product_url = API_GET_PRODUCTS_TEMPLATE.format(categoryCode=category.page_no)
        return product_url

    def _get_product_obj(self, page: ZaraProductCategory, product: ZaraProduct):
        product_id = product["code"]
        name = product["rangeName"]
        brand = product["masterBrand"]["name"]
        category = product["name"]
        raw_link = product["url"]

        return ZaraProduct(
            source=HOMEPAGE,
            product_id=product_id,
            name=name,
            brand=brand,
            line=category,
            gender=page.gender,
            raw_link=raw_link,
        )

    def _get_volume_from_name(self, name: str):
        name = name.lower()
        if "ml" not in name:
            return None, None
        values = re.split(r"\W+", name)
        for index, value in enumerate(values):
            if "ml" not in value:
                continue
            if value != "ml":
                logger.info("ML together with number: %s", value)
                return value.split("ml")[0], "ml"
            try:
                volume = int(values[index - 1])
                return volume, "ml"
            except (ValueError, IndexError):
                logger.error("Cannot parse volume from name: %s", name)
                return None, None

        return None, None

    def _is_valid_perfume(self, perfume_name: str) -> bool:
        for keyword in PERFUME_KEYWORDS:
            if keyword in perfume_name.upper():
                return True
        return False

    def _get_products_from_element(self, element: ZaraProductType) -> set[ZaraProduct]:
        if "commercialComponents" not in element:
            logger.error("No commercial component found in element")
            return
        commercial_component = element["commercialComponents"]
        result = set()
        for component in commercial_component:
            if str(component.get("type")).lower() != "product":
                logger.info("Not a product type: %s", component.get("type"))
                continue

            gender: GenderType = "all"
            if component["sectionName"].upper() == "WOMAN":
                gender = "F"
            elif component["sectionName"].upper() == "MAN":
                gender = "M"

            product_name = component["name"]
            if not product_name:
                logger.warning("Product name not found in component")
                continue

            seo_keyword = component["seo"]["keyword"]
            seo_product_id = component["seo"]["seoProductId"]
            seo_discern_id = component["seo"].get("discernProductId")
            product_link = f"{PRODUCT_BASE_URL}/{seo_keyword}-p{seo_product_id}.html"
            variant_link = f"{product_link}?v1={seo_discern_id}"

            if not seo_keyword:
                logger.error("SEO keyword not found in component")
                continue

            line_name = component["subfamilyName"]

            if not self._is_valid_perfume(line_name):
                logger.warning("Not a perfume product: %s", line_name)
                logger.info("Product link: %s", product_link)
                continue

            product = ZaraProduct(
                source=HOMEPAGE,
                product_id=str(seo_product_id),
                name=product_name,
                brand=component["brand"]["brandGroupCode"],
                line=line_name,
                gender=gender,
                raw_link=product_link,
            )
            if product in self._all_loaded_products:
                for p in self._all_loaded_products:
                    if p != product:
                        continue
                    logger.warning("Product already in cached! %s", product.name)
                    product = p
            self._all_loaded_products.add(product)

            variant_volume, variant_volume_unit = self._get_volume_from_name(
                product_name
            )
            variant = ZaraProductVariant(
                variant_id=str(component["id"]),
                variant_name=seo_keyword,
                product_parent=product,
                variant_price=component["price"] / 100,
                variant_price_unit="EUR",
                variant_volume=variant_volume,
                variant_volume_unit=variant_volume_unit,
                variant_link=variant_link,
            )

            product.add_variant(variant)

            result.add(product)

        return result

    def _load_products_by_category(self, category: ZaraProductCategory):
        logger.info("Loading product for cate: %s", category.category)
        page_url = self._get_products_url(category)
        page_data: ZaraCategoryProductType = self.get_json(page_url)
        for products in page_data["productGroups"]:
            for element in products["elements"]:
                products = self._get_products_from_element(element)
                for product in products:
                    category.add_product(product)
        return category

    def get_perfume_subcategories(
        self, subcategories: list[ZaraCategoryType]
    ) -> list[dict]:
        result = []
        if not subcategories:
            return result

        for subcategory in subcategories:
            # If parent category is perfume, does not need to check subcategories
            if self._is_valid_perfume(subcategory["key"]):
                result.append(subcategory)
                logger.info(
                    "Found perfume subcategory: %s - %s",
                    subcategory["id"],
                    subcategory["key"],
                )
                continue

            p_cate_in_sub_cate = self.get_perfume_subcategories(
                subcategory.get("subcategories")
            )
            result.extend(p_cate_in_sub_cate)

        return result

    def get_perfume_categories(self) -> list[ZaraCategoryType]:
        categories: ZaraCategoryProductType = self.get_json(API_GET_CATEGORY_TEMPLATE)

        all_perfume_categories = []
        for category in categories.get("categories", []):
            perfume_subcategories = self.get_perfume_subcategories(
                category.get("subcategories")
            )
            all_perfume_categories.extend(perfume_subcategories)
        return all_perfume_categories

    def load_perfume_from_all_categories(self):
        categories = self.get_perfume_categories()
        for category in categories:
            category_obj = ZaraProductCategory(
                page_identifier=category["id"],
                category=category["name"],
                section_name=category["sectionName"],
            )
            if category_obj in self._loaded_categories:
                logger.warning("Category already in cached! %s", category_obj.id)
                continue
            self._load_products_by_category(category_obj)
            self._loaded_categories.add(category_obj)

    def validate_all_products(self):
        self.load_perfume_from_all_categories()

    def entry_main(self, **kwargs):
        self.login()
        self.to_json(**kwargs)

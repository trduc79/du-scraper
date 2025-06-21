from functools import partial
import json
import random
import re
import logging
import math
import uuid



from core.file.cloud_handler import CloudHandler
from core.utils.helper import CookiesProtocol
from core.scraper.base import (
    BaseScraper,
    BaseProduct,
    BaseProductPage,
    BaseProductVariant,
    DummyDriver,
)

HOMEPAGE = "https://www.harrods.com/en-us"
URL = "https://www.harrods.com"
PRODUCT_LIST = "https://www.harrods.com/en-us/perfume"

API_BASE = "https://www.harrods.com/en-af/api/rpc"
API_PRODUCT_BY_MASTER_KEY = f"{API_BASE}/getProductsByMasterKey"


HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-US,e1n;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "User-Agent": "PostmanRuntime/7.30.0",
}
logger = logging.getLogger(__name__)


class HarrodsProductVariant(BaseProductVariant):
    @property
    def link(self):
        return f"{self.raw_link}"


class HarrodsProductPage(BaseProductPage):
    @property
    def link(self):
        return f"{PRODUCT_LIST}?page={self.id}"


class HarrodsProduct(BaseProduct):
    def __init__(
        self,
        source: str,
        product_id: str,
        name: str,
        brand: str,
        line: str,
        gender=str,
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

    @property
    def link(self):
        return self.raw_link


class HarrodsScraper(BaseScraper):
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
            scraper_id="Harrods",
            otp_generator=None,
            cloud_handler=cloud_handler,
            cookie_saver=cookie_saver,
            execution_date=execution_date,
            default_wait_seconds=default_wait_seconds,
        )
        self._all_loaded_products: set[HarrodsProduct] = set()
        self._name = "Harrods"
        
    def is_valid_uuid(self, s: str) -> bool:
        if not isinstance(s, str):
            return False

        pattern = r"^[A-F0-9]{8}-([A-F0-9]{4}-){3}[A-F0-9]{12}$"
        return bool(re.fullmatch(pattern, s))


    def _find_master_key(self, product: HarrodsProduct):
        nuxt_data = self.soup_find_all_by_attribute("id", "__NUXT_DATA__")
        if not nuxt_data:
            logger.error("Cannot find Nuxt data")
            return

        if len(nuxt_data) > 1:
            logger.warning("Find more than one Nuxt data!")

        for nuxt in nuxt_data:
            data = nuxt.get_text()
            json_data = json.loads(data)
            if not json_data:
                logger.warning("Cannot find the data")
                return
            
            for index, value in enumerate(json_data):
                if str(value) != product.id:
                    continue
                if index > 0: 
                    previous_value = json_data[index - 1]
                    if self.is_valid_uuid(str(previous_value)):
                        return previous_value
                return value

    def _load_product_variant(self, product: HarrodsProduct):
        master_key = self._find_master_key(product)
        if not master_key:
            logger.error("Cannot find variant")
            return

        data = {"payload": {"masterKey": master_key}}

        response = self.post(API_PRODUCT_BY_MASTER_KEY, json_data=data, data=None,use_cached=False)
        if not response:
            logger.error("Cannot find variant or out of stock")
            return

        entities = response.get("entities", [])
        if not entities:
            logger.warning("Product have problem : %s", product.link)
            return

        for entity in entities:
            variant = entity.get("variants", [{}])[0]
            variant_id = variant.get("id")

            price_data = variant.get("price", {})
            price = price_data.get("withTax")
            variant_price = price / 100 if price is not None else None

            currency = price_data.get("currencyCode", "")

            volume_label = entity.get("attributes", {}).get("volumeDescription", {}) \
                                .get("values", {}).get("label", "")
            
            variant_volume = "1"
            variant_volume_unit = "unit" 
            if " " in volume_label:
                variant_volume, variant_volume_unit = volume_label.split(" ")
                variant_volume_unit = variant_volume_unit.lower()
            else:
                name_label = entity.get("attributes", {}).get("name", {}).get("values", {}).get("label", "")
                import re
                match = re.search(r"\((\d+(?:\.\d+)?)\s*([a-zA-Z]+)\)", name_label)
                if match:
                    variant_volume = match.group(1)
                    variant_volume_unit = match.group(2).lower()

            logger.info(
                " Variant -> Size: %s | Unit: %s | Price: %s | ID: %s | URL: %s",
                variant_volume,
                variant_volume_unit,
                variant_price,
                variant_id,
                product.link,
            )

            product.add_variant(
                HarrodsProductVariant(
                    variant_id=variant_id,
                    product_parent=product,
                    variant_name=product.name,
                    variant_price=variant_price,
                    variant_price_unit=currency,
                    variant_link=product.link,
                    variant_volume=variant_volume,
                    variant_volume_unit=variant_volume_unit,
                    variant_stock=True,
                )
            )

        product.added_all_variants()
        
    def get_max_page(self, base_url: str) -> int:
        page = 1
        while True:
            soup = self.get(f"{base_url}?page={page}")
            
            next_button = None
            pagination_buttons = soup.select('[data-test-id="paginationButton"]')
            
            for button in pagination_buttons:
                if 'next' in button.get_text().lower():
                    next_button = button
                    break
            
            if not next_button:
                return page
    
            page += 1
   
   

    def load_all_product_by_url(self, base_url: str, use_cache=True):
        fully_loaded = lambda _: self.find_all_by_attribute(
            "data-test-id", "product-item"
        )
        max_page = self.get_max_page(base_url)
        for page in range(1, max_page + 1):
            self.get(
                f"{base_url}?page={page}",
                use_cache=use_cache,
                condition=fully_loaded,
                timeout=10,
            )
            products = self.soup.select('article[data-test-id="product-item"]')
            logger.info("Page %s have %s products.", page, len(products))

            for product in products:
                product_id = self.get_product_id(product)
                full_href = self.get_full_href(product)
                brand = self.get_product_brand(product)
                name = self.get_product_name(product)

                product_obj = HarrodsProduct(
                    source=HOMEPAGE,
                    product_id=product_id,
                    name=name,
                    brand=brand,
                    line="Parfum",
                    gender="All",
                    raw_link=full_href,
                )
                self._all_loaded_products.add(product_obj)

                logger.info(
                    "Product : id=%s, name=%s, brand=%s, link=%s",
                    product_id,
                    name,
                    brand,
                    full_href,
                )

    def get_product_name(self, product):
        name_tag = product.select_one('p[data-test-id="product-card-product-name"]')
        if name_tag:
            raw_name = name_tag.get_text(strip=True)
            name = re.sub(r"\s*\(\d+\s*ml\)$", "", raw_name, flags=re.IGNORECASE)
        else:
            name = "none"
        return name

    def get_product_brand(self, product):
        brand_tag = product.select_one('p[data-test-id="headline"]')
        brand = brand_tag.get_text(strip=True) if brand_tag else "N/A"
        return brand

    def get_full_href(self, product):
        href_tag = product.select_one("a[href]")
        href = href_tag["href"] if href_tag else "N/A"
        full_href = URL + href
        return full_href

    def get_product_id(self, product):
        product_id = product.get("data-product-card-id")
        return product_id

    def load_all_product(self):
        self.load_all_product_by_url(PRODUCT_LIST, False)

    def validate_all_products(self):
        self.load_all_product()
        self.load_all_variants()

    def load_all_variants(self):
        for product in self._all_loaded_products:
            self._load_product_variant(product)

    def entry_main(self, **kwargs):
        self.login()
        self.to_json(**kwargs)

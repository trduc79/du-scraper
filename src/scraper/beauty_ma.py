from core.scraper.base import (
    BaseScraper,
    BaseProduct,
    BaseProductPage,
    BaseProductVariant,
    DummyDriver,
)
import logging
from selenium.webdriver.common.by import By
from core.file.cloud_handler import CloudHandler
from core.utils.helper import CookiesProtocol
import re
import json

HOMEPAGE = "https://www.beautysuccess.fr/"
PRODUCT_LIST_MA = "https://www.beautysuccess.fr/shop/homme/parfum-homme"
MAX_PAGE = 36

LIST_PRODUCT_SELECTOR = "li.item.product.product-item.listing"
NAME_RANGE_PRODUCT_SELECTOR = "div.product-range-label"
NAME_SUB_PRODUCT_SELECTOR="div.product-subtitle-label"
BRAND_PRODUCT_SELECTOR="div.brand-label strong"
LINK_PRODUCT_SELECTOR = "div.product.name.product-item-name a"
ID_TAG_PRODUCT_SELECTOR="button[data-product-id]"
ID_PRODUCT_SELECTOR = "data-product-id"

PRICE_DATA_ATTR = "data-price-amount"
OPTION_LABEL_ATTR = "data-option-label"
OPTION_ID_ATTR = "data-option-id"
URL_KEY_ATTR ="data-url_key"


VARIANT_TITLE_CLASS = "product-variant-title"
SWATCH_PRICE_CONTAINER_CLASS = ".swatch-price-container"
SWATCH_OPTION_CLASS = "swatch-option"

HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-US,e1n;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "User-Agent": "PostmanRuntime/7.30.0",
}
logger = logging.getLogger(__name__)


class BeautyMAProductVariant(BaseProductVariant):
    @property
    def link(self):
        return f"{self.raw_link}"


class BeautyMAProductPage(BaseProductPage):
    @property
    def link(self):
        return f"{PRODUCT_LIST_MA}?p={self.id}"


class BeautyMAProduct(BaseProduct):
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
        self._is_variants_loaded = True

    @property
    def link(self):
        return self.raw_link


class BeautyMAScraper(BaseScraper):
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
            scraper_id="beauty_ma",
            otp_generator=None,
            cloud_handler=cloud_handler,
            cookie_saver=cookie_saver,
            execution_date=execution_date,
            default_wait_seconds=default_wait_seconds,
        )
        self._all_loaded_products: set[BeautyMAProduct] = set()
        self._name = "beauty_ma"

    def get_variant_price(self, product: BeautyMAProduct) -> float:
        self.get(product.link)

        price_id = f"product-price-{product.id}"
        price_span = self.soup.find("span", id=price_id)

        if not price_span:
            logger.info("Can not find id:  %s." , price_id)
            return 0.0

        price_str = price_span.get(PRICE_DATA_ATTR)
        if not price_str:
            logger.info(
                "Can not find atribute of 'data-price-amount' in tag %s. ",price_id
            )
            return 0.0
        
        return float(price_str)

    def get_variant_volume(self, product: BeautyMAProduct) -> str:
        self.get(product.link)

        variant_container = self.soup.find("div", class_=VARIANT_TITLE_CLASS)
        if not variant_container:
            logger.info("Can not found container contain volume.")
            return None

        text = variant_container.get_text(strip=True).replace(",", ".")
        match = re.search(r"(\d+(?:\.\d+)?)\s*(g|ml)", text.lower())
        if match:
            return match.group(1)  
        else:
            logger.info("Can not find match volume.")

    def get_variant_volume_unit(self, product: BeautyMAProduct) -> str:
        self.get(product.link)

        variant_container = self.soup.find("div", class_=VARIANT_TITLE_CLASS)
        if not variant_container:
            logger.info("Can not found container contain volume_unit.")
            return None

        text = variant_container.get_text(strip=True).replace(",", ".")

        match = re.search(r"(\d+(?:\.\d+)?)\s*(g|ml)", text.lower())
        if match:
            return match.group(2) 
        else:
            logger.info("Can not find match unit")

    def get_variant_in_stock(self, product: BeautyMAProduct) -> int:

        self.get(product.link)

        scripts = self.soup.find_all("script", text=re.compile(r"in_stock"))
        for script in scripts:
            try:
                match = re.search(
                    r"dlObjects\s*=\s*(\[\{.*?\}\]);", script.string, re.DOTALL
                )
                if match:
                    json_text = match.group(1)
                    dl_objects = json.loads(json_text)
                    for obj in dl_objects:
                        if isinstance(obj, dict):
                            params = obj.get("google_tag_params")
                            if params and "in_stock" in params:
                                return 1 if params["in_stock"] else 0
                            elif "in_stock" in obj:
                                return 1 if obj["in_stock"] else 0
            except Exception:
                continue
        return 0

    def parse_price(self, price_text: str) -> float:
        return float(price_text.replace("€", "").replace(",", ".").strip())

    def _load_product_variant(self, product: BeautyMAProduct):

        self.get(product.link)
        price_containers = self.soup.select(SWATCH_PRICE_CONTAINER_CLASS)

        if not price_containers:
            logger.info(" Reload variants without using cache")
            self.get(product.link, use_cache=False)
            price_containers = self.soup.select(SWATCH_PRICE_CONTAINER_CLASS)

        if not price_containers:
            logger.warning(
                "Cannot find the variants. Try to extract product data only."
            )
            return self._get_variant_no_container(product)

        for price_container in price_containers:
            variant = price_container.find_parent("div", class_=SWATCH_OPTION_CLASS)
            if not variant:
                continue

            raw_volume = variant.get(OPTION_LABEL_ATTR) or variant.select_one("h3").get_text(strip=True)
            match = re.search(r"(\d+(?:[\.,]\d+)?)\s*(?:ml|g)?", raw_volume.lower())
            variant_volume = float(match.group(1).replace(",", ".")) if match else raw_volume
            
            variant_id = variant.get(OPTION_ID_ATTR)
            url_key = variant.get(URL_KEY_ATTR)

            link_url = f"{HOMEPAGE}{url_key}" if url_key else product.link
            sku = url_key.split("-")[-1] if url_key else None

            final_price_tag = price_container.select_one(".final_price, .price")
            variant_price = (
                self.parse_price(final_price_tag.get_text(strip=True))
                if final_price_tag
                else 0.0
            )

            logger.info(
                " Variant : %s | ID: %s | SKU: %s | Giá: %s | Link: %s",
                variant_volume,
                variant_id,
                sku,
                variant_price,
                link_url,
            )

            product.add_variant(
                BeautyMAProductVariant(
                    variant_id=variant_id,
                    product_parent=product,
                    variant_name=product.name,
                    variant_price=variant_price,
                    variant_price_unit="€",
                    variant_link=link_url,
                    variant_volume=variant_volume,
                    variant_volume_unit="ml",
                    variant_stock=self.get_variant_in_stock(product),
                )
            )

    def _get_variant_no_container(self, product):
        variant_price = self.get_variant_price(product)
        variant_volume = self.get_variant_volume(product)
        variant_volume_unit = self.get_variant_volume_unit(product)

        logger.info(
            " Variant : %s | ID: %s | Giá: %s | Link: %s",
            variant_volume,
            product.id,
            variant_price,
            product.link,
        )

        product.add_variant(
            BeautyMAProductVariant(
                variant_id=product.id,
                variant_name=product.name,
                product_parent=product,
                variant_price=variant_price,
                variant_price_unit="€",
                variant_volume=variant_volume,
                variant_volume_unit=variant_volume_unit,
                variant_link=product.link,
                variant_stock=self.get_variant_in_stock(product),
            )
        )

    def load_all_product_by_url(self, base_url: str):
        for page in range(1, MAX_PAGE + 1):
            soup = self.get(f"{base_url}?p={page}")
            products = soup.select(LIST_PRODUCT_SELECTOR)
            logger.info("Page %s have %s products.", page, len(products))

            # collecting data
            for product in products:
                try:
                    # Get name
                    name_range = product.select_one(NAME_RANGE_PRODUCT_SELECTOR)
                    name_sub = product.select_one(NAME_SUB_PRODUCT_SELECTOR)
                    name = ""
                    if name_range:
                        name += name_range.get_text(strip=True)
                    if name_sub:
                        name += f" - {name_sub.get_text(strip=True)}"
                    if not name:
                        name = "Unknown"

                    # Get brand
                    brand_tag = product.select_one(BRAND_PRODUCT_SELECTOR)
                    brand = brand_tag.get_text(strip=True) if brand_tag else "Unknown"

                    # Get link
                    name_tag = product.select_one(
                        LINK_PRODUCT_SELECTOR
                    )
                    href = name_tag.get("href") if name_tag else None
                    full_url = (
                        href
                        if href and href.startswith("http")
                        else f"https://www.beautysuccess.fr{href}" if href else None
                    )

                    # Get id
                    product_id_tag = product.select_one(ID_TAG_PRODUCT_SELECTOR)
                    product_id = (
                        product_id_tag.get(ID_PRODUCT_SELECTOR)
                        if product_id_tag
                        else None
                    )
                    product_obj = BeautyMAProduct(
                        source=HOMEPAGE,
                        product_id=product_id,
                        name=name,
                        brand=brand,
                        line="Parfum Homme",
                        gender="Male",
                        raw_link=full_url,
                    )
                    self._all_loaded_products.add(product_obj)

                    logger.info(" %s | %s | %s", product_id, name, full_url)
                except Exception as e:
                    logger.warning(" Error processing product: %s", e)

    def load_all_product(self):
        self.load_all_product_by_url(PRODUCT_LIST_MA)

    def validate_all_products(self):
        self.load_all_product()
        self.load_all_variants()

    def load_all_variants(self):
        for product in self._all_loaded_products:
            self._load_product_variant(product)

    def entry_main(self, **kwargs):
        self.login()
        self.to_json(**kwargs)

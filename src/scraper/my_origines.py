import re
import logging

from core.file.cloud_handler import CloudHandler
from core.utils.helper import CookiesProtocol
from core.scraper.base import (
    BaseScraper,
    BaseProduct,
    BaseProductPage,
    BaseProductVariant,
    DummyDriver,
)

HOMEPAGE = "https://www.my-origines.com/fr"
PRODUCT_LIST = "https://www.my-origines.com/fr/z1/parfums/all"

DIV_NEXT_PAGE = "div.pagination-container.mo-productlist-pagination.observed"
LIST_PRODUCT_SELECTOR = "article[class*='mo-producttile--']"
PRODUCT_NAME_SELECTOR = "div.mo-text-label"
PRODUCT_BRAND_SELECTOR = "div.mo-text-brand"

VARIANT_CONTAINER = "mo-productdetail-infos-size"
VARIANT_LIST = ".mo-custom-label"
SIZE_MULTI_VARIANT = "p.mo-text-pricer"
PRICE_MULTI_VARIANT = "div.mo-text-price"
ID_CONTAIN_VARIANT = "input[type='radio']"

LABEL_VARIANT = "label.mo-custom-label"
SIZE_SINGLE_VARIANT = "p.mo-text-pricer"
PRICE_SINGELE_VARIANT = "div.mo-text-price"

HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-US,e1n;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "User-Agent": "PostmanRuntime/7.30.0",
}
logger = logging.getLogger(__name__)


class MyOriginesProductVariant(BaseProductVariant):
    @property
    def link(self):
        return f"{self.raw_link}"


class MyOriginesProductPage(BaseProductPage):
    @property
    def link(self):
        return f"{PRODUCT_LIST}?page={self.id}"


class MyOriginesProduct(BaseProduct):
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


class MyOriginesScraper(BaseScraper):
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
            scraper_id="my_origines",
            otp_generator=None,
            cloud_handler=cloud_handler,
            cookie_saver=cookie_saver,
            execution_date=execution_date,
            default_wait_seconds=default_wait_seconds,
        )
        self._all_loaded_products: set[MyOriginesProduct] = set()
        self._name = "my_origines"

    def load_single_variant(self, product: MyOriginesProduct):
        variant_label = self.soup.select_one(LABEL_VARIANT)
        if not variant_label:
            logger.warning("No variant info found for single-variant product.")
            return

        variant_volume, variant_volume_unit = self.get_variant_volume_and_unit(
            variant_label
        )

        variant_price = self.get_variant_price(variant_label)

        logger.info(
            "Single Variant -> Size: %s | Unit: %s | Price: %s | ID: %s | URL: %s",
            variant_volume,
            variant_volume_unit,
            variant_price,
            product.id,
            product.link,
        )

        product.add_variant(
            MyOriginesProductVariant(
                variant_id=product.id,
                product_parent=product,
                variant_name=product.name,
                variant_price=variant_price,
                variant_price_unit="€",
                variant_link=product.link,
                variant_volume=variant_volume,
                variant_volume_unit=variant_volume_unit,
                variant_stock=True,
            )
        )
        product.added_all_variants()

    def get_variant_price(self, variant_label):
        price_tag = variant_label.select_one(PRICE_SINGELE_VARIANT)
        price_text = price_tag.get_text(strip=True) if price_tag else ""
        price_match = re.search(r"(\d+(?:[\.,]\d+)?)", price_text)
        variant_price = (
            float(price_match.group(1).replace(",", ".")) if price_match else "N/A"
        )
        return variant_price

    def get_variant_volume_and_unit(self, variant_label):
        size_elements = variant_label.select(SIZE_SINGLE_VARIANT)
        size_text = (
            size_elements[0].get_text(strip=True) if len(size_elements) > 0 else ""
        )

        match = re.search(
            r"(\d+(?:[\.,]\d+)?)\s*([a-zA-ZéÉèÈêÊàÀôÔûÛùÙîÎçÇ]+)", size_text
        )
        if match:
            variant_volume = float(match.group(1).replace(",", "."))
            variant_volume_unit = match.group(2)
        else:
            variant_volume = None
            variant_volume_unit = None
        return variant_volume, variant_volume_unit

    def _load_product_variant(self, product: MyOriginesProduct):
        self.get(product.link)

        variant_container = self.soup.find("div", class_=VARIANT_CONTAINER)
        if not variant_container:
            logger.warning(
                "Product does not have variant. Try to extract product data only."
            )
            return self.load_single_variant(product)
        
        self.load_multi_variants(product)

    def load_multi_variants(self, product:MyOriginesProduct):
        variants = self.soup.select(VARIANT_LIST)
        for variant in variants:
            variant_volume, variant_volume_unit = self.get_volume_variant(variant)

            variant_price = self.get_price_variant(variant)

            variant_id = self.get_variant_id(variant)

            full_url = re.sub(r"-\d+\.html", f"-{variant_id}.html", product.link)

            logger.info(
                    "Variant -> Size: %s %s | Price: %s | ID: %s | URL: %s",
                    variant_volume,
                    variant_volume_unit,
                    variant_price,
                    variant_id,
                    full_url,
                )

            product.add_variant(
                    MyOriginesProductVariant(
                        variant_id=variant_id,
                        product_parent=product,
                        variant_name=product.name,
                        variant_price=variant_price,
                        variant_price_unit="€",
                        variant_link=full_url,
                        variant_volume=variant_volume,
                        variant_volume_unit=variant_volume_unit,
                        variant_stock=True,
                    )
                )
        product.added_all_variants()
            
    def get_variant_id(self, variant):
        input_tag = variant.select_one(ID_CONTAIN_VARIANT)
        data_url = input_tag.get("data-url", "") if input_tag else ""
        variant_id = (
                    data_url.split("pid=")[-1].split("&")[0]
                    if "pid=" in data_url
                    else ""
                )
            
        return variant_id

    def get_price_variant(self, variant):
        price_tag = variant.select_one(PRICE_MULTI_VARIANT)
        if price_tag:
            price_text = price_tag.get_text(strip=True)
            price_match = re.search(r"([\d.,]+)", price_text)
            variant_price = (
                        float(price_match.group(1).replace(",", "."))
                        if price_match
                        else None
                    )
                
        return variant_price

    def get_volume_variant(self, variant):
        size_tag = variant.select_one(SIZE_MULTI_VARIANT)
        size_text = size_tag.get_text(strip=True) if size_tag else ""
        size_match = re.search(r"([\d.,]+)\s*([a-zA-Z]+)", size_text)

        if size_match:
            variant_volume = float(size_match.group(1).replace(",", "."))
            variant_volume_unit = size_match.group(2)
        return variant_volume,variant_volume_unit

    def get_numbers_of_page(self, base_url: str, max_pages=100) -> int:
        page = 1
        while page <= max_pages:
            logger.info("Loading page: %s", page)
            soup = self.get(f"{base_url}?page={page}")
            pagination = soup.select_one(
                DIV_NEXT_PAGE
            )
            if not pagination:
                logger.info("No pagination found. Stop!")
                break
            next_href = pagination.get("data-href", "").strip()
            if not next_href:
                logger.info("Reached last page at %s (no more data-href).", page)
                break
            page += 1
        return page

    def load_all_product_by_url(self, base_url: str):
        max_page = self.get_numbers_of_page(base_url)
        logger.info("All page: %s", max_page)
        for page in range(1, max_page  + 1):
            soup = self.get(
                f"https://www.my-origines.com/fr/z1/parfums/all?page={page}"
            )
            products = soup.select(LIST_PRODUCT_SELECTOR)
            logger.info("Page %s have %s products.", page, len(products))

            for product in products:
                a_tag = product.select_one("a[href]")

                if not a_tag:
                    continue

                product_id = self.get_product_id(a_tag)
                full_url = self.get_link_url(base_url, a_tag)
                name = self.get_product_name(product)
                brand = self.get_product_brand(product)

                product_obj = MyOriginesProduct(
                    source=HOMEPAGE,
                    product_id=product_id,
                    name=name,
                    brand=brand,
                    line="Parfum",
                    gender="All",
                    raw_link=full_url,
                )
                self._all_loaded_products.add(product_obj)

                logger.info(
                    "Product : id=%s, name=%s, brand=%s, link=%s",
                    product_id,
                    name,
                    brand,
                    full_url,
                )

    def get_product_brand(self, product):
        brand_tag = product.select_one(PRODUCT_NAME_SELECTOR)
        brand = brand_tag.get_text(strip=True) if brand_tag else ""
        return brand

    def get_product_name(self, product):
        name_tag = product.select_one(PRODUCT_NAME_SELECTOR)
        name = name_tag.get_text(strip=True) if name_tag else ""
        return name

    def get_link_url(self, base_url, a_tag):
        full_url = base_url + a_tag.get("href", "")
        return full_url

    def get_product_id(self, a_tag):
        product_id = a_tag.get("data-pid", "").strip()
        if not product_id or product_id in ("0", "None"):
            product_id = a_tag.get("href", "").strip()
        return product_id

    def load_all_product(self):
        self.load_all_product_by_url(PRODUCT_LIST)

    def validate_all_products(self):
        self.load_all_product()
        self.load_all_variants()

    def load_all_variants(self):
        for product in self._all_loaded_products:
            self._load_product_variant(product)

    def entry_main(self, **kwargs):
        self.login()
        self.to_json(**kwargs)

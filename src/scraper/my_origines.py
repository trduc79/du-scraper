from core.scraper.base import (
    BaseScraper,
    BaseProduct,
    BaseProductPage,
    BaseProductVariant,
    DummyDriver,
)
import logging
from core.file.cloud_handler import CloudHandler
from core.utils.helper import CookiesProtocol
import re
import json

HOMEPAGE = "https://www.my-origines.com/fr"
PRODUCT_LIST = "https://www.my-origines.com/fr/z1/parfums/all"
MAX_PAGE = 36

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


class My_OriginesProductVariant(BaseProductVariant):
    @property
    def link(self):
        return f"{self.raw_link}"


class My_OriginesProductPage(BaseProductPage):
    @property
    def link(self):
        return f"{PRODUCT_LIST}?page={self.id}"


class My_OriginesProduct(BaseProduct):
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


class My_OriginesScraper(BaseScraper):
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
        self._all_loaded_products: set[My_OriginesProduct] = set()
        self._name = "my_origines"
      
    def get_single_variant(self, product: My_OriginesProduct):
        variant_label = self.soup.select_one(LABEL_VARIANT)
        if not variant_label:
            logger.warning("No variant info found for single-variant product.")
            return

        #Get size
        size_elements = variant_label.select(SIZE_SINGLE_VARIANT)
        size_text = size_elements[0].get_text(strip=True) if len(size_elements) > 0 else ""

        match = re.search(r"(\d+(?:[\.,]\d+)?)\s*([a-zA-ZéÉèÈêÊàÀôÔûÛùÙîÎçÇ]+)", size_text)
        if match:
            variant_volume = float(match.group(1).replace(",", "."))
            variant_volume_unit = match.group(2)
        else:
            variant_volume = None
            variant_volume_unit = None
        #Get price
        price_tag = variant_label.select_one(PRICE_SINGELE_VARIANT)
        price_text = price_tag.get_text(strip=True) if price_tag else ""
        price_match = re.search(r"(\d+(?:[\.,]\d+)?)", price_text)
        variant_price = float(price_match.group(1).replace(",", ".")) if price_match else "N/A"
        

        logger.info(
            "Single Variant -> Size: %s | Unit: %s | Price: %s | ID: %s | URL: %s",
            variant_volume, variant_volume_unit, variant_price, product.id, product.link
        )
        
        product.add_variant(
            My_OriginesProductVariant(
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
        
    def _load_product_variant(self,product: My_OriginesProduct):
        self.get(product.link)
        
        variant_container = self.soup.find( "div" ,class_= VARIANT_CONTAINER)
        if  not variant_container:
            logger.warning(
                "Product does not have variant. Try to extract product data only."
            )
            return self.get_single_variant(product)
        else:
            variants = self.soup.select(VARIANT_LIST)
            for variant in variants:
                size_tag = variant.select_one(SIZE_MULTI_VARIANT)
                size_text = size_tag.get_text(strip=True) if size_tag else ""
                size_match = re.search(r"([\d.,]+)\s*([a-zA-Z]+)", size_text)

                if size_match:
                    variant_volume = float(size_match.group(1).replace(",", "."))
                    variant_volume_unit = size_match.group(2)

                price_tag = variant.select_one(PRICE_MULTI_VARIANT)
                if price_tag:
                    price_text = price_tag.get_text(strip=True)
                    price_match = re.search(r"([\d.,]+)", price_text)
                    variant_price = float(price_match.group(1).replace(",", ".")) if price_match else None

                
                input_tag = variant.select_one(ID_CONTAIN_VARIANT)
                data_url = input_tag.get("data-url", "") if input_tag else ""
                variant_id = data_url.split("pid=")[-1].split("&")[0] if "pid=" in data_url else ""

                full_url = re.sub(r"-\d+\.html", f"-{variant_id}.html", product.link)

                logger.info(
                    "Variant -> Size: %s %s | Price: %s | ID: %s | URL: %s",
                    variant_volume, variant_volume_unit, variant_price, variant_id, full_url
                )
                
                product.add_variant(
                My_OriginesProductVariant(
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
                            
    def load_all_product_by_url(self, base_url: str):
        for page in range(1, 6):
            soup = self.get(f"https://www.my-origines.com/fr/z1/parfums/all?page={page}")
            products = soup.select(LIST_PRODUCT_SELECTOR)
            logger.info("Page %s have %s products.", page, len(products))
            
            for product in products:
                a_tag = product.select_one("a[href]")
                
                if not a_tag:
                    continue
                #Get id 
                
                product_id = a_tag.get("data-pid", "")
                
                #Get link 
                full_url = base_url + a_tag.get("href", "")

                # Get name
                name_tag = product.select_one(PRODUCT_NAME_SELECTOR)
                name = name_tag.get_text(strip=True) if name_tag else ""
                
                #Get brand
                brand_tag = product.select_one(PRODUCT_NAME_SELECTOR)
                brand = brand_tag.get_text(strip=True) if brand_tag else ""

                product_obj = My_OriginesProduct(
                        source=HOMEPAGE,
                        product_id=product_id,
                        name=name,
                        brand=brand,
                        line="Parfum",
                        gender="All",
                        raw_link=full_url,
                    )
                self._all_loaded_products.add(product_obj)
                    
                logger.info("Product : id=%s, name=%s, brand=%s, link=%s", product_id, name, brand, full_url)

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

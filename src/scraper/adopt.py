import logging

from selenium.common.exceptions import NoSuchElementException
from core.file.cloud_handler import CloudHandler
from core.utils.helper import CookiesProtocol
import json
import re
from core.scraper.base import (
    BaseScraper,
    BaseProduct,
    BaseProductPage,
    BaseProductVariant,
    DummyDriver,
)


HOMEPAGE = "https://www.adopt.com"
PRODUCT_BASE_URL = f"{HOMEPAGE}/fr"
PRODUCT_LIST = f"{PRODUCT_BASE_URL}/parfum.html"
LIST_PRODUCT_SELECTOR = "a.product-item"

OPTION_OF_PRODUCT = "label.pill-radio-capacity"
VARIANT_DESC = "span.short-description-container"
VARIANT_NAME_SELECTOR = "font-romie font-bold flex gap-2 items-center justify-between"
VARIANT_ID_SELECTOR = 'data-wishlist'
VARIANT_ALERT_SELECTOR = "alert_container"

END_PAGE_SELECTOR = 'span.text-purple.font-primary.font-semibold.xl\\:text-smaller.text-xs[x-show="wording"]'
 
FORM_ID_SELECTOR = "product_addtocart_form"
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
        return f"{self.product_parent.link}/?contenance={int(self.volume)}{self.volume_unit}"


class AdoptProduct(BaseProduct):

    @property
    def default_variant_id(self) -> str:
        return "000000"

    @property
    def link(self):
        return f"{self.raw_link}"


class AdoptProductPage(BaseProductPage):
    @property
    def link(self):
        return f"{PRODUCT_LIST}?/p={self.id}"


class AdoptScraper(BaseScraper):
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
            scraper_id="adopt",
            otp_generator=None,
            cloud_handler=cloud_handler,
            cookie_saver=cookie_saver,
            execution_date=execution_date,
            default_wait_seconds=default_wait_seconds,
        )
        self._loaded_pages: dict[str, set[AdoptProductPage]] = {}
        self._all_loaded_products: set[AdoptProduct] = set()
        self._name = "adopt"


    def find_variants_option(self, product: AdoptProduct):

        if not product.link:
            return 0

        logger.info("Loading product detail page: %s", product.link)

        self.get(product.link)
        
        try:
            form = self.soup.find(id="product_addtocart_form")
        except NoSuchElementException:
            logger.warning(
                "Can not find variant of product: %s", product.link
            )
            return 0
        if not form:
            logger.warning(
                "Can not find variant of product: %s", product.link
            )
            return 0 
        

        options = form.select(OPTION_OF_PRODUCT)
        valid_options = [
            opt for opt in options if re.search(r"\d+\s*ml", opt.text.strip().lower())
        ]
        if options:
            logger.info(
                "Find %d variants of product: %s",
                len(valid_options),
                product.link,
            )
            return len(options)

        desc_container = self.soup.select_one(VARIANT_DESC)
        if desc_container:
            desc_text = desc_container.get_text(strip=True)
        else:
            desc_text = ""

        ml_matches = re.findall(r"\d{1,4}\s*ml", desc_text.lower())

        if len(ml_matches) == 1 and "+" not in desc_text:
            match = re.search(
                r"(eau de parfum.*?\d{1,4}\s*ml)", desc_text, re.IGNORECASE
            )
            if match:
                variant_name = match.group(1).strip()
                logger.info("No variant. Try to extract data only: %s", variant_name)
                return 1
            else:
                logger.warning(
                    "Description have 1 volume not right: %s", desc_text
                )
                return 0

        if "+" in desc_text or "ml" not in desc_text.lower():
            logger.warning("Description is unclear: %s", desc_text)
            return 0

        logger.warning("Can not find variant of product: %s", product.link)
        return 0

    def get_variant_volume(self, product: AdoptProduct):
        self.get(product.link)

        desc_container = self.soup.select_one(VARIANT_DESC)
        if desc_container:
            desc_text = desc_container.get_text(strip=True)
        else:
            desc_text = ""

        match = re.search(r"(\d{1,4})\s*ml", desc_text.lower())
        if match:
            volume = int(match.group(1))
            logger.info("Find volume: %dml from : %s", volume, desc_text)
            return volume
        else:
            logger.warning("Can not find volume: %s", desc_text)
            return None

    def get_variant_price(self, product: AdoptProduct):
        self.get(product.link)

        meta_price = self.soup.find("meta", attrs={"property": "product:price:amount"})
        if not meta_price:
            logger.info("Can not find tag meta  %s", product.link)
            return None

        price_text = meta_price.get("content")
        try:
            price = float(price_text)
            return price
        except (TypeError, ValueError):
            logger.warning("Can not prase price '%s' into number", price_text)
            return None
        
    def get_variant_name(self, product: AdoptProduct):
        self.get(product.link)
        
        name_text = self.soup.find("div", class_ = VARIANT_NAME_SELECTOR)
        if not name_text:
            logger.info("Can not find name of variant")
            return None
        return name_text.get_text(strip=True)
        
    def get_variant_id(self, product: AdoptProduct):
        self.get(product.link)
        
        btn = self.soup.find('button', attrs={'data-wishlist': True})
        if btn:
            product_id = btn.get(VARIANT_ID_SELECTOR)
            return product_id
        
    def get_all_variants(self, product: AdoptProduct):
        self.get(product.link)

        scripts = self.soup.find_all("script")
        script_text = ""

        for script in scripts:
            if script.string and "initConfigurableSwatchOptions_" in script.string:
                script_text = script.string
                break

        if not script_text:
            logger.info("Can not find script contain initConfigurableSwatchOptions_")
            return {}

        pattern = r'initConfigurableOptions\(\s*[\'"]\d+[\'"]\s*,\s*(\{.*?})(?=\s*\);)'
        match = re.search(pattern, script_text, re.DOTALL)

        if not match:
            logger.info("Can not find JSON in  initConfigurableOptions")
            return {}

        raw_json_text = match.group(1)

        try:
            json_text = re.sub(r',(\s*[}\]])', r'\1', raw_json_text)
            json_text = json_text.replace("'", '"')
            json_text = re.sub(r'([,{]\s*)(\w+)(\s*:)', r'\1"\2"\3', json_text)
            json_text = json_text.replace("False", "false").replace("True", "true").replace("None", "null")
            json_text = json_text.strip().lstrip('\ufeff')

            data = json.loads(json_text)
            attribute_options = data.get("attributes", {})
            option_prices = data.get("optionPrices", {})
            salable_dict = data.get("salable", {})

            results = {}  # size (float) -> (variant_id, final_price, in_stock)

            for attr in attribute_options.values():
                attr_id = str(attr["id"])
                salable = salable_dict.get(attr_id, {})

                for option in attr.get("options", []):
                    label = option.get("label", "")
                    products = option.get("products", [])
                    option_id = str(option.get("id"))

                    if not products:
                        continue

                    variant_id = products[0]
                    in_stock = variant_id in salable.get(option_id, [])

                    size_match = re.search(r"(\d+(?:[.,]\d+)?)\s*ml", label.lower())
                    if size_match:
                        size = float(size_match.group(1).replace(",", "."))
                        final_price = option_prices.get(variant_id, {}).get("finalPrice", {}).get("amount", 0)
                        results[size] = (variant_id, final_price, in_stock)

            return results

        except Exception as e:
            logger.info("Lỗi xử lý JSON: %s",e)
            return {}
    
    def get_variant_stock(self, product: AdoptProduct) -> int:
        self.get(product.link)

        form = self.soup.find(id=FORM_ID_SELECTOR)
        if not form:
            logger.warning("Can not find form in variant %s", product.link)
            return 1  

        alert_div = self.soup.find("div", id=VARIANT_ALERT_SELECTOR)
        if alert_div and "display: none" not in alert_div.get("style", ""):
            logger.info("Variant is out_of_stock")
            return 0  

        logger.info("Variant in_stock")
        return 1  
    
    def _load_product_variant(self, product: AdoptProduct):
        num_variants = self.find_variants_option(product)

        if num_variants == 0:
            logger.warning("Product does not have variant: %s", product.link)
            return

        if num_variants == 1:
            variant_id = self.get_variant_id(product)
            variant_name = self.get_variant_name(product)
            variant_price = self.get_variant_price(product)
            variant_price_unit = "€"
            variant_volume = self.get_variant_volume(product)
            variant_volume_unit = "ml"

            product.add_variant(
                AdoptProductVariant(
                    variant_id=variant_id,
                    variant_name=variant_name,
                    product_parent=product,
                    variant_price=variant_price,
                    variant_price_unit=variant_price_unit,
                    variant_volume=variant_volume,
                    variant_volume_unit=variant_volume_unit,
                    variant_stock=self.get_variant_stock(product)
                )
            )
            logger.info("Product have 1 variant : %s", variant_name)
            return

        logger.info("Product has many variants: %s", product.link)
        self.get(product.link)

        variants_info = self.get_all_variants(product)
        for size_ml, (variant_id, price, in_stock) in variants_info.items():
            product.add_variant(
                AdoptProductVariant(
                    variant_id=variant_id,
                    product_parent=product.id,
                    variant_name=product.name,
                    variant_price=price,
                    variant_price_unit="€",
                    variant_volume=size_ml,
                    variant_volume_unit="ml",
                    variant_stock=in_stock
                )
            )
        return 
                
            
    def get_number_of_pages(self, max_pages=100):
        page = 1
        while page <= max_pages:
            logger.info("Loading page: %s",page)
            soup = self.get(f"{PRODUCT_LIST}?p={page}")

            end_of_selection = soup.select_one(
                END_PAGE_SELECTOR
            )

            if end_of_selection and "Fin de sélection" in end_of_selection.get_text(
                strip=True
            ):
                logger.info(
                    "End in page %s due to show up 'Fin de sélection ",page
                )
                break

            page += 1
        return page

    def load_all_product(self):
        max_page = self.get_number_of_pages()
        logger.info("📄 All page : %s",max_page)

        for page in range(1,max_page + 1):
            soup = self.get(f"{PRODUCT_LIST}?p={page}")
            products = soup.select(LIST_PRODUCT_SELECTOR)
            scripts = soup.find_all(
                "script", text=re.compile(r"function initItemProduct_")
            )

            logger.info("Page %s have %s product and %s script.",page, len(products), len(scripts))

            for product, script in zip(products, scripts):
                try:
                    content = script.text or ""
                    match = re.search(
                        r"function initItemProduct_\w+\(\)\s*{\s*return\s*{\s*currentProductData\s*:\s*{(.*?)}\s*[,}]",
                        content,
                        re.DOTALL,
                    )

                    if not match:
                        logger.warning("Can not find data 'currentProductData'  %d", page)
                        continue

                    block = match.group(1).encode().decode("unicode_escape")
                    block = (
                        block.replace("\\'", "'")
                        .replace('\\"', '"')
                        .replace("\\\\", "\\")
                        .strip()
                    )

                    id_match = re.search(r"'id'\s*:\s*'([^']+)'", block)
                    name_match = re.search(r"'name'\s*:\s*'([^']+)'", block)

                    product_id = id_match.group(1) if id_match else ""
                    name = name_match.group(1) if name_match else ""


                    href = product.get("href", "")
                    full_url = HOMEPAGE + href if href.startswith("/") else href
                    

                    product_obj = AdoptProduct(
                        source=HOMEPAGE,
                        product_id=product_id,
                        name=name,
                        brand="Adopt",
                        line="Adopt",
                        raw_link=full_url,
                    )
                    self._all_loaded_products.add(product_obj)

                    logger.info("%s | %s | %s", product_id, name, full_url)

                except Exception as e:
                    logger.warning("Error : %s",e)

    def validate_all_products(self):
        self.load_all_product()
        self.load_all_variants()

    def load_all_variants(self):
        for product in self._all_loaded_products:
            self._load_product_variant(product)

    def entry_main(self, **kwargs):
        self.login()
        self.to_json(**kwargs)

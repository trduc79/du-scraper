"""
This module provides functionality for scraping product data from the Nocibe website.
It includes classes and methods to represent products, product variants, product pages,
and a scraper to extract and process data from the website.

Classes:
    NocibeProductVariant:
        Represents a product variant with attributes such as ID, name, price, volume,
        and parent product.

    NocibeProduct:
        Represents a product with attributes such as ID, name, line, category, gender,
        and associated variants.

    NocibeProductPage:
        Represents a page of products with attributes such as page number
        and a collection of products.

    NocibeScraper:
        A scraper class that extends the BaseScraper to extract product data
        from the Nocibe website.

"""

import logging
import re

from bs4 import BeautifulSoup as BS

from selenium.webdriver.remote.webdriver import WebDriver


from ..file.cloud_handler import CloudHandler
from ..utils.helper import CookiesProtocol

from .base import BaseScraper, BaseProductPage, BaseProduct, BaseProductVariant


HOMEPAGE = "https://www.nocibe.fr"
PERFUME_LIST = f"{HOMEPAGE}/fr/c/parfum/01"
PRODUCT_BASE_URL = f"{HOMEPAGE}/fr/p/"

BY_ATTR_TEST_ID = "data-testid"
BY_ATTR_DETAIL_LINK = "details-link"
BY_ATTR_TEST_ID_VALUE_PAGE = "pagination-title-dropdown"
BY_ATTR_RADIO_BUTTON = "RadioButton"
BY_ATTR_STRUCTURE_DATA = "structured-data-script"
BY_ATTR_PRODUCT_DETAIL = "product-details-description"

BY_XPATH_ACCEPT_COOKIES = "//*[@data-testid='uc-accept-all-button']"

BY_CLASS_PRODUCT_CATEGORY = "text category"
BY_CLASS_PRODUCT_LINE = "text brand-line"
BY_CLASS_PRODUCT_NAME = "text top-brand"
BY_CLASS_PRODUCT_NAME_2 = "text name"
BY_CLASS_PRODUCT_ROW = "product-detail__variant-row--spread-content"
BY_CLASS_PRODUCT_DESCRIPTION = "product-details__description"
BY_CLASS_UNIT = "product-price__extended-content-units"

BY_CLASS_TOTAL_PRODUCT = "product-overview__headline-wrapper"

DEFAULT_VOLUME = 30
DEFAULT_VOLUME_UNIT = "ml"

logger = logging.getLogger(__name__)


class NocibeProductVariant(BaseProductVariant):
    @property
    def link(self):
        if self.id == "-1":
            logger.warning("No variant ID found, return the parent link instead!")
            return self.product_parent.raw_link

        return f"{PRODUCT_BASE_URL}{self.product_parent.id}?variant={self.id}"


class NocibeProduct(BaseProduct):
    @property
    def default_variant_id(self) -> str:
        match = re.search(r"/p/\d+\?variant=(\d+)", self.raw_link)
        if match:
            return match.group(1)
        logger.debug("Do not have default variant for: %s", self.raw_link)
        return -1

    @property
    def link(self):
        return f"{PRODUCT_BASE_URL}{self.id}"


class NocibeProductPage(BaseProductPage):
    @property
    def link(self):
        return f"{PERFUME_LIST}?page={self.id}"


class NocibeScraper(BaseScraper):
    def __init__(
        self,
        driver: WebDriver,
        run_id: str,
        cloud_handler: CloudHandler,
        cookie_saver: CookiesProtocol,
        execution_date=None,
        default_wait_seconds=10,
    ):
        super().__init__(
            driver=driver,
            run_id=run_id,
            scraper_id="nocibe",
            otp_generator=None,
            cloud_handler=cloud_handler,
            cookie_saver=cookie_saver,
            execution_date=execution_date,
            default_wait_seconds=default_wait_seconds,
        )
        self._current_page = 1
        self._total_products = -1
        self._total_pages = -1
        self._loaded_pages: dict[int, NocibeProductPage] = {}
        self._all_loaded_products: set[NocibeProduct] = set()
        self._name = "nocibe"

    @property
    def total_pages(self):
        if self._total_pages > 0:
            return self._total_pages

        soup = self.get(PERFUME_LIST)
        total_pages = self.soup_find_all_by_attribute(
            BY_ATTR_TEST_ID, BY_ATTR_TEST_ID_VALUE_PAGE, soup=soup
        )
        if not total_pages:
            logger.warning("No pagination found on the page.")
            return 0
        if len(total_pages) > 1:
            logger.warning("There too many pagination found on the page.")
            return 0
        page_text = total_pages[-1].get_text().strip().split(" ")[-1]
        page_text = re.sub(r"[^\d]", "", page_text)
        no_pages = int(page_text)

        logger.info("Total pages: %s", no_pages)

        self._total_pages = no_pages
        return self._total_pages

    @property
    def total_loaded_products(self):
        return len(self._all_loaded_products)

    @property
    def total_products_in_pages(self):
        return sum([len(page.children) for page in self._loaded_pages.values()])

    @property
    def total_loaded_variants(self):
        return sum([p.number_of_variants for p in self._all_loaded_products])

    @property
    def total_products_from_web(self):
        if self._total_products > 0:
            logger.info("Total products (cached): %s", self._total_products)
            return self._total_products

        self.get(PERFUME_LIST)
        total_products = self.soup_find_all_by_class(BY_CLASS_TOTAL_PRODUCT)

        if not total_products:
            logger.warning("No products found on the page.")
            return 0

        if len(total_products) > 1:
            logger.warning("There are too many `total products` found on the page.")
            return 0

        no_products_txt = re.sub(
            r"[^\d]", "", total_products[-1].get_text().split("(")[-1]
        )
        no_products = int(no_products_txt)
        self._total_products = no_products
        logger.info("Total products live on page: %s", no_products)
        return self._total_products

    def _get_product_id_from_url(self, url: str):
        """Extract product ID from the URL."""
        match = re.search(r"/p/([a-z0-9]+)(?:\?variant=\d+)?", url)
        if match:
            return match.group(1)
        logger.debug("Cannot find product ID in URL: %s", url)
        return -1

    def _get_variant_id_from_url(self, url: str):
        """Extract product ID from the URL."""
        match = re.search(r"/p/\d+\?variant=(\d+)", url)
        if match:
            return match.group(1)
        logger.debug("Cannot find variant ID in URL: %s", url)
        return -1

    def get_product_page(self, page_no: int):
        if page_no in self._loaded_pages:
            logger.info("Page %s already loaded.", page_no)
            return self._loaded_pages[page_no]

        soup = self.get(f"{PERFUME_LIST}?page={page_no}")
        product_page = NocibeProductPage(page_identifier=page_no)
        products = soup.select(f'a[{BY_ATTR_TEST_ID}="{BY_ATTR_DETAIL_LINK}"]')
        for product in products:
            raw_url = f"{HOMEPAGE}{product.get("href")}"
            product_id = self._get_product_id_from_url(raw_url)
            name = product.find("div", class_=BY_CLASS_PRODUCT_NAME)
            if name:
                name = name.get_text()
            else:
                name = product.find("div", class_=BY_CLASS_PRODUCT_NAME_2)
                if not name:
                    logger.warning("Cannot find product name for %s", product_id)
                else:
                    name = name.get_text()
            line = product.find("div", class_=BY_CLASS_PRODUCT_LINE)
            if line:
                line = line.get_text()
            category = product.find("div", class_=BY_CLASS_PRODUCT_CATEGORY)
            if category:
                category = category.get_text()
            product_page.add_product(
                NocibeProduct(
                    source=HOMEPAGE,
                    product_id=product_id,
                    name=name,
                    brand=line,
                    line=category,
                    raw_link=raw_url,
                )
            )
        self._loaded_pages[page_no] = product_page

        return product_page

    def get_variant_info_radio_style(self, variant: BS, product: NocibeProduct = None):
        variant_id = variant.find_next("input", class_="radio-item__input").get("value")
        variant_name: str = variant.find_next(
            "div", class_="product-detail__variant-name"
        ).get_text()
        variant_price_text = variant.find_next(
            "span", class_="product-price__price"
        ).get_text()
        cleaned_price_text = self.clean_text(variant_price_text)

        variant_price = float(
            cleaned_price_text.split(" ")[0].replace(",", ".").strip()
        )
        variant_price_unit = cleaned_price_text.split(" ")[-1].strip()

        try:
            volume = float(variant_name.split(" ")[0].replace("ml", "").strip())
        except ValueError:
            logger.warning(
                "Cannot find volume in first word of variant name: %s", variant_name
            )
            logger.info(
                "Trying to find volume in 2nd last word of variant name: %s",
                variant_name,
            )
            volume = float(variant_name.split(" ")[-2].replace("ml", "").strip())

        volume_unit = (
            "ml"
            if "ml" in variant_name
            else variant_name.split(" ")[-1].strip() or "ml"
        )

        return NocibeProductVariant(
            variant_id=variant_id,
            variant_name=variant_name,
            product_parent=product,
            variant_price=variant_price,
            variant_price_unit=variant_price_unit,
            variant_volume=volume,
            variant_volume_unit=volume_unit,
        )

    def get_product_variants(self, product: NocibeProduct):
        """Get product variants from the product page."""
        if product in self._all_loaded_products:
            logger.info("Already loaded product! %s", product.link)
            return

        self.get(product.link)

        variants = self.soup_find_all_by_attribute(
            BY_ATTR_TEST_ID, BY_ATTR_RADIO_BUTTON
        )
        if not variants:
            logger.warning("No variants Radio style found for product %s", product.link)
            logger.info(
                "Trying to find variants in structured data. Will use default variant id (if any)."
            )
            variants = self.soup_find_all_by_class(BY_CLASS_PRODUCT_ROW)

        if not variants:
            logger.error("No variants found for product %s", product.link)

        for variant in variants:
            variant_id = self.get_variant_id(product, variant)
            variant_name = self.get_variant_name(variant)
            variant_price, variant_price_unit = self.get_variant_price(variant)
            variant_volume, variant_volume_unit = self.get_variant_volume(variant)

            product.add_variant(
                NocibeProductVariant(
                    variant_id=variant_id,
                    variant_name=variant_name,
                    product_parent=product,
                    variant_price=variant_price,
                    variant_price_unit=variant_price_unit,
                    variant_volume=variant_volume,
                    variant_volume_unit=variant_volume_unit,
                )
            )

        product.added_all_variants()
        self._all_loaded_products.add(product)

    def _get_variant_volume_normal_case(self, variant: BS):
        variant_name = self.get_variant_name(variant)
        try:
            volume = float(variant_name.split(" ")[0].replace("ml", "").strip())
            unit = variant_name.split(" ")[1]
            return volume, unit
        except ValueError:
            logger.warning(
                "Cannot find volume in first word of variant name: %s", variant_name
            )
            return None, None
        except IndexError:
            logger.error("Cannot find the unit!")
            return None, None

    def get_variant_volume(self, variant: BS):
        variant_name = self.get_variant_name(variant)

        if variant_name == "3X20 ml - Recharges":
            return 20, DEFAULT_VOLUME_UNIT

        volume, unit = self._get_variant_volume_normal_case(variant)
        if volume:
            return volume, unit

        logger.info(
            "Trying to find volume in 2nd last word of variant name: %s",
            variant_name,
        )

        volume_text: str = variant_name.split(" ")
        if len(volume_text) >= 2 and volume_text[-2].replace(",", ".").isnumeric():
            volume = float(volume_text[-2].replace(",", "."))
            return volume, DEFAULT_VOLUME_UNIT

        logger.warning("Cannot find the 2nd last word! Finding the price per volume...")
        price_per_100mil = self.get_price_per_volume(variant)
        if price_per_100mil:
            variant_price, _ = self.get_variant_price(variant)
            volume = round(variant_price / price_per_100mil * 100, 0)
            return volume, DEFAULT_VOLUME_UNIT

        logger.error("Cannot find numeric volume! Try to use last digit")

        volume = re.split(r"\D+", variant_name)[-1]
        if not volume.isnumeric():
            logger.error("Cannot find any volume, return default volume!")
            return DEFAULT_VOLUME, DEFAULT_VOLUME_UNIT

        volume = float(volume)
        volume_unit = (
            DEFAULT_VOLUME_UNIT
            if DEFAULT_VOLUME_UNIT in variant_name
            else variant_name.split(" ")[-1] or DEFAULT_VOLUME_UNIT
        )

        return volume, volume_unit

    def get_variant_price(self, variant: BS):
        variant_price_text = variant.find_next(
            "span", class_="product-price__price"
        ).get_text()
        cleaned_price_text = self.clean_text(variant_price_text)

        variant_price = float(
            cleaned_price_text.split(" ")[0].replace(",", ".").strip()
        )
        variant_price_unit = cleaned_price_text.split(" ")[-1].strip()
        return variant_price, variant_price_unit

    def get_variant_name(self, variant: BS) -> str:
        variant_name = variant.find_next("div", class_="product-detail__variant-name")
        if not variant_name:
            return "__UNKNOWN_NAME"

        variant_name = variant_name.get_text().strip()

        return variant_name

    def get_variant_id(self, product: NocibeProduct, variant: BS):
        variant_id = variant.find_next("input", class_="radio-item__input")
        if not variant_id:
            return product.default_variant_id

        return variant_id.get("value", product.default_variant_id)

    def get_price_per_volume(self, variant: BS):
        unit = variant.find_next("span", class_=BY_CLASS_UNIT)
        if not unit:
            logger.warning("Cannot find price per volume")
            return

        price_per_100mil = float(
            self.clean_text(unit.get_text()).split(" ")[0].replace(",", ".")
        )
        return price_per_100mil

    def load_all_product_variants(self):
        """Get all product variants from all loaded pages."""
        for page in self._loaded_pages.values():
            for product in page:
                if product.is_variants_loaded:
                    continue
                self.get_product_variants(product)

    def load_all_pages(self):
        """Load all product pages."""
        for page_no in range(1, self.total_pages + 1):
            logger.info("Loading page %s", page_no)
            self.get_product_page(page_no)

    def validate_all_products(self, raise_error: bool = False):
        """Validate all products."""
        self.load_all_pages()
        self.load_all_product_variants()

        if self.total_products_in_pages != self.total_products_from_web:

            logger.warning(
                "Total (non-unique) products loaded (%s) vs. the total products (%s)",
                self.total_products_in_pages,
                self.total_products_from_web,
            )

            logger.warning(
                "Total unique products loaded (%s) vs. the total products (%s)",
                self.total_loaded_products,
                self.total_products_from_web,
            )

            logger.warning(
                "Total unique variants loaded (%s) vs. the total products (%s)",
                self.total_loaded_variants,
                self.total_products_from_web,
            )

            if raise_error:
                raise ValueError(
                    f"Total products loaded ({self.total_loaded_products}) does not match the total products ({self.total_products_from_web})"
                )
            return

        logger.info(
            "Total unique products loaded (%s) matches the total products (%s)",
            self.total_loaded_products,
            self.total_products_from_web,
        )

    def entry_main(self, **kwargs):
        self.login()
        self.to_json(**kwargs)

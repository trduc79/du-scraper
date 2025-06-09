from abc import ABC, abstractmethod
from datetime import datetime, timezone
from hashlib import md5
import json
import logging
import os
import random
import re
import string
from time import sleep
from typing import Literal
import uuid

from bs4 import BeautifulSoup as BS
from bs4.element import ResultSet

import requests

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .models import ScraperOutput

from ..file.cloud_handler import CloudHandler
from ..file import file_handler as fh
from ..otp.otp_generator import BaseOTPGenerator
from ..utils import constant as cct
from ..utils import money as mn
from ..utils.helper import (
    CookiesProtocol,
    StateSaver,
    make_safe_file_name,
    parse_response,
)
from ..utils.types import Gender

logger = logging.getLogger(__name__)

NON_PRINTABLE_PATTERN = f"[^{re.escape(f"{string.printable}$€")}]"

DEFAULT_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "User-Agent": cct.DEFAULT_USER_AGENT,
}

GenderType = Literal["F", "M", "all"]


class DummyDriver:

    def quit(self):
        logger.info("Quitting dummy driver")

    def get(self, url: str):
        logger.info("Dummy driver get: %s", url)


class BaseItem(ABC):

    id: str
    children: set

    @property
    @abstractmethod
    def link(self): ...

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, BaseItem):
            return self.id == other.id
        return False

    def __iter__(self):
        """Allow iteration over products in the ProductPage."""
        return iter(self.children)

    def __str__(self):
        return f"{self.__class__.__name__}( {self.link} )"

    def __repr__(self):
        return self.__str__()


class BaseProductPage(BaseItem):
    def __init__(
        self,
        page_identifier: int,
        products: set | None = None,
        category: str | None = None,
    ):
        super().__init__()
        self.id = f"{category}:{page_identifier}"
        self.page_no = page_identifier
        self.children: set["BaseProduct"] = products or set()
        self.category: str = category

    def __iter__(self):
        """Allow iteration over products in the ProductPage."""
        return iter(self.children)

    def add_product(self, product: "BaseProduct"):
        self.children.add(product)

    def remove_product(self, product: "BaseProduct"):
        self.children.discard(product)

    def get_product(self, product_id: str):
        for product in self.children:
            if product.id == product_id:
                return product
        return None


class BaseProduct(BaseItem):
    def __init__(
        self,
        source: str,
        product_id: str,
        name: str,
        brand: str,
        line: str,
        gender: GenderType = Gender.ALL,
        raw_link: str = "",
    ):
        super().__init__()
        self.source = source
        self.id = product_id
        self._name = name
        self.brand = brand
        self.line = line
        self.gender = gender
        self.raw_link = raw_link
        self.children: set["BaseProductVariant"] = set()
        self._is_variants_loaded: bool = False

    def __iter__(self):
        """Allow iteration over products in the ProductPage."""
        return iter(self.children)

    @property
    def is_variants_loaded(self) -> bool:
        return self._is_variants_loaded

    @property
    def name(self) -> str:
        """Return the name of the product."""
        name = self._format_name(self._name)
        return name

    @property
    def number_of_variants(self) -> int:
        return len(self.children)


    def _format_name(self, name: str) -> str:
        if not name:
            return name
        org_name = name
        name = name.split(" EDP ")[0]
        name = name.split(" EDT ")[0]
        name = name.split(" EAU ")[0]
        
        pattern = (
            r'(?i)-?\s?('
            'Eau de parfum rechargeable'
            '|Eau de parfum'
            '|Eau de toilette'
            '|Eau de cologne'
            '|Eau fraîche'
            '|Cologne Intense'
            '|Recharge'
            '|rechargeable'
            '|Recharge Eau de Toilette Florale Florale'
            '|Parfum Recharge'
            '|Extrait de parfum'
            '|Elixir de Parfum'
            '|Eau de Parfum Femme florale'
            '|Parfum Remarquable'
            r')\s?-?'
        )
        name = re.sub(pattern, '', name)
        name = name.replace("  ", " ")
        if not name:
            return org_name.strip()
        
        return name.strip()

    def add_variant(self, variant: "BaseProductVariant"):
        if variant in self.children:
            return
        self.children.add(variant)
        variant.update_product_parent(self)

    def remove_variant(self, variant: "BaseProductVariant"):
        self.children.discard(variant)
        variant.update_product_parent(None)

    def added_all_variants(self):
        """Finalize the addition of variants."""
        self._is_variants_loaded = True


class BaseProductVariant(BaseItem):
    def __init__(
        self,
        variant_id: str,
        variant_name: str,
        product_parent: "BaseProduct",
        variant_price: float,
        variant_volume: float,
        variant_price_unit: str = "€",
        variant_volume_unit: str = "ml",
        variant_link: str = "",
        variant_stock: int = 0,
        is_sampling: bool = False,
    ):
        super().__init__()
        self.id = str(variant_id)
        self.name = variant_name
        self.product_parent = product_parent
        self.price = variant_price
        self.volume = variant_volume
        self.price_unit = variant_price_unit
        self.volume_unit = variant_volume_unit
        self.raw_link = variant_link
        self.variant_stock = variant_stock
        self.is_sampling = is_sampling

    @property
    def in_stock(self) -> bool:
        return self.variant_stock > 0

    @property
    def iso_price_unit(self):
        if self.price_unit in mn.CURRENCY_MAP.values():
            return self.price_unit

        iso_unit = mn.convert_currency_symbol_to_iso(self.price_unit)
        return iso_unit

    @property
    def iso_volume_unit(self):
        if not self.volume_unit:
            return None
        return self.volume_unit.lower()

    @property
    def price_per_volume(self):
        if self.volume and self.price:
            return round(self.price / self.volume, 2)
        return None

    def update_product_parent(self, product_parent: "BaseProduct"):
        if self.product_parent == product_parent:
            logger.debug(
                "No need to change to %s, already is a parent!", product_parent
            )
            return
        self.product_parent = product_parent
        if self.product_parent is not None:
            self.product_parent.add_variant(self)

    def to_scraper_ouput(self) -> ScraperOutput:
        """Convert to ScraperOutput object."""
        return ScraperOutput(
            source=self.product_parent.source,
            parent_perfume_id=self.product_parent.id,
            id=self.id,
            price=self.price,
            currency=self.iso_price_unit,
            size=self.volume,
            size_unit=self.iso_volume_unit,
            link=self.link,
            line=self.product_parent.line,
            vendor=self.product_parent.brand,
            sku=self.id,
            is_sampling=self.is_sampling,
            in_stock=self.in_stock,
        )


class BaseScraper:
    """
    The abstract Scraper contains structure and helper functions.
    Child Scraper must implement `login()`, `get_otp` and `entry_main()` method.
    `entry_main()` method is the start of child scraper,
    but you have to call `child_scraper.main()` to start scraper instead.
    """

    def __init__(
        self,
        driver: webdriver.Edge,
        run_id: str,
        scraper_id: str,
        otp_generator: BaseOTPGenerator,
        cloud_handler: CloudHandler,
        cookie_saver: CookiesProtocol,
        execution_date: str = None,
        state_saver: StateSaver = None,
        default_wait_seconds=10,
        tmp_location="./tmp/scrapers",
    ) -> None:
        self._browser = driver
        self.id = scraper_id
        self.run_id = str(run_id)
        self.default_wait = default_wait_seconds
        self.blob_client = cloud_handler
        self.otp_generator = otp_generator
        self.cookie_saver = cookie_saver
        self.execution_date = execution_date or datetime.now(timezone.utc).strftime(
            "%Y-%d-%m"
        )
        self.session = requests
        self.state_saver = state_saver
        self.soup: BS = None
        self._uploaded_files: list[cct.DownloadedInfoType] = []
        self._cached_sites: dict[str, str] = {}
        self._tmp_location = tmp_location
        self._all_loaded_products: set[BaseProduct] = set()
        self._init()
        self._name = None

    @property
    def name(self) -> str:
        if self._name:
            return self._name

        return __name__.rsplit(".", maxsplit=1)[-1]

    def clean_text(self, text: str) -> str:
        """
        Clean the text to remove unwanted characters
        """
        new_text = re.sub(NON_PRINTABLE_PATTERN, " ", text)
        return new_text

    def get_cached_name(self, url: str, data=None, file_type="html") -> str:
        """
        You need to implement this method to get the cached name
        of the file.
        """
        file_name = f"{self._tmp_location}/{self.id}/{self.execution_date}/{md5(f"{url}:{data}".encode()).hexdigest()}.{file_type}"
        if not os.path.exists(os.path.dirname(file_name)):
            os.makedirs(os.path.dirname(file_name), exist_ok=True)
        
        return file_name

    def _get_volume_from_code(self, volume_text: str):
        if volume_text == "Taille unique":
            return 1, "Taille unique"
        if not volume_text:
            logger.error("Cannot find volume from empty. Default to 30ml")
            return 30, "ml"
        volume_text = (
            volume_text.replace(".", "😒.😘").replace(",", ".").replace("😒.😘", ",")
        )
        try:
            volume = float(re.sub(r"[^0-9,.]", "", volume_text))
            unit = re.sub(r"[0-9 ,.]+", "", volume_text) or "ml"
            return volume, unit.strip().lower()
        except ValueError:
            logger.error("Cannot parse volume from %s", volume_text)
            return 1, volume_text

    def get_json(self, url: str, headers=None, timeout=20, use_cached=True) -> dict:
        cached_name = self.get_cached_name(url, file_type="json")
        if use_cached and os.path.isfile(cached_name):
            logger.info("Found cached site: %s", cached_name)
            self._cached_sites[url] = cached_name
            with open(cached_name, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    if data:
                        return data
                except json.JSONDecodeError:
                    logger.error(
                        "Cannot decode json from %s. Reload the file...", cached_name
                    )
                    os.remove(cached_name)

        if not url:
            return {}

        if not headers:
            headers = DEFAULT_HEADERS
        sleep(random.random())

        response = self.session.get(url=url, headers=headers, timeout=timeout)

        retry = 3
        while response.status_code == 429 and retry > 0:
            logger.warning("Too many requests, sleep for 30 seconds!")
            retry -= 1
            sleep(30)
            response = self.session.get(url=url, headers=headers, timeout=timeout)

        if response.status_code == 429:
            logger.error("Too many requests, cannot get result from %s", url)
            sleep(60)
            return {}

        if response.status_code != 200:
            logger.error(
                "Status: %s, Cannot get result from %s", response.status_code, url
            )
            return {}

        result: dict = parse_response(response.text)
        if result:
            logger.info("Cached site: %s", url)
            with open(cached_name, "w", encoding="utf-8") as f:
                json.dump(result, f)

        return result

    def get(self, url: str, use_cache=True):
        cached_name = self.get_cached_name(url)
        if use_cache and os.path.isfile(cached_name):
            logger.info("Found cached site: %s", cached_name)
            self._cached_sites[url] = cached_name
            with open(cached_name, "r", encoding="utf-8") as f:
                content = f.read()
                if len(content) > 0:
                    self.soup = BS(content, "html.parser")
                    return self.soup

        self._browser.get(url)
        with open(cached_name, "w", encoding="utf-8") as file:
            file.write(self._browser.page_source)
            self._cached_sites[url] = cached_name
            logger.info("Cached site: %s", url)

        self.soup = BS(self._browser.page_source, "html.parser")
        return self.soup

    def _get_default_post_headers(
        self,
        boundary=None,
        content_type: str = None,
        referer: str = None,
        x_requested_with: str = None,
    ):
        headers = DEFAULT_HEADERS
        boundary = boundary or f"----EdWIn{uuid.uuid4().hex}"
        if "Content-Type" not in headers:
            headers["Content-Type"] = (
                content_type or f"multipart/form-data; boundary={boundary}"
            )
        if "X-Requested-With" not in headers:
            headers["X-Requested-With"] = x_requested_with or "XMLHttpRequest"
        if "Referer" not in headers:
            headers["Referer"] = referer or "https://www.printemps.com/fr/fr/parfum"

        return headers, boundary

    def post_form(
        self,
        url: str,
        data: dict,
        headers=None,
        timeout=20,
        boundary=None,
        content_type: str = None,
        referer: str = None,
        x_requested_with: str = None,
    ):
        if not boundary:
            boundary = f"----EdWIn{md5(self.execution_date.encode()).hexdigest()}"
        if not headers:
            headers, boundary = self._get_default_post_headers(
                boundary=boundary,
                content_type=content_type,
                referer=referer,
                x_requested_with=x_requested_with,
            )

        post_data = ""
        for key, value in data.items():
            post_data += f"--{boundary}\r\n"
            post_data += f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
            if isinstance(value, list):
                for item in value:
                    post_data += f"{item}\r\n"
            else:
                post_data += f"{value}\r\n"
        post_data += f"--{boundary}--\r\n"
        post_data = post_data.encode("utf-8")
        result = self.post(url=url, data=post_data, headers=headers, timeout=timeout)
        return result

    def post(
        self, url: str, data: dict, headers=None, timeout=20, use_cached=True
    ) -> dict:
        cached_name = self.get_cached_name(url, data=data, file_type="json")
        if use_cached and os.path.isfile(cached_name):
            logger.info("Found cached site: %s", cached_name)
            self._cached_sites[url] = cached_name
            with open(cached_name, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        if not url:
            return {}

        if not headers:
            headers = DEFAULT_HEADERS

        response = self.session.post(
            url=url, data=data, headers=headers, timeout=timeout
        )
        if response.status_code != 200:
            logger.error("Cannot get result from %s", url)
            return {}

        result: dict = response.json()

        if result:
            logger.info("Cached site: %s", url)
            with open(cached_name, "w", encoding="utf-8") as f:
                json.dump(result, f)

        return result

    def get_otp(self) -> str:
        """
        You need to implement this method to generate OTP
        or retrieve the OTP.
        """
        otp = self.otp_generator.get_otp()
        return otp

    @abstractmethod
    def entry_main(self, **kwargs):
        """
        The real code will start here,
        you have to implement this function.
        You should NOT call this function directly!
        """

    def _init(self):
        self._check_default_wait()
        self._make_download_folder()
        self._make_tmp_folder()
        self._make_screenshot_folder()

    def _check_default_wait(self):
        if not self.default_wait or not isinstance(self.default_wait, int):
            self.default_wait = int(os.getenv("DEFAULT_SLEEP_TIME") or 10)

    def get_download_folder(self):
        download_path = fh.get_download_location(
            run_id=self.run_id,
            scraper_id=self.id,
            suffix=cct.DOWNLOAD,
            execution_date=self.execution_date,
        )
        return download_path

    def _make_download_folder(self):
        download_path = self.get_download_folder()
        os.makedirs(download_path, exist_ok=True)
        return download_path

    def _make_tmp_folder(self):
        os.makedirs(self._tmp_location, exist_ok=True)

    def get_img_folder_path(self) -> str:
        return fh.get_download_location(
            scraper_id=self.id,
            run_id=self.run_id,
            suffix=cct.SCREENSHOT,
            execution_date=self.execution_date,
        )

    def _make_screenshot_folder(self):
        path_save_screenshot = self.get_img_folder_path()
        os.makedirs(path_save_screenshot, exist_ok=True)
        return path_save_screenshot

    def save_screenshot(self, file_name: str):
        """Save the screenshot of current browser to current run folder.

        Args:
            file_name (str): The file name of browser.

        Returns:
            str: The path where screenshot save
        """
        time_stamp = int(datetime.now(timezone.utc).timestamp())
        file_name = f"{time_stamp}_{file_name}"
        file_name = make_safe_file_name(file_name)

        img_folder_path = self._make_screenshot_folder()
        img_full_path = os.path.join(img_folder_path, file_name)
        self._browser.save_screenshot(img_full_path)
        logger.info("Saved screenshot to %s", img_full_path)

        self.upload_image_to_blob(img_full_path)

        return img_full_path

    def wait(
        self, until=None, timeout: int = 10, reason="", raise_error=True
    ) -> WebElement:
        """Wait only or wait until the condition is meet.

        Args:
            until (callable, optional): The callable return True when stop waiting.
            Defaults to None.
            timeout (int, optional): The time in seconds that will raise TimeoutException.
            Defaults to 10.

        Returns:
            WebElement: The element you found through until condition
        """
        if not until:
            if reason:
                logger.info("Sleep %ss, wait for: %s.", timeout, reason)
            else:
                logger.info("Only sleep: %s second(s), not wait for anything.", timeout)
            sleep(timeout)
            return

        wait = WebDriverWait(driver=self._browser, timeout=timeout)
        try:
            result = wait.until(until)
            return result
        except TimeoutException:
            logger.error("Cannot find for %s in %s", until, timeout)
            if raise_error:
                raise
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Cannot find for %s", until)
            logger.error(e)
            if raise_error:
                raise

    def get_blob_path(self, file_path: str, suffix: str):

        blob_path = fh.get_blob_path(
            file_path=file_path,
            suffix=suffix,
            scraper_id=self.id,
            execution_date=self.execution_date,
            run_id=self.run_id,
        )

        return blob_path

    def _get_image_blob_path(self, img_path: str) -> str:
        img_blob_path = self.get_blob_path(file_path=img_path, suffix=cct.SCREENSHOT)
        return img_blob_path

    def _get_file_blob_path(self, file_path: str) -> str:
        file_blob_path = self.get_blob_path(file_path=file_path, suffix=cct.DOWNLOAD)
        return file_blob_path

    def wait_and_find(
        self, by: str, value: str, timeout=10, find_existing=False, raise_error=True
    ) -> WebElement:
        """Wait until find the element by specific value or raise
        TimeoutException when timeout.

        Args:
            by (str): By.ID or By.NAME or By...
            value (str): The value that you found
            timeout (int, optional): The timeout in seconds. Defaults to 10.

        Returns:
            WebElement: The element you found.
        """
        element = None
        if find_existing:
            condition = EC.presence_of_element_located((by, value))
        else:
            condition = EC.visibility_of_element_located((by, value))
        try:
            element = self.wait(until=condition, timeout=timeout)
        except TimeoutException:
            logger.error(
                "Timeout (>%s s) error while looking for %s=%s", timeout, by, value
            )
            self.save_screenshot(f"By_[{by}]=[{value}]-timeout=[{timeout}s].png")
            if raise_error:
                raise

        return element

    def set_attribute(self, element: WebElement, attribute: str, value: str):
        """Set the attribute of element

        Args:
            element (WebElement): The element has attribute want to set
            value (str): The value of attribute want to set
        """
        self._browser.execute_script(
            f"arguments[0].setAttribute('{attribute}',arguments[1])", element, value
        )

    def get_attribute(self, element: WebElement, attribute: str) -> str:
        """Get the attribute of element

        Args:
            element (WebElement): The element has attribute want to get
            value (str): The value of attribute want to get

        Returns:
            str: The value of attribute
        """
        value = self._browser.execute_script(
            f"return arguments[0].getAttribute('{attribute}')", element
        )
        logger.info("Get attribute %s=%s", attribute, value)
        if not value:
            logger.error("Cannot get attribute %s", attribute)
            return None
        return value

    def find_by_attribute(self, attribute: str, value: str, raise_error=False):
        """Find the element by attribute

        Args:
            attribute (str): The attribute you want to find
            value (str): The value of attribute you want to find

        Returns:
            WebElement: The element you found
        """
        element = self._browser.find_element(f"//*[@{attribute}='{value}']")
        if not element:
            logger.error("Cannot find element with %s=%s", attribute, value)
            if raise_error:
                raise LookupError(f"Cannot find element with {attribute}={value}")
        return element

    def soup_find_all_by_attribute(
        self, attribute: str, value: str, soup: BS = None, raise_error=False
    ) -> ResultSet:
        """Find the element by attribute

        Args:
            attribute (str): The attribute you want to find
            value (str): The value of attribute you want to find
            soup (BeautifulSoup): The soup you want to find. Defaults to self.soup

        Returns:
            BeautifulSoup: The element you found
        """
        if not soup:
            soup = self.soup

        if not soup:
            logger.error("Cannot find soup! You have to provide soup!")
            if raise_error:
                raise LookupError("Cannot find soup!")

        element = soup.find_all(attrs={attribute: value})
        if not element:
            logger.error("Cannot find element with %s=%s", attribute, value)
            if raise_error:
                raise LookupError(f"Cannot find element with {attribute}={value}")
        return element

    def soup_find_by_attribute(
        self, attribute: str, value: str, soup: BS = None, raise_error=False
    ) -> BS:
        """Find the element by attribute

        Args:
            attribute (str): The attribute you want to find
            value (str): The value of attribute you want to find
            soup (BeautifulSoup): The soup you want to find. Defaults to self.soup

        Returns:
            BeautifulSoup: The element you found
        """
        if not soup:
            soup = self.soup

        if not soup:
            logger.error("Cannot find soup! You have to provide soup!")
            if raise_error:
                raise LookupError("Cannot find soup!")

        element = soup.find(attrs={attribute: value})
        if not element:
            logger.error("Cannot find element with %s=%s", attribute, value)
            if raise_error:
                raise LookupError(f"Cannot find element with {attribute}={value}")
        return element

    def soup_find_all_by_class(
        self, class_name: str, soup: BS = None, raise_error=False
    ) -> BS:
        """Find the element by class name
        Args:
            soup (BeautifulSoup): The soup you want to find
            class_name (str): The class name you want to find
            raise_error (bool, optional): Raise error if not found. Defaults to False.
        Returns:
            WebElement: The element you found
        """
        if not soup:
            soup = self.soup
        if not soup:
            logger.error("Cannot find soup! You have to provide soup!")
            if raise_error:
                raise LookupError("Cannot find soup!")

        element = soup.find_all(class_=class_name)
        if not element:
            logger.error("Cannot find element with class=%s", class_name)
            if raise_error:
                raise LookupError(f"Cannot find element with class={class_name}")
        return element

    def soup_find_by_class(
        self, class_name: str, soup: BS = None, raise_error=False
    ) -> BS:
        """Find the element by class name
        Args:
            soup (BeautifulSoup): The soup you want to find
            class_name (str): The class name you want to find
            raise_error (bool, optional): Raise error if not found. Defaults to False.
        Returns:
            WebElement: The element you found
        """
        if not soup:
            soup = self.soup
        if not soup:
            logger.error("Cannot find soup! You have to provide soup!")
            if raise_error:
                raise LookupError("Cannot find soup!")

        element = soup.find(class_=class_name)
        if not element:
            logger.error("Cannot find element with class=%s", class_name)
            if raise_error:
                raise LookupError(f"Cannot find element with class={class_name}")
        return element

    def find_all_by_attribute(self, attribute: str, value: str):
        """Find the element by attribute

        Args:
            attribute (str): The attribute you want to find
            value (str): The value of attribute you want to find

        Returns:
            WebElement: The element you found
        """
        elements = self._browser.find_elements(By.XPATH, f"//*[@{attribute}='{value}']")
        if not elements:
            logger.error("Cannot find element with %s=%s", attribute, value)

        return elements

    def _set_windows_to_the_right(self):
        if not os.getenv("SELENIUM_SET_HALF_RIGHT_SCREEN"):
            logger.info("Skipped set windows to the right.")
            return

        logger.info("Setting window to the right.")
        size = self._browser.get_window_size()
        height = size.get("height") or 768
        width = size.get("width") or 1024
        self._browser.set_window_size(width=width // 2, height=height)
        self._browser.set_window_position(width // 2, 0)

    def upload_image_to_blob(self, img_path: str):
        logger.info("Uploading screenshot to: %s", img_path)
        if not os.path.isfile(img_path):
            logger.warning("Cannot upload image: %s", img_path)
            return

        blob_path = self._get_image_blob_path(img_path=img_path)
        result = self.blob_client.upload_blob_file(
            file_path=img_path,
            destination_name=blob_path,
            overwrite=True,
        )
        logger.info("Uploaded to: %s", blob_path)
        return result

    def get_downloaded_files(self) -> list[str]:
        logger.info("Getting local downloaded files...")
        temp_folder_path = self.get_download_folder()
        downloaded_files = fh.get_all_file_inside_path(temp_folder_path)
        return downloaded_files

    def wait_all_files_downloaded(
        self,
        file_type=".csv",
        file_count=1,
        default_wait=10,
        wait_times=120,
        check_local=False,
        **kwargs,
    ):
        if check_local:
            files = self.get_downloaded_files() or []
        else:
            logger.info("Getting remote downloaded files...")
            files: list[str] = self._browser.get_downloadable_files()
            logger.debug("Found files from remote location: %s", files)

        wanted_files = [file for file in files if file.endswith(f"{file_type}")]
        enough_file = True
        if file_count and file_count > len(wanted_files):
            enough_file = False

        if all(wanted_files) and enough_file:
            return wanted_files

        if wait_times < 0:
            logger.error("Cannot wait for %s type %s", file_count, file_type)
            raise TimeoutError(f"Cannot wait for {file_count} type {file_type}")

        wait_times = wait_times - 1

        self.wait(timeout=default_wait, reason="Waiting file to be downloaded...")
        return self.wait_all_files_downloaded(
            file_type=file_type,
            default_wait=default_wait,
            wait_times=wait_times,
            check_local=check_local,
            **kwargs,
        )

    def download_from_grid(
        self, file_type=".csv", file_count=1, default_wait=10, wait_times=120
    ):
        files = self.wait_all_files_downloaded(
            file_type, file_count, default_wait, wait_times
        )

        if not files:
            logger.warning("There is no file in Grid to download!")
            return []

        local_download_folder = self.get_download_folder()
        for downloadable_file in files:
            self._browser.download_file(downloadable_file, local_download_folder)

        downloaded_files = self.wait_all_files_downloaded(
            file_type, file_count, default_wait, wait_times, check_local=True
        )

        if len(downloaded_files) != len(files):
            logger.error("There is missing file when download from Selenium remote!")

        return downloaded_files

    def upload_download_folder_to_blob(
        self, file_type=".json", file_count=1, default_wait=10, **kwargs
    ):
        logger.info("Uploading downloaded folder to blob...")
        wait_times = kwargs.get("wait_times", 120)
        downloaded_files = self.download_from_grid(
            file_type, file_count, default_wait, wait_times
        )

        if not downloaded_files:
            logger.warning("Cannot download from grid!!!")
            return

        logger.info("Uploading file: %s", downloaded_files)

        for file_path in downloaded_files:
            blob_path = self._get_file_blob_path(file_path=file_path)
            self.blob_client.upload_blob_file(
                file_path=file_path,
                destination_name=blob_path,
                overwrite=True,
            )
            self._uploaded_files.append(
                {"local_file": file_path, "blob_file": blob_path}
            )
            logger.info("Uploaded to: %s", blob_path)

        logger.info("Finished Upload to Blob storage.")
        return self._uploaded_files

    def get_uploaded_files(self) -> list[cct.DownloadedType]:
        return self._uploaded_files

    def _exit(self, timeout=1):
        self.wait(timeout=timeout, reason="Before exiting scraper...")
        self._browser.quit()

    def load_cookies(self):
        if not self.cookie_saver:
            logger.warning("Do not have cookie saver! Skip load cookies!")
            return
        self.cookie_saver.load_cookies(driver=self._browser)

    def save_cookies(self):
        if not self.cookie_saver:
            logger.warning("Do not have cookie saver! Skip load cookies!")
            return
        logger.info("Saving cookies to use later")
        self.cookie_saver.save_cookies(driver=self._browser)

    def save_state(self, state: dict):
        if not self.state_saver:
            logger.warning("Do not have state saver! Skip saving state!")
            return

        logger.info("Saving state to use later")
        for key, value in state.items():
            if isinstance(value, list):
                value = ",".join(value)
            elif isinstance(value, dict):
                value = ",".join([f"{k}:{v}" for k, v in value.items()])
            elif isinstance(value, str):
                value = value.replace(",", "@@COMMA@@")
            elif isinstance(value, int):
                value = str(value)
            else:
                logger.warning("Cannot save state with type %s", type(value))
                continue

            self.state_saver.save_state(
                scraper_id=self.id,
                execution_date=self.execution_date,
                state_key=key,
                state_value=value,
            )

    def load_state(self, state_keys: str | list[str]) -> dict:
        if not self.state_saver:
            logger.warning("Do not have state saver! Skip loading state!")
            return {}
        if isinstance(state_keys, str):
            state_keys = [state_keys]

        logger.info("Loading state to use later")

        parsed_state = {}

        for key in state_keys:
            state = self.state_saver.load_state(
                scraper_id=self.id,
                state_key=key,
            )
            if "," in state:
                if ":" in state:
                    parsed_state[key] = {
                        k: v for k, v in (item.split(":") for item in state.split(","))
                    }
                else:
                    parsed_state[key] = state.split(",")
            else:
                parsed_state[key] = state.replace("@@COMMA@@", ",")

        return parsed_state

    @abstractmethod
    def validate_all_products(self):
        """You have to override this method to load all products"""

    def to_json(self, file_name: str = None):
        """Convert the products to JSON format."""
        if not file_name:
            file_name = f"data/exported/{self.name}.json"
        self.validate_all_products()

        result = []
        count_variants = 0

        for product in self._all_loaded_products:
            if not product.is_variants_loaded:
                logger.warning("Product %s is not loaded!", product)
            product_item = {
                "id": product.id,
                "name": product.name,
                "brand": {
                    "name": product.brand,
                },
                "category": product.line,
                "gender": product.gender,
                "url": product.link,
            }
            variants = []
            product_item["variants"] = variants
            for variant in product:
                count_variants += 1
                variant_item = variant.to_scraper_ouput()
                variants.append(variant_item.model_dump())

            result.append(product_item)

        logger.info("Found %s products and %s variants", len(result), count_variants)

        dir_name = os.path.dirname(file_name)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)

        with open(file_name, "w", encoding="utf-8") as f:
            json.dump(
                result,
                f,
                indent=4,
                default=lambda x: x.isoformat() if isinstance(x, datetime) else x,
            )
        logger.info("Exported %s products to file: %s", len(result), file_name)

    def to_json_old(self, file_name: str = "scraper.json"):
        """Convert the products to JSON format."""
        self.validate_all_products()

        result = []

        for product in self._all_loaded_products:
            if not product.is_variants_loaded:
                logger.warning("Product %s is not loaded!", product)
            product_item = {
                "id": product.id,
                "name": product.name,
                "brand": {
                    "name": product.brand,
                },
                "category": product.line,
                "gender": product.gender,
                "url": product.link,
            }
            variants = []
            product_item["variants"] = variants
            for variant in product:
                variant_item = {
                    "id": variant.id,
                    "size": variant.volume,
                    "sizeUnit": variant.iso_volume_unit,
                    "isSampling": None,
                    "currency": variant.iso_price_unit,
                    "price": variant.price,
                    "url": variant.link,
                    "updatedAt": datetime.now().isoformat(),
                }
                variants.append(variant_item)

            result.append(product_item)

        dir_name = os.path.dirname(file_name)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)

        with open(file_name, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4)
        logger.info("Exported %s products to file: %s", len(result), file_name)

    def get_variants(self) -> list[dict]:
        """Get all variants of the product."""
        variants = []
        for product in self._all_loaded_products:
            if not product.is_variants_loaded:
                logger.warning("Product %s is not loaded!", product)
            for variant in product:
                variants.append(variant.to_scraper_ouput().model_dump_json())
        return variants

    def login(self):
        logger.info("No need to login to %s", self.name)

    def main(self, *args, **kwargs):
        """Main start of scraper. You must call this instead of entry_main() function."""
        logger.info("---------Start scraping---------")
        logger.info("---Run ID: %s---", self.run_id)
        logger.info(
            "---Start Time: %s---", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        try:
            self._set_windows_to_the_right()
            self.entry_main(*args, **kwargs)
        finally:
            self._exit()

        logger.info("-------Scraping Finished-------")

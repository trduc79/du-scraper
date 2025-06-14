import logging


from core.file.cloud_handler import CloudHandler
from core.utils.helper import CookiesProtocol
from selenium.common.exceptions import NoSuchElementException
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

        logger.info("[INFO] Loading product detail page: %s", product.link)

        self.get(product.link)
        ##dk1
        try:
            form = self.soup.find(id="product_addtocart_form")
        except NoSuchElementException:
            logger.warning(
                "⛔ Không tìm thấy biến thể nào cho sản phẩm%s", product.link
            )
            return 0
        if form == None:
            logger.warning(
                "⛔ Không tìm thấy biến thể nào cho sản phẩm %s", product.link
            )
            return 0 
        

        options = form.select("label.pill-radio-capacity")
        valid_options = [
            opt for opt in options if re.search(r"\d+\s*ml", opt.text.strip().lower())
        ]
        if options:
            logger.info(
                "✅ Tìm thấy %d biến thể cho sản phẩm %s",
                len(valid_options),
                product.link,
            )
            return len(options)

        # lay ra doan chu chua size  dk2
        desc_container = self.soup.select_one("span.short-description-container")
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
                logger.info("🟢 Không có biến thể UI nhưng tìm thấy: %s", variant_name)
                return 1
            else:
                logger.warning(
                    "⚠️ Mô tả chỉ có 1 dung tích nhưng không khớp mẫu: %s", desc_text
                )
                return 0

        # Điều kiện 3: Có dấu "+" hoặc không có đơn vị ml
        if "+" in desc_text or "ml" not in desc_text.lower():
            logger.warning("⚠️ Mô tả kết hợp hoặc không rõ ràng: %s", desc_text)
            return 0

        # Không có gì hợp lệ
        logger.warning("⛔ Không tìm thấy biến thể nào cho sản phẩm %s", product.link)
        return 0

    def get_variant_volume(self, product: AdoptProduct):
        self.get(product.link)

        desc_container = self.soup.select_one("span.short-description-container")
        if desc_container:
            desc_text = desc_container.get_text(strip=True)
        else:
            desc_text = ""

        # Tìm dung tích trong mô tả, ví dụ "50 ML", "100ml"
        match = re.search(r"(\d{1,4})\s*ml", desc_text.lower())
        if match:
            volume = int(match.group(1))
            logger.info("📦 Tìm thấy dung tích: %dml từ mô tả: %s", volume, desc_text)
            return volume
        else:
            logger.warning("⚠️ Không tìm thấy dung tích trong mô tả: %s", desc_text)
            return None

    def get_variant_price(self, product: AdoptProduct):
        self.get(product.link)

        meta_price = self.soup.find("meta", attrs={"property": "product:price:amount"})
        if not meta_price:
            logger.info("⚠️ Không tìm thấy thẻ meta giá cho sản phẩm %s", product.link)
            return None

        price_text = meta_price.get("content")
        try:
            price = float(price_text)
            return price
        except (TypeError, ValueError):
            logger.warning("❌ Không thể chuyển đổi giá '%s' thành số", price_text)
            return None
        
    def get_variant_name(self, product: AdoptProduct):
        self.get(product.link)
        
        name_text = self.soup.find("div", class_ = "font-romie font-bold flex gap-2 items-center justify-between")
        if not name_text:
            logger.info("Ko tim ra ten bien the")
        return name_text.get_text(strip=True)
        
    def get_variant_id(self, product: AdoptProduct):
        self.get(product.link)
        
        btn = self.soup.find('button', attrs={'data-wishlist': True})
        if btn:
            product_id = btn.get('data-wishlist')
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
            logger.info("❌ Không tìm thấy script chứa initConfigurableSwatchOptions_")
            return {}

        # Tách JSON từ initConfigurableOptions
        pattern = r'initConfigurableOptions\(\s*[\'"]\d+[\'"]\s*,\s*(\{.*?})(?=\s*\);)'
        match = re.search(pattern, script_text, re.DOTALL)

        if not match:
            logger.info("❌ Không tìm thấy JSON trong initConfigurableOptions")
            return {}

        raw_json_text = match.group(1)

        try:
            # Làm sạch JSON
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
            logger.info(f"❌ Lỗi xử lý JSON: {e}")
            return {}
    
    def check_stock_variants(self, product: AdoptProduct) -> bool:
        self.get(product.link)

        # Kiểm tra form chứa biến thể
        form = self.soup.find(id="product_addtocart_form")
        if not form:
            logger.warning("❌ Không tìm thấy form chứa biến thể trong %s", product.link)
            return False  # Giả định là còn hàng nếu không kiểm tra được

        # Kiểm tra alert_container xuất hiện -> là hết hàng
        alert_div = self.soup.find("div", id="alert_container")
        if alert_div and "display: none" not in alert_div.get("style", ""):
            logger.info("❌ Biến thể đang chọn đã hết hàng (alert_container hiển thị)")
            return False

        logger.info("✅ Biến thể đang chọn vẫn còn hàng")
        return True
    
    def _load_product_variant(self, product: AdoptProduct):
        num_variants = self.find_variants_option(product)

        if num_variants == 0:
            logger.warning("⛔ Sản phẩm không có biến thể: %s", product.link)
            return

        elif num_variants == 1:
            # TODO: Phân tích dữ liệu từ mô tả hoặc giá
            # Dummy variant info (tạm thời bạn cần lấy đúng dữ liệu thật):
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
                    variant_stock=self.check_stock_variants(product)
                )
            )
            logger.info("✅ Sản phẩm có 1 biến thể (mặc định): %s", variant_name)

        elif num_variants > 1:
            logger.info("✅ Sản phẩm có nhiều biến thể UI: %s", product.link)
            # TODO: Trích xuất biến thể từ UI (ví dụ từ form)
            
            #b1: Tim dc variants ID cua tung bien the 
            self.get(product.link) 
            
            variants_info = self.get_all_variants(product)
            for size_ml, (variant_id, price , in_stock) in variants_info.items():
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
            
            
            
    def get_number_of_pages(self, max_pages=100):
        page = 1
        while page <= max_pages:
            logger.info(f"🔄 Đang kiểm tra trang {page}")
            soup = self.get(f"{PRODUCT_LIST}?p={page}")

            # Kiểm tra xem có xuất hiện "Fin de sélection"
            end_of_selection = soup.select_one(
                'span.text-purple.font-primary.font-semibold.xl\\:text-smaller.text-xs[x-show="wording"]'
            )

            if end_of_selection and "Fin de sélection" in end_of_selection.get_text(
                strip=True
            ):
                logger.info(
                    f"✅ Kết thúc tại trang {page} do xuất hiện 'Fin de sélection'"
                )
                break

            page += 1

        if page > max_pages:
            logger.warning(
                "⚠️ Vượt quá giới hạn trang (%s), có thể bị vòng lặp vô hạn!", max_pages
            )

        return page

    def load_all_product(self):
        max_page = self.get_number_of_pages()
        logger.info(f"📄 Tổng số trang: {max_page}")

        for page in range(1,max_page + 1):
            soup = self.get(f"{PRODUCT_LIST}?p={page}")
            products = soup.select("a.product-item")
            scripts = soup.find_all(
                "script", text=re.compile(r"function initItemProduct_")
            )

            logger.info(
                f"🔍 Trang {page} có {len(products)} sản phẩm và {len(scripts)} script."
            )

            for product, script in zip(products, scripts):
                try:
                    content = script.text or ""
                    match = re.search(
                        r"function initItemProduct_\w+\(\)\s*{\s*return\s*{\s*currentProductData\s*:\s*{(.*?)}\s*[,}]",
                        content,
                        re.DOTALL,
                    )

                    if not match:
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

                    # 🔥 Quan trọng: lấy URL từ thẻ <a>, không phải script
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

                    logger.info("✅ %s | %s | %s", product_id, name, full_url)

                except Exception as e:
                    logger.warning(f"❌ Lỗi xử lý sản phẩm: {e}")

    def validate_all_products(self):
        self.load_all_product()
        self.load_all_variants()

    def load_all_variants(self):
        for product in self._all_loaded_products:
            self._load_product_variant(product)

    def entry_main(self, **kwargs):
        self.login()
        self.to_json(**kwargs)

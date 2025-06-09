from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import re
import time
from bs4 import BeautifulSoup

service = Service(executable_path="chromedriver.exe")
driver = webdriver.Chrome(service=service)

def extract_variant_ids_from_script(driver, product_url):
    """
    Trích xuất variant IDs từ script initConfigurableSwatchOptions
    Return: dict với key là size (ml) và value là variant ID
    """
    variant_ids = {}
    
    try:
        # Mở tab mới
        driver.execute_script("window.open(arguments[0]);", product_url)
        driver.switch_to.window(driver.window_handles[1])
        
        # Tắt popup cookie nếu có
        try:
            accept_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            accept_button.click()
            print("✅ Đã tắt popup cookie")
        except:
            pass
        
        # Chờ load trang
        time.sleep(3)
        
        # Lấy toàn bộ mã nguồn HTML
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        scripts = soup.find_all("script")
        
        # Tìm script chứa initConfigurableSwatchOptions
        script_text = ""
        for script in scripts:
            if script.string and "initConfigurableSwatchOptions_" in script.string:
                script_text = script.string
                print("🔍 Found script containing initConfigurableSwatchOptions_")
                break
        
        if not script_text:
            print("❌ No script containing initConfigurableSwatchOptions_ found")
            return variant_ids
        
        # Trích xuất JSON từ initConfigurableOptions
        pattern = r'initConfigurableOptions\(\s*[\'"]\d+[\'"]\s*,\s*(\{.*?})(?=\s*\);)'
        match = re.search(pattern, script_text, re.DOTALL)
        
        if match:
            raw_json_text = match.group(1)
            print("✅ Found JSON data in initConfigurableOptions")
            
            try:
                # Làm sạch JSON
                json_text = re.sub(r',(\s*[}\]])', r'\1', raw_json_text)
                json_text = json_text.replace("'", '"')
                json_text = re.sub(r'([,{]\s*)(\w+)(\s*:)', r'\1"\2"\3', json_text)
                json_text = json_text.replace("False", "false").replace("True", "true").replace("None", "null")
                json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
                json_text = json_text.strip().lstrip('\ufeff')
                
                # Parse JSON
                data = json.loads(json_text)
                attribute_options = data.get("attributes", {})
                
                # Trích xuất variant IDs theo size
                for attr_id, attr_data in attribute_options.items():
                    for option in attr_data.get("options", []):
                        label = option.get("label", "")
                        products = option.get("products", [])
                        
                        if products and label:
                            # Tìm size từ label
                            size_match = re.search(r"(\d+(?:[.,]\d+)?)\s*ml", label.lower())
                            if size_match:
                                size = float(size_match.group(1).replace(",", "."))
                                # Lấy variant ID đầu tiên (thường chỉ có 1)
                                variant_id = products[0] if products else None
                                if variant_id:
                                    variant_ids[size] = variant_id
                                    print(f"📦 {size}ml: {variant_id}")
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON Parse Error: {e}")
            except Exception as e:
                print(f"❌ Error processing JSON: {e}")
        else:
            print("❌ Không tìm thấy JSON trong initConfigurableOptions")
            
    except Exception as e:
        print(f"❌ Error extracting variant IDs: {e}")
    finally:
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
    
    return variant_ids

def extract_variants_from_product_page(driver, product_url, parent_id, parent_sku):
    """
    Trích xuất các variant (size + giá + variant ID) từ trang chi tiết sản phẩm
    """
    variants = []
    
    try:
        # Lấy variant IDs từ script
        variant_ids = extract_variant_ids_from_script(driver, product_url)
        print(f"🎯 Variant IDs tìm thấy: {variant_ids}")
        
        # Mở tab mới để lấy giá
        driver.execute_script("window.open(arguments[0]);", product_url)
        driver.switch_to.window(driver.window_handles[1])
        time.sleep(3)
        
        # Tìm tất cả các options
        try:
            form = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "product_addtocart_form"))
            )
            
            options = form.find_elements(By.CSS_SELECTOR, "label.pill-radio-capacity")
            print(f"🎯 Tìm thấy {len(options)} options đúng trong form sản phẩm")
            
        except Exception as e:
            print(f"❌ Không tìm thấy options nào trong form: {e}")
            options = []
        
        if not options:
            print("⚠️ Không tìm thấy variants")
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            return variants
        
        print(f"🔍 Đang xử lý variants cho sản phẩm {parent_sku}")
        
        for idx, option in enumerate(options):
            try:
                # Scroll và click
                driver.execute_script("arguments[0].scrollIntoView(true);", option)
                time.sleep(1)
                option_text = option.text.strip()
                print(f"🔄 Đang xử lý option {idx + 1}: {option_text}")
                
                # Click để chọn option
                driver.execute_script("arguments[0].click();", option)
                time.sleep(2)
                
                # Lấy giá
                try:
                    wrapper = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "price-wrapper"))
                    )
                    price_element = wrapper.find_element(By.CLASS_NAME, "price")
                    price_text = price_element.text.strip()
                    price_match = re.search(r"(\d+[.,]?\d*)", price_text.replace(",", "."))
                    price = float(price_match.group(1)) if price_match else None
                    print(f"💰 Giá: {price}")
                except Exception as e:
                    print(f"⚠️ Không lấy được giá: {e}")
                    price = None
                
                # Lấy size từ text
                size_match = re.search(r"(\d+(?:[.,]\d+)?)\s*ml", option_text.lower())
                size = float(size_match.group(1).replace(",", ".")) if size_match else None
                print(f"📏 Size: {size}")
                
                # Lấy variant ID từ dict đã trích xuất
                variant_id = variant_ids.get(size) if size in variant_ids else None
                print(f"🆔 Variant ID: {variant_id}")
                
                # Chỉ thêm variant nếu có đủ thông tin
                if price is not None and size is not None and variant_id is not None:
                    variants.append({
                        "size": size,
                        "price": price,
                        "currency": "EUR",
                        "variant_id": variant_id,
                        "link_source": product_url,
                        "parents_id": parent_id or parent_sku
                    })
                    print(f"✅ Thêm variant: {size}ml - {price}€ - ID: {variant_id}")
                else:
                    print(f"⚠️ Bỏ qua variant do thiếu thông tin")
                    
            except Exception as e:
                print(f"⚠️ Lỗi ở variant {idx + 1}: {e}")
                continue
        
        print(f"📊 Tổng số variants: {len(variants)}")
        
    except Exception as e:
        print(f"❌ Lỗi trang chi tiết sản phẩm: {e}")
    finally:
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
    
    return variants

try:
    driver.get("https://www.adopt.com/fr/parfum.html")

    # Chấp nhận cookie
    try:
        accept_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
        )
        time.sleep(5)
        accept_button.click()
        print("✅ Đã tắt popup cookie")
    except Exception as e:
        print("⚠️ Không tìm thấy popup:", e)

    # Click Load More
    try:
        while True:
            button_element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "amscroll-load-button"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", button_element)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", button_element)
            print("📦 Đã click Load More")
            time.sleep(3)
    except:
        print("⛔ Không còn nút load thêm")

    products = driver.find_elements(By.CSS_SELECTOR, "a.product-item")
    print(f"🔍 Tìm thấy {len(products)} sản phẩm")

    product_list = []

    for index, product in enumerate(products[:10]):
        try:
            data_sku = product.get_attribute("data-sku")
            product_url = product.get_attribute("href")
            
            if not data_sku or not product_url:
                continue

            print(f"\n🔍 Đang xử lý sản phẩm {index+1} - SKU: {data_sku}")

            # Trích xuất thông tin sản phẩm từ HTML
            try:
                page_source = driver.page_source
                pattern = rf"function initItemProduct_[^(]*\(\)\s*\{{\s*return\s*\{{[^}}]*currentProductData:\s*\{{([^}}]*)}}"
                matches = re.finditer(pattern, page_source, re.DOTALL)
                
                current_product_data = None
                for match in matches:
                    data_content = match.group(1)
                    if data_sku in data_content:
                        sku_match = re.search(r"'sku':\s*'([^']*)'", data_content)
                        name_match = re.search(r"'name':\s*'([^']*)'", data_content)
                        id_match = re.search(r"'id':\s*'([^']*)'", data_content)
                        price_match = re.search(r"'final_price':\s*'([^']*)'", data_content)
                        image_match = re.search(r"'image':\s*'([^']*)'", data_content)
                        description_match = re.search(r"'short_description':\s*\"([^\"]*?)\"", data_content)
                        
                        current_product_data = {
                            'sku': sku_match.group(1) if sku_match else data_sku,
                            'name': name_match.group(1).replace('\\u0020', ' ') if name_match else None,
                            'id': id_match.group(1) if id_match else None,
                            'final_price': price_match.group(1) if price_match else None,
                            'image': image_match.group(1) if image_match else None,
                            'short_description': description_match.group(1).replace('\\u0020', ' ').replace('\\u00E9', 'é') if description_match else None,
                        }
                        break
                        
            except Exception as e:
                print(f"❌ Lỗi trích xuất HTML: {e}")
                current_product_data = None
            
            # Trích xuất variants với variant IDs
            variants = extract_variants_from_product_page(
                driver, 
                product_url, 
                current_product_data.get('id') if current_product_data else None, 
                current_product_data.get('sku') if current_product_data else data_sku
            )

            # Tạo item cuối cùng
            item = {
                "id": current_product_data.get('id') if current_product_data else None,
                "name": current_product_data.get('name') if current_product_data else None,
                "url": product_url,
                "sku": current_product_data.get('sku') if current_product_data else data_sku,
                "brand": "Adopt",
                "variants": variants
            }

            product_list.append(item)
            print(f"✅ Đã xử lý sản phẩm {index+1}: {item['name']}")

        except Exception as e:
            print(f"⚠️ Lỗi sản phẩm {index+1}: {e}")
            continue

    # Lưu JSON
    with open("parfums_product.json", "w", encoding="utf-8") as f:
        json.dump(product_list, f, ensure_ascii=False, indent=4)

    print(f"\n🎉 Đã lưu {len(product_list)} sản phẩm vào 'parfums_product.json'")

except Exception as e:
    print(f"❌ Lỗi chung: {e}")

finally:
    driver.quit()
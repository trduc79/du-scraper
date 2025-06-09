from datetime import datetime, timezone
import logging
import os

from selenium import webdriver
from selenium.webdriver import Edge as Browser
from selenium.webdriver.edge.options import Options

from selenium.webdriver.edge.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager as Driver


from core.file.file_handler import get_download_location

logger = logging.getLogger(__name__)
DEFAULT_DRIVER_VERSION = "128.0"



def clear_sessions(session_id=None, driver_url="http://localhost:4444"):
    """
    Here we query and delete orphan sessions
    docs: https://www.selenium.dev/documentation/grid/advanced_features/endpoints/
    :return: None
    """
    #pylint: disable = redefined-outer-name, reimported, import-outside-toplevel
    import requests
    import json
    if session_id:
        print("Delete Selenium Session: %s", session_id)
        r = requests.delete(f"{driver_url}/session/{session_id}", timeout=20)
        return

    print("Delete all selenium session!!!")
    try:
        r = requests.get(f"{driver_url}/status", timeout=20)
        data = json.loads(r.text)
        for node in data["value"]["nodes"]:
            for slot in node["slots"]:
                if slot["session"]:
                    session_id = slot["session"]["sessionId"]
                    r = requests.delete(
                        f"{driver_url}/session/{session_id}", timeout=20
                    )
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to Selenium server at %s", driver_url)

def get_driver(
    scraper_id: str,
    run_id: str,
    remote_server=None,
    driver_version=None,
    execution_date=None,
):
    """Get Selenium Browser Driver

    Args:
        run_id (str): The uuid4 for current scaping
        scraper_id (str): The scraper id (name)

    Returns:
        Driver: The Selenium web driver.
    """
    if not execution_date:
        execution_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not driver_version:
        driver_version = DEFAULT_DRIVER_VERSION

    # Change download location:
    logger.info("Starting driver %s for scraper: %s", run_id, scraper_id)
    edge_options = Options()

    download_location = get_download_location(
        run_id, scraper_id, execution_date=execution_date
    )

    prefs = {
        "download.default_directory": download_location,
        "profile.managed_default_content_settings.images": 2,  # Disable load image
        'profile.default_content_settings.images': 2, # Disable load image
    }
    edge_options.add_experimental_option("prefs", prefs)

    is_headless = os.getenv("HEADLESS_BROWSER")
    if is_headless:
        if str(is_headless).lower() == "new":
            edge_options.add_argument("--headless=new")
        else:
            edge_options.add_argument("--headless")
    edge_options.add_argument("--start-maximized")

    edge_options.browser_version = driver_version
    edge_options.enable_downloads = True

    if str(os.getenv("CLEAR_SESSION")).lower() == "true":
        clear_sessions()

    if remote_server:
        driver = webdriver.Remote(command_executor=remote_server, options=edge_options)
    else:
        service = Service(Driver().install())
        driver = Browser(options=edge_options, service=service)

    # Dirty fix for download not enable even enable_download set to True
    if "se:downloadsEnabled" not in driver.capabilities:
        driver.capabilities["se:downloadsEnabled"] = True

    return driver

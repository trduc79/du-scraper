import logging
import os
import uuid

from core.scraper.base import DummyDriver
from core.utils import driver as d
from core.file.cloud_handler import DummyCloudHandler

from scraper.nocibe import NocibeScraper
from scraper.marionnaud import MarionnaudScraper
from scraper.lafayette import LafayetteScraper
from scraper.printemps import PrintempsScraper
from scraper.zara import ZaraScraper

logger = logging.getLogger(__name__)


def configure_logging(log_name: str = "scraper"):
    log_handlers = [logging.StreamHandler()]
    if not os.path.exists("./logs"):
        os.makedirs("./logs")
    if os.getenv("IS_LOCAL", "false").lower() == "true":
        log_handlers.append(logging.FileHandler(f"./logs/{log_name}.log", mode="w+"))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(filename)s:%(lineno)s  - %(levelname)s - %(message)s",
        handlers=log_handlers,
    )
    logger.info("Logging configured.")


def main():

    execution_date = "2025-04-07"
    run_id = f"{uuid.uuid4()}"
    # TODO: Change the scraper to the one you want to run
    Scraper = NocibeScraper
    
    configure_logging(Scraper.__name__.lower())

    if issubclass(Scraper, (ZaraScraper, MarionnaudScraper, LafayetteScraper, PrintempsScraper)):
        driver = DummyDriver()
    elif issubclass(Scraper, NocibeScraper):
        driver_url = os.getenv("SELENIUM_DRIVER_URL", "http://localhost:4444")
        driver = d.get_driver(
            scraper_id="nocibe",
            run_id=run_id,
            remote_server=driver_url,
            execution_date=execution_date,
        )

    scraper = Scraper(
        driver=driver,
        run_id=run_id,
        cloud_handler=DummyCloudHandler(),
        cookie_saver=None,
        execution_date=execution_date,
    )

    scraper.main()


if __name__ == "__main__":
    main()

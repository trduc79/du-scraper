import logging
import uuid

from core.scraper.base import DummyDriver
from core.scraper.nocibe import NocibeScraper
from core.scraper.marionnaud import MarionnaudScraper
from core.scraper.lafayette import LafayetteScraper
from core.scraper.printemps import PrintempsScraper
from core.scraper.zara import ZaraScraper
from core.utils import driver as d
from core.file.cloud_handler import DummyCloudHandler

logger = logging.getLogger(__name__)


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(filename)s:%(lineno)s  - %(levelname)s - %(message)s",
    )
    logger.info("Logging configured.")


def main():
    configure_logging()

    execution_date = "2025-04-07"
    run_id = f"{uuid.uuid4()}"
    # TODO: Change the scraper to the one you want to run
    Scraper = NocibeScraper

    if issubclass(Scraper, NocibeScraper):
        driver = d.get_driver(
            scraper_id="nocibe",
            run_id=run_id,
            remote_server="http://localhost:4444",
            execution_date=execution_date,
        )
    elif isinstance(Scraper, (ZaraScraper, MarionnaudScraper, LafayetteScraper, PrintempsScraper)):
        driver = DummyDriver()
    else:
        driver = DummyDriver()

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

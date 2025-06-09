import asyncio
import functools
import logging
import os
import pickle
import re
import time

import json
from typing import Awaitable, Literal, Protocol
import xml.etree.ElementTree as ET

from requests import Session
import xmltodict


from selenium.webdriver.edge.webdriver import WebDriver as Edge
from selenium.common.exceptions import StaleElementReferenceException


from . import constant as cct
from ..file.file_handler import get_columns_in_parquets


NOT_SAFE_CHAR_IN_FILE_NAME = re.compile(r"[^\w_. -/:]")
SAFE_FILE_NAME_PATTERN = re.compile(r"[^\w_. \-\[\]\(\)=]")

logger = logging.getLogger(__name__)


def detect_format(response: str) -> Literal["JSON", "XML", "Unknown"]:
    """Detect if the response is JSON or XML."""
    try:
        json.loads(response)
        logger.info("Detected JSON format")
        return "JSON"
    except json.JSONDecodeError:
        pass

    try:
        ET.fromstring(response)
        logger.info("Detected XML format")
        return "XML"
    except ET.ParseError:
        pass

    return "Unknown"


def parse_response(response: str) -> dict:
    """Parse the response based on its format."""
    format_type = detect_format(response)
    if format_type.upper() == "JSON":
        return json.loads(response)
    elif format_type.upper() == "XML":
        return xmltodict.parse(response)
    else:
        logger.error("Unknown format type: %s", format_type)
        return {}


def make_safe_file_name(file_name: str) -> str:
    # pylint: disable=W1401
    r"""Remove all unsafe character out of the path name.
    Consider to be unsafe: `r"[^\w_. \-\[\]\(\)=]"`
    Replace with: `_` character.

    Args:
        path (str): The path of file/folder

    Returns:
        str: The safe path.
    """
    safe_file_name = re.sub(SAFE_FILE_NAME_PATTERN, "_", file_name)
    return safe_file_name


def make_safe_path(path: str) -> str:
    r"""Remove all unsafe character out of the path name.
    Consider to be unsafe: `r"[^\w_. -/:]"`
    Replace with: `_` character.

    Args:
        path (str): The path of file/folder

    Returns:
        str: The safe path.
    """
    safe_path = re.sub(NOT_SAFE_CHAR_IN_FILE_NAME, "_", path)
    return safe_path


def async_run(awaitable_obj: Awaitable):
    """Run async coroutine in side synchronous function.
    This is a work-around due to the a known issue in aiohttp < 4.0.0 on Windows:
    https://github.com/aio-libs/aiohttp/issues/4324

    The work-around instead of call `asyncio.run(awaitable)` directly,
    we get event loop then call `loop.run_until_complete(awaitable)`.

    Args:
        awaitable_obj (Awaitable): Coroutine need to be awaited.

    Returns:
        (Any): The result of coroutine or raise exception.
    """
    logger.info("Running awaitable object...")
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(awaitable_obj)
    return result


class CookiesProtocol(Protocol):
    def load_cookies(self, driver: Edge):
        """Load cookies to web driver!"""

    def save_cookies(self, driver: Edge):
        """Save cookies of current webdriver"""


class StateSaver(Protocol):
    def load_state(
        self,
        scraper_id: str,
        state_key: str,
    ) -> str:
        """State of last scraping run"""

    def save_state(
        self,
        scraper_id: str,
        state_key: str,
        state_value: str,
    ):
        """Save states of last scraping run"""


class LocalCookiesSaver(CookiesProtocol):
    def __init__(self, cookie_path: str) -> None:
        self.cookie_path = cookie_path
        super().__init__()

    def load_cookies(self, driver: Edge):
        logger.info("Loading cookies...")
        if not os.path.isfile(self.cookie_path):
            logger.warning("Cannot find cookie in cookie path! Skip loading cookies.")
            return driver

        with open(self.cookie_path, "rb") as f:
            cookies = pickle.load(f)

        for cookie in cookies:
            if "expiry" in cookie:
                del cookie["expiry"]
            driver.add_cookie(cookie)

        logger.info("Loaded Cookies!")
        return driver

    def save_cookies(self, driver: Edge):
        logger.info("Saving cookies to use later...")
        save_path = self.cookie_path

        cookies_folder = os.path.dirname(os.path.abspath(save_path))
        os.makedirs(cookies_folder, exist_ok=True)
        with open(save_path, "wb") as f:
            pickle.dump(driver.get_cookies(), f)
            logger.info("Saved cookies!")


# Define your Azure AD credentials
# TODO add the id here
TENANT_ID = ""
CLIENT_ID = ""


def set_log_level(level=logging.INFO):
    azure_logger = logging.getLogger("azure")
    azure_logger.setLevel(level)
    azure_logger.propagate = True


def load_parquet_to_snowflake(
    hook: "SnowflakeHook",
    parquet_file: str,
    landing_table_name: str,
    stage_name: str,
    recreate_landing=True,
    schema_name=cct.DEFAULT_LANDING_SCHEMA,
):
    parquet_file = os.path.realpath(parquet_file)
    if not os.path.isfile(parquet_file):
        logger.error("Cannot upload settlements due to file not exists!")
        return

    file_name = os.path.basename(parquet_file)
    file_format_name = "scraper_parquet"
    logger.info("Creating file format...")
    hook.run(
        f"""
        USE SCHEMA {schema_name};
        CREATE OR REPLACE FILE FORMAT {file_format_name} TYPE = parquet;
        """
    )

    logger.info("Creating stage...")
    hook.run(
        f"""
        USE SCHEMA {schema_name};
        CREATE OR REPLACE STAGE {stage_name}
            FILE_FORMAT = {file_format_name};"""
    )

    logger.info("Put data to stage area: %s", parquet_file)
    hook.run(
        f"PUT file:///{parquet_file} @{stage_name};",
    )

    if recreate_landing:
        logger.info("Creating the landing table: %s", landing_table_name)
        columns = get_columns_in_parquets(parquet_path=parquet_file)
        column_def = ",".join(f"{column} STRING" for column in columns)
        logger.debug("Colum definition: %s", column_def)
        landing_definition = cct.LANDING_TABLE_DDL.format(
            table_name=landing_table_name, columns=column_def
        )
        logger.debug("Table definition: %s", landing_definition)
        hook.run(landing_definition)

    logger.info("Loading data into landing table")
    hook.run(
        f"""
        USE SCHEMA {schema_name};
        COPY INTO {landing_table_name}
        FROM @{stage_name}/{file_name}
        FILE_FORMAT = (TYPE = 'PARQUET')
        MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;
        """
    )

    logger.info("Loading data into landing table")
    hook.run(
        f"""
        USE SCHEMA {schema_name};
        UPDATE {landing_table_name}
        SET {cct.ETL_LOADED_TIMESTAMP_COL} = CURRENT_TIMESTAMP()
        WHERE {cct.ETL_LOADED_TIMESTAMP_COL} IS NULL
        ;
        """
    )

    logger.info("Finished loaded data to %s.%s", schema_name, landing_table_name)


def retry_stale(tries=3, delay=2, backoff=2):
    def decorator_retry(func):
        @functools.wraps(func)
        def wrapper_retry(*args, **kwargs):
            _tries, _delay = tries, delay
            while _tries > 1:
                try:
                    return func(*args, **kwargs)
                except StaleElementReferenceException as e:
                    logger.info("%s, Retrying in %s seconds...", e, _delay)
                    time.sleep(_delay)
                    _tries -= 1
                    _delay *= backoff
            return func(*args, **kwargs)

        return wrapper_retry

    return decorator_retry


def load_cookies(session: Session):
    if os.path.isfile(cct.AIRFLOW_TMP_JAR):
        cookies = pickle.loads(cct.AIRFLOW_TMP_JAR)
        session.cookies = cookies
        return session

    return session


def save_cookies(session: Session):
    with open(cct.AIRFLOW_TMP_JAR, "wb") as f:
        logger.info("Saving session to use later...")
        pickle.dump(session.cookies, f)


def get_landing_table_name(
    file_name: str | re.Pattern,
    configs: list[cct.LandingConfig],
    priority=1,
    raise_error=False,
) -> str:
    logger.info("File name: %s", file_name)
    logger.info("Table def Config: %s", configs)
    found_names = []
    for config in configs:
        pattern = config["file_pattern"]
        landing_table_name = config["landing_table_name"]
        priority = config.get("priority") or 1
        if re.search(pattern=pattern, string=file_name):
            logger.info("Found a landing table match: %s", landing_table_name)
            found_names.append((landing_table_name, priority))

    if not found_names:
        logger.info("Cannot find any name with the pattern %s", pattern)
        if raise_error:
            raise LookupError("Cannot find any landing table name!")
        return ""

    sorted_name = sorted(found_names, key=lambda x: x[1])
    for name in sorted_name:
        if name[1] == priority:
            logger.info("Found priority %s", priority)
            return name[0]

    return sorted_name[0][0]


def prepare_folder(folder_path):
    if os.path.exists(folder_path):
        logger.info("No need to create folders!")
        return

    logger.info("Creating %s", folder_path)
    os.makedirs(folder_path, exist_ok=True)


def basic_init():
    set_log_level(logging.WARNING)


basic_init()

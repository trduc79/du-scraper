import re
from typing import Literal, Optional, TypedDict, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from ..scraper.base import BaseScraper


DEFAULT_LANDING_SCHEMA = "LANDING"
DEFAULT_SNOWFLAKE_CONN_ID = "snow_conn_id"

DBT_DAG_ID = "SCRAPER_DBT_REFRESH"
CANCEL_TASK_NAME = "cancel_if_needed"
TASK_TERM_BY_SIG_TERM = "State of this instance has been externally set to failed."
LOG_FILENAME_TEMPLATE = (
    "dag_id={dag_id}/run_id={run_id}/task_id={task_id}/attempt={try_number}.log"
)

DISABLED_SCHEDULE = "DISABLED"

AIRFLOW_HOME_URL = "http://airflow-webserver.airflow.svc:8080"
AIRFLOW_LOGIN_URL = f"{AIRFLOW_HOME_URL}/login/"
AIRFLOW_LOGGED_IN_URL = f"{AIRFLOW_HOME_URL}/home"
AIRFLOW_TMP_JAR = "tmp/web.airflow"

LOG_URL_TEMPLATE = (
    "{airflow_home_url}"
    "/api/v1/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}"
    "/logs/{try_number}?full_content=true"
)


BASE_DIRECTORY = "tmp/scraper/"
PROCESSED_DIR = "mid_converted"

PROJECT_NAME = "selenium"
SCREENSHOT = "screenshot"
DOWNLOAD = "downloaded"

COOKIES_PATH = "./.token/{scraper_id}"
TOKEN_PATH = "./.token/o365_token.txt"

TOKEN_TYPE_AIRFLOW = "airflow"
TOKEN_TYPE_LOCAL = "local"

ETL_LOADED_TIMESTAMP_COL = "B__loaded_date"

LANDING_TABLE_DDL = """
CREATE OR REPLACE TABLE {table_name} (
    {columns}
);
"""

PARQUET_FILE_PATTERN = r".*\.parquet$"

PBI_DEFAULT_REFRESH_TIMEOUT = 5 * 60
PBI_DEFAULT_SLEEP_TIME = 30
PBI_ALREADY_RUNNING = "Another refresh request is already executing"
PBI_REFRESH_URL = "https://api.powerbi.com/v1.0/myorg/groups/{group_id}/datasets/{dataset_id}/refreshes"
PBI_FINISHED_STATUS = ("Completed", "Failed", "Cancelled")
PBI_STARTING_STATUS = ("NotStarted", "InProgress")
PBI_API_REFRESH_TYPE = ("ViaEnhancedApi", "ViaXmlaEndpoint")

DEFAULT_LOCK_TIME = 33

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0"
    )


class AzureConfigType(TypedDict):
    storage_account_id: str
    default_container: str
    tenant_id: str
    client_id: str
    client_secret: str
    credentials: Optional[str]


class DownloadedInfoType(TypedDict):
    blob_file: str
    local_file: str
    file_info: Optional[str]


class ConvertedType(TypedDict):
    converted_files: list[DownloadedInfoType]
    run_id: str


class DownloadedType(TypedDict):
    uploaded_files: list[DownloadedInfoType]
    run_id: str


class LandingConfig(TypedDict):
    file_pattern: str | re.Pattern
    landing_table_name: str
    priority: Optional[int]


class TokenConfigType(TypedDict):
    token_path: str
    token_backend: Literal["airflow", "local"]


class ScraperConfigType(TypedDict):
    user_name: str
    password: str
    email_address: str
    otp_seed: Optional[str]


class BaseScraperTrigger(Protocol):
    def main(
        self,
        run_id: str = None,
        scraper_id: str = None,
        remote_server: str = None,
        azure_config: AzureConfigType = None,
        token_config: TokenConfigType = None,
        scraper_config: ScraperConfigType = None,
        airflow_cookie_saver: str = None,
        execution_date: str = None,
        driver_version: str = None,
        **kwargs,
    ) -> "BaseScraper":
        """The main function will trigger the dag run"""

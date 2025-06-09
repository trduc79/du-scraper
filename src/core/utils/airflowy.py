import logging
import pickle
import re
import sys

from functools import partial
from types import TracebackType
from typing import Callable, Optional

from airflow.models import Variable
from airflow.exceptions import AirflowException

import requests
from requests import Session

from selenium import webdriver
from selenium.webdriver.edge.webdriver import WebDriver as Edge

from . import constant as cct

from .helper import CookiesProtocol, load_cookies

logger = logging.getLogger(__name__)


class AirflowCookiesSaver(CookiesProtocol):
    def __init__(self, airflow_cookie_variable_name: str) -> None:
        if not airflow_cookie_variable_name.upper().endswith("SECRET"):
            logger.warning("Name of variable have to end with _SECRET!")
            airflow_cookie_variable_name = f"{airflow_cookie_variable_name}_SECRET"
        self.airflow_cookie_var = airflow_cookie_variable_name.upper()
        super().__init__()

    def load_cookies(self, driver: Edge):
        logger.info("Loading cookies...")

        cookies = Variable.get(
            self.airflow_cookie_var,
            default_var=[],
            deserialize_json=True,
        )

        if not cookies:
            logger.info("There is no cookies at all!")
            return driver

        for cookie in cookies:
            if "expiry" in cookie:
                del cookie["expiry"]
            driver.add_cookie(cookie)

        logger.info("Loaded Cookies!")
        return driver

    def save_cookies(self, driver: webdriver.Edge):
        logger.info("Saving cookies to use later...")
        cookies = driver.get_cookies()
        Variable.set(self.airflow_cookie_var, cookies, serialize_json=True)
        logger.info("Saved cookies!")


def airflow_exception_hook(
    exc_type,
    exc_value: BaseException,
    exc_traceback: Optional[TracebackType] = None,
    executable: Callable = None,
    exception_class: Callable = AirflowException,
):
    if issubclass(exc_type, KeyboardInterrupt):
        # Ignore keyboard interrupt exception so we can terminate the running code
        # when press Ctrl+C.
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # When airflow get term in UI: AirflowException class raised.
    if issubclass(exc_type, exception_class) and executable:
        logger.info(exc_type)
        logger.info(exc_type.args)
        logger.info(exc_value)
        if exc_value:
            executable()

    logger.info("Error happened! %s", exc_type)

    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def set_up_except_hook(
    executable: Callable, exception_class: Callable = AirflowException
):
    exception_hook = partial(
        airflow_exception_hook, executable=executable, exception_class=exception_class
    )
    sys.excepthook = exception_hook


def extract_csrf_token(html_text: str):
    if not html_text:
        logger.warning("Cannot find CSRF token from empty!")
        return
    pattern = r'<input id="csrf_token"[^>]*value="([^"]+)"'
    match = re.search(pattern, html_text)
    if match:
        csrf_token = match.group(1)
        logger.info("Extracted CSRF token: %s", csrf_token)
        return csrf_token
    else:
        logger.warning("CSRF token not found")


def save_cookies(session: Session):
    with open(cct.AIRFLOW_TMP_JAR, "wb") as f:
        logger.info("Saving session to use later...")
        pickle.dump(session.cookies, f)


def login_to_airflow(user_name, password, load_session=True):
    session = Session()
    if load_session:
        session = load_cookies(session)

    res = session.get(cct.AIRFLOW_LOGIN_URL, timeout=30)
    csrf_token = extract_csrf_token(res.text)

    if not csrf_token:
        if res.url == cct.AIRFLOW_LOGGED_IN_URL:
            logger.info("Already logged in to Airflow")
            return session

        logger.error("Cannot login to airflow to find log!")
        return

    payload = {
        "csrf_token": csrf_token,
        "username": user_name,
        "password": password,
    }

    res = session.post(cct.AIRFLOW_LOGIN_URL, timeout=30, data=payload)

    if res.status_code == requests.codes["OK"]:
        return session
    elif res.url == cct.AIRFLOW_LOGGED_IN_URL:
        return session
    else:
        logger.error("Cannot login to Airflow")
        return

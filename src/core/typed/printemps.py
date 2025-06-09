"""
This module defines a collection of `TypedDict` classes
that represent the structure of various data models
used in a scraping application. These data models are used to
define the expected structure of data retrieved from external sources,
ensuring type safety and consistency.
"""

from typing import TypedDict

from .base import Result
from .lafayette import LafayetteProductType


class PrintempsPageType(TypedDict):
    results: list[Result]


class PrintempsProductType(LafayetteProductType):
    pass

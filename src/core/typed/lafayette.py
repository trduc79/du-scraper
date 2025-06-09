"""
This module defines a collection of `TypedDict` classes
that represent the structure of various data models
used in a scraping application. These data models are used to
define the expected structure of data retrieved from external sources,
ensuring type safety and consistency.
"""

from typing import TypedDict

from .base import (
    Age,
    BaseOption,
    Brand,
    Category,
    Gender,
    Image,
    Pagination,
    Price,
    PriceRange,
    Stock,
    VariantOption,
)

class LafayetteProductType(TypedDict):
    ages: list[Age]
    appMobCode: str
    baseOptions: list[BaseOption]
    baseProduct: str
    brand: Brand
    categories: list[Category]
    code: str
    exclusiveProduct: bool
    gender: Gender
    images: list[Image]
    isMarketPlaceProduct: bool
    luxury: str
    name: str
    newProduct: bool
    price: Price
    priceRange: PriceRange
    productLine: str
    sapCode: str
    stock: Stock
    url: str
    variantOptions: list[VariantOption]


class LafayettePageType(TypedDict):
    products: list[LafayetteProductType]
    pagination: Pagination

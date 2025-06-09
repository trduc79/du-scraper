"""
This module defines a collection of `TypedDict` classes
that represent the structure of various data models
used in a scraping application. These data models are used to
define the expected structure of data retrieved from external sources,
ensuring type safety and consistency.
"""

from typing import TypedDict

from .base import (
    MasterBrand,
    OtherPrice,
    Pagination,
    Price,
    RoundelCategoryBadge,
    Stock,
    Image,
    TopPromotion,
    VariantValueCategory,
)


class MarionnaudProductType(TypedDict):
    absentInHybrisProduct: bool
    ageRestricted: bool
    allowedOnMobileApp: bool
    averageRating: float
    categoryNameHierarchy: str
    charity: bool
    classifications: list
    code: str
    defaultSku: str
    digitalProduct: bool
    displayOnly: bool
    engravingEnabled: bool
    external: bool
    fastlane: bool
    gwp: bool
    hidePromotionsAndMarkdownPrice: bool
    homeDeliveryOnly: bool
    images: list[Image]
    inStockFlag: bool
    inactiveInHybris: bool
    isComingSoon: bool
    isGiftWrapAvailable: bool
    isLoyaltyProduct: bool
    isOfflineProduct: bool
    marketplaceProduct: bool
    masterBrand: MasterBrand
    maxOrderQuantity: int
    minOrderQuantity: int
    name: str
    newIn: bool
    numberOfReviews: int
    otherPrices: list[OtherPrice]
    paidLoyalty: bool
    pharmacy: bool
    potentialLoyaltyPoints: int
    preOrder: bool
    price: Price
    priceRange: dict
    productLoyaltyPoints: int
    promotions: list
    purchasable: bool
    rangeName: str
    restrictedForWishlist: bool
    reviewDisabled: bool
    reviewEnabled: bool
    roundelCategoryBadge: RoundelCategoryBadge
    roundelCategoryBadges: list
    showVATShip: bool
    stock: Stock
    subscription: bool
    supplierDescription: str
    topPromotion: TopPromotion
    url: str
    variantValueCategories: list[VariantValueCategory]
    variantsNumber: int
    whiteLabelShopProduct: bool


class MarionnaudPageType(TypedDict):
    categoryCode: str
    pagination: Pagination
    products: list[MarionnaudProductType]

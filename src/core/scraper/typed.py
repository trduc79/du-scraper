"""
This module defines a collection of `TypedDict` classes
that represent the structure of various data models
used in a scraping application. These data models are used to
define the expected structure of data retrieved from external sources,
ensuring type safety and consistency.
"""

from typing import Optional, TypedDict


class ParentVariantCategory(TypedDict):
    code: str
    hasImage: bool
    name: str
    priority: int


class OtherPrice(TypedDict):
    currencyIso: str
    formattedValue: str
    isTpr: bool
    priceSource: str
    priceType: str
    savePrice: str
    savePriceValue: float
    value: float


class PriceData(TypedDict):
    currencyIso: str
    formattedValue: str
    priceType: str
    value: float


class Stock(TypedDict):
    stockLevel: int
    stockLevelStatus: str


class ThumbnailImage(TypedDict):
    url: str
    altText: str


class VariantOptionQualifier(TypedDict):
    code: str
    name: str
    qualifier: str
    value: str
    image: ThumbnailImage


class VariantOption(TypedDict):
    code: str
    ean: str
    otherPrices: list[OtherPrice]
    priceData: PriceData
    pricePerUnit: PriceData
    stock: Stock
    url: str
    variantOptionQualifiers: list[VariantOptionQualifier]


class VariantValueCategory(TypedDict):
    code: str
    name: str
    sequence: int


class VariantType(TypedDict):
    elements: list
    isLeaf: bool
    parentVariantCategory: ParentVariantCategory
    variantOption: VariantOption
    variantValueCategory: VariantValueCategory


class Option(TypedDict):
    code: str
    priceData: PriceData
    stock: Stock | None
    url: str
    variantOptionQualifiers: list[VariantOptionQualifier]


class Selected(TypedDict):
    code: str
    engravingEnabled: bool
    priceData: PriceData
    stock: Stock
    url: str
    variantOptionQualifiers: list[VariantOptionQualifier]


class BaseOption(TypedDict):
    options: list[Option]
    selected: Selected
    variantType: str


class ProductType(TypedDict):
    baseProduct: str
    baseOptions: list[BaseOption]
    url: str
    variantMatrix: list[VariantType]


class Pagination(TypedDict):
    currentPage: int
    pageSize: int
    sort: str
    pageSizeOptions: list[int]
    totalPages: int
    totalResults: int


class Price(TypedDict):
    currencyIso: str
    formattedValue: str
    priceType: str
    value: float


class MasterBrand(TypedDict):
    engravingEnabled: bool
    hidePromotionsAndMarkdownPrice: bool
    hideRoundel: bool
    limitative: bool
    name: str


class RoundelCategoryBadge(TypedDict):
    backgroundColorHexCode: str
    image: dict
    label: str
    textColorHexCode: str


class TopPromotionBadge(TypedDict):
    backgroundColorHexCode: str
    image: dict
    label: str
    textColorHexCode: str


class TopPromotionReward(TypedDict):
    rewardType: str


class TopPromotion(TypedDict):
    badge: TopPromotionBadge
    reward: TopPromotionReward


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
    images: list["Image"]
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


class RegularRetailPrice(TypedDict):
    currencyIso: str
    formattedValue: str
    priceType: str
    value: float


class PriceRange(TypedDict):
    maxPrice: Price
    minPrice: Price


class VariantOptionImage(TypedDict):
    altText: str
    format: str
    imageType: str
    url: str


class Age(TypedDict):
    name: str


class Brand(TypedDict):
    code: str
    name: str
    webChannel: bool


class Category(TypedDict):
    categoryType: str
    name: str


class Image(TypedDict):
    altText: str | None
    format: str
    imageType: str
    url: str


class Gender(TypedDict):
    code: str
    name: str


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



class Media(TypedDict):
    mediaPath: str
    mediaPathTablet: str
    mediaPathMobile: str
    isBaseVA: bool
    isVideo: int


class Taille(TypedDict):
    refId: int
    stk: int
    ean: int
    label: str
    isTU: bool


class Sibling(TypedDict):
    itemID: int
    markColor: str
    markColorCode: str
    medias: list[Media]
    tailles: list[Taille]
    ficheProduitUrl: str


class Prices(TypedDict):
    real: int
    aff: str
    bar: str
    avp: str


class Hit(TypedDict):
    objectID: str
    itemID: int
    modeleID: int
    saleID: int
    itemLabel: str
    itemName: Optional[str]
    mark: str
    color: str
    categoryMenus: list[str]
    siblings: list[Sibling]
    ficheProduitUrl: str
    markUrl: str
    medias: list[Media]
    pictos: str
    isTeasing: bool
    dateLancementTeasing: Optional[str]
    isMultiPrice: bool
    prices: Prices
    remiseSoldes: int
    tailles: list[Taille]
    position: int
    currency: str
    univers: str
    universLabel: str
    isMarketPlace: Optional[bool]
    secondeMain: bool


class Result(TypedDict):
    exhaustiveFacetsCount: bool
    exhaustiveNbHits: bool
    facets: dict
    facets_stats: dict
    hits: list[Hit]
    hitsPerPage: str
    index: str
    nbHits: int
    nbPages: int
    page: int
    params: str
    processingTimeMS: int
    query: Optional[str]


class PrintempsPageType(TypedDict):
    results: list[Result]


class Merchant(TypedDict):
    id: str
    label: str
    url: Optional[str]
    shippings: list


class WarehouseStock(TypedDict):
    stock: int
    reserved: int


class StockDetails(TypedDict):
    warehouse: dict[str, WarehouseStock]
    total_stock: int
    total_reserved: int


class Product(TypedDict):
    refId: str
    dispo: str
    pxAff: int
    pxBar: str
    pxAvp: str
    pxAffFormatted: str
    pxBarFormatted: str
    pxAvpFormatted: str
    inPanier: int
    label: str
    generiqueLabel: str
    attributeISO: str
    ordre: str
    description: Optional[str]
    dimension: Optional[str]
    merchant: Merchant
    quantity_available: int
    stockPantin: int
    stockMp: int
    stockHaussman: int
    resaPantin: int
    resaMp: int
    resaHaussman: int
    stock: StockDetails


# PrintempsProductType = dict[str, Product]

class PrintempsProductType(LafayetteProductType):
    pass

class SommelierProductType(TypedDict):
    name: str
    id_sommelier: str
    designer_name: str
    id_designer: str
    image: str
    dosage: str
    annee: str
    type: str
    sexe: str
    min_price: dict[str, float]
    perfume_color: str
    url_website: str
    url_website_designer: str
    is_sample: bool
    is_sample_ship: bool


class ZaraProductType(TypedDict):
    id: str
    name: str
    description: str
    price: float
    currency: str
    image_url: str
    link: str
    category: str
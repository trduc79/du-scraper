"""
This module defines a collection of `TypedDict` classes
that represent the structure of various data models
used in a scraping application. These data models are used to
define the expected structure of data retrieved from external sources,
ensuring type safety and consistency.
"""

from typing import Optional, TypedDict, Any


class Area(TypedDict):
    x1: int
    y1: int
    x2: int
    y2: int


class Link(TypedDict):
    datatype: str
    id: int
    code: str
    seoKeyword: str
    type: str
    seoId: str


class AreaLink(TypedDict):
    url: str
    queryParams: str


class Region(TypedDict):
    area: Area
    link: Link
    areaLink: AreaLink
    showIcon: bool


class ExtraInfo(TypedDict, total=False):
    originalName: str
    assetId: str
    deliveryUrl: str
    deliveryPath: str


class XMedia(TypedDict):
    datatype: str
    set: int
    type: str
    kind: str
    path: str
    name: str
    width: int
    height: int
    timestamp: str
    allowedScreens: list[str]
    extraInfo: ExtraInfo
    url: str
    regions: list[Region]


class Color(TypedDict):
    id: str
    productId: int
    name: str
    stylingId: str
    xmedia: list[XMedia]


class Detail(TypedDict):
    reference: str
    displayReference: str
    colors: list[Color]
    extraInfo: dict[str, Any]
    canonicalReference: str


class Brand(TypedDict):
    brandId: int
    brandGroupId: int
    brandGroupCode: str

class CommercialComponent(TypedDict):
    id: int
    brand: Brand
    availability: str
    reference: str
    type: str
    kind: str
    familyName: str
    xmedia: list[XMedia]
    name: str
    price: int
    description: str
    seo: "SEOProduct"
    section: int
    sectionName: str
    detail: Detail


class SEOProduct(TypedDict):
    keyword: str
    seoProductId: str
    discernProductId: int
    irrelevant: Optional[bool]


class SEOCate(TypedDict):
    seoCategoryId: int
    keyword: str
    irrelevant: bool
    isHiddenInMenu: bool


class MarketingMetaInfo(TypedDict):
    type: str
    isDivider: bool
    isSticky: bool
    mappingInfo: list[dict[str, Any]]
    showLinksIcon: bool


class ExtraInfoBlock(TypedDict, total=False):
    isDivider: bool
    highlightPrice: bool
    hideProductInfo: bool
    isAddToCartInGridDisabled: bool
    duplicateReference: bool


class Style(TypedDict):
    hideGridLines: bool


class Attributes(TypedDict):
    mustDisplayContent: bool
    showSubcategories: bool
    isDivider: bool
    isLineBreak: bool
    isTitle: bool


class ZaraCategoryType(TypedDict):
    id: int
    name: str
    sectionName: str
    subcategories: list["ZaraCategoryType"]
    layout: str
    contentType: str
    gridLayout: str
    seo: SEOCate
    attributes: Attributes
    key: str
    isRedirected: bool
    isSelected: bool
    hasSubcategories: bool
    irrelevant: bool
    menuLevel: int


class ZaraCategoryResponseType(TypedDict):
    categories: list[ZaraCategoryType]



class ZaraProductType(TypedDict):
    id: str
    type: str
    isPinned: bool
    layout: str
    commercialComponents: list[CommercialComponent]
    seo: SEOProduct
    tagTypes: list[str]
    marketingMetaInfo: MarketingMetaInfo
    extraInfo: ExtraInfoBlock
    style: Style
    tags: list[str]
    hasStickyBanner: bool
    needsSeparator: bool


class ZaraProductGroupType(TypedDict):
    id: str
    type: str
    elements: list[ZaraProductType]
    attributeList: list[dict[str, str]]
    hasStickyBanner: str


class ZaraCategoryProductType(TypedDict):
    productGroups: list[ZaraProductGroupType]
    

from dataclasses import dataclass
from typing import Optional


class Gender:
    MALE= 'M'
    FEMALE= 'F'
    ALL= 'all'

@dataclass
class NoteCategory:
    name: str


@dataclass
class Note:
    category: NoteCategory
    name: str
    type: str
    percentage: float


@dataclass
class PerfumeVariant:
    sku: str
    size: float
    is_sampling: bool
    in_stock: bool
    price: float
    currency: str
    vendor: str
    link: str


@dataclass
class Brand:
    name: str
    description: Optional[str] = None
    logo_b64: Optional[str] = None


@dataclass
class Nose:
    name: str
    description: Optional[str] = None
    avatar_b64: Optional[str] = None


@dataclass
class PerfumeScraper:
    name: str
    description: Optional[str] = None
    family: Optional[str] = None
    type: Optional[str] = None
    gender:  Optional[str] = None
    year: Optional[str] = None
    season: Optional[str] = None
    chems: list[str] = None
    picture_b64: Optional[str] = None
    brand: Brand = None
    noses: Optional[list[Nose]] = None
    notes: list[Note] = None
    variants: list[PerfumeVariant] = None
    raw: dict = None


@dataclass
class SearchResult:
    id: str
    name: str
    brand_name: str
    brand_id: str
    provider_name: str

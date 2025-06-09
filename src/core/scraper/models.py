from datetime import datetime
from pydantic import BaseModel, Field

class ScraperOutput(BaseModel):
    """
    Base class for scraper output.
    """
    source: str = Field(..., description="The source of the product.")
    parent_perfume_id: str = Field(..., description="The ID of the associated perfume. In source system.")
    id: str = Field(..., description="The unique identifier of the product.")
    price: float | None = Field(..., description="The price of the product.")
    currency: str | None = Field('EUR', description="The currency of the price.")
    size: float | str | None = Field(None, description="The size of the product.")
    size_unit: str | None = Field(None, description="The unit of the size.")
    link: str | None = Field(None, description="The link to the product.")
    line: str | None = Field(None, description="The line of the product.")
    vendor: str | None = Field(..., description="The vendor of the product.")
    sku: str | None = Field(None, description="The SKU of the product.")
    is_sampling: bool = Field(False, description="Indicates if the product is a sample.")
    in_stock: bool = Field(True, description="Indicates if the product is in stock.")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="The creation timestamp.")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="The last update timestamp.")


def validate():
    data = {
        "source": "example_source",
        "perfume_id": 123,
        "price": 49.99,
        "currency": "EUR",
        "sku": "ABC123",
        "size": 50,
        "is_sampling": False,
        "in_stock": True,
        "vendor": "VendorName",
        "link": "http://example.com/product",
    }
    validated_data = ScraperOutput.model_validate(data)
    print(validated_data.model_dump_json(indent=4))

if __name__ == "__main__":
    validate()
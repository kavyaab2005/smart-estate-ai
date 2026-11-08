from pydantic import BaseModel
from typing import List

class PropertyPriceRequest(BaseModel):
    property_type: str
    listing_type: str
    area_sqft: float
    bhk: int
    bedrooms: int
    floor: int
    total_floors: int
    property_age_years: int
    furnishing: str
    parking: int
    city: str
    amenities: List[str] = []

class PropertyPriceResponse(BaseModel):
    predicted_price: float
    difference_percent: float
    insight_text: str
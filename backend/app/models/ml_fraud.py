from pydantic import BaseModel
from typing import List, Optional

class FraudScoreRequest(BaseModel):
    property_id: Optional[str] = None
    property_type: str
    listing_type: str
    price: float
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
    is_verified: bool = False

class FraudFlag(BaseModel):
    level: str
    reason: str

class FraudScoreResponse(BaseModel):
    trust_score: float
    risk_level: str
    flags: List[FraudFlag]
    reasons: List[str]
    is_verified: bool = False
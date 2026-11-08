from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID


class ChatMessageRequest(BaseModel):
    session_id: Optional[UUID] = None
    message: str


class ChatMessageResponse(BaseModel):
    session_id: UUID
    response_text: str
    referenced_property_ids: List[str]


class RecommendationItem(BaseModel):
    property_id: str
    match_score: int
    reason_text: str


class RecommendationsResponse(BaseModel):
    recommendations: List[RecommendationItem]


class NearbyPlace(BaseModel):
    name: str
    distance_km: float


class NearbyFacilities(BaseModel):
    schools: List[NearbyPlace]
    colleges: List[NearbyPlace]
    hospitals: List[NearbyPlace]
    metro: List[NearbyPlace]
    bus_stops: List[NearbyPlace]
    malls: List[NearbyPlace]
    restaurants: List[NearbyPlace]
    parks: List[NearbyPlace]


class LocationIntelResponse(BaseModel):
    nearby: NearbyFacilities
    location_score: int
    data_source: str = "live"
    from_cache: bool = False


class AnalyzePropertyResponse(BaseModel):
    price_score: Optional[int] = None
    location_score: Optional[int] = None
    amenity_score: Optional[int] = None
    market_price_score: Optional[int] = None
    document_score: Optional[int] = None
    fraud_score: Optional[int] = None
    requirement_match_score: Optional[int] = None
    overall_score: int
    recommendation_text: str    
from pydantic import BaseModel
from pydantic import field_validator
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.models.property import PropertyTypeEnum


class PropertyCreate(BaseModel):
    title: str
    description: Optional[str] = None
    property_type: Optional[PropertyTypeEnum] = None
    listing_type: str  # "buy" or "rent"
    price: float
    area_sqft: Optional[float] = None
    bhk: Optional[int] = None
    bathrooms: Optional[int] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    property_age_years: Optional[int] = None
    furnishing: Optional[str] = None
    parking: Optional[bool] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    city: Optional[str] = None
    epid: Optional[str] = None

    @field_validator("city", mode="before")
    @classmethod
    def normalize_city(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return v.strip().title()

    @field_validator("epid", mode="before")
    @classmethod
    def check_epid(cls, v):
        if v is None:
            return None
        v = str(v).strip()
        if v == "":
            return None
        if not (v.isdigit() and len(v) == 10):
            raise ValueError("ePID must be exactly 10 digits")
        return v


class PropertyUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    property_type: Optional[PropertyTypeEnum] = None
    listing_type: Optional[str] = None
    price: Optional[float] = None
    area_sqft: Optional[float] = None
    bhk: Optional[int] = None
    bathrooms: Optional[int] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    property_age_years: Optional[int] = None
    furnishing: Optional[str] = None
    parking: Optional[bool] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    city: Optional[str] = None
    epid: Optional[str] = None
    status: Optional[str] = None

    @field_validator("city", mode="before")
    @classmethod
    def normalize_city(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return v.strip().title()

    @field_validator("epid", mode="before")
    @classmethod
    def check_epid(cls, v):
        if v is None:
            return None
        v = str(v).strip()
        if v == "":
            return None
        if not (v.isdigit() and len(v) == 10):
            raise ValueError("ePID must be exactly 10 digits")
        return v


class PropertyResponse(BaseModel):
    id: UUID
    agent_id: Optional[UUID]
    title: str
    description: Optional[str]
    property_type: Optional[PropertyTypeEnum]
    listing_type: Optional[str]
    price: float
    area_sqft: Optional[float]
    bhk: Optional[int]
    bathrooms: Optional[int]
    floor: Optional[int]
    total_floors: Optional[int]
    property_age_years: Optional[int]
    furnishing: Optional[str]
    parking: Optional[bool]
    latitude: Optional[float]
    longitude: Optional[float]
    address: Optional[str]
    city: Optional[str]
    epid: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    trust_score: Optional[int] = None

    class Config:
        from_attributes = True


class FavoriteCreate(BaseModel):
    property_id: UUID
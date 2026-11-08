import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Numeric, Boolean, DateTime, Enum, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class ListingTypeEnum(str, enum.Enum):
    buy = "buy"
    rent = "rent"


class PropertyStatusEnum(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    sold = "sold"


class PropertyTypeEnum(str, enum.Enum):
    apartment = "apartment"
    villa = "villa"
    plot = "plot"
    independent_house = "Independent House"


class Property(Base):
    __tablename__ = "properties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    title = Column(String, nullable=False)
    description = Column(String)
    property_type = Column(Enum(PropertyTypeEnum, values_callable=lambda x: [e.value for e in x]))
    listing_type = Column(Enum(ListingTypeEnum))
    price = Column(Numeric)
    area_sqft = Column(Numeric)
    bhk = Column(Integer)
    bathrooms = Column(Integer)
    floor = Column(Integer)
    total_floors = Column(Integer)
    property_age_years = Column(Integer)
    furnishing = Column(String)
    parking = Column(Boolean)
    latitude = Column(Numeric)
    longitude = Column(Numeric)
    address = Column(String)
    city = Column(String)
    epid = Column(String(10), nullable=True, index=True)
    status = Column(Enum(PropertyStatusEnum), default=PropertyStatusEnum.pending)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
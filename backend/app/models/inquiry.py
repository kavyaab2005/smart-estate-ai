import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class InquiryTypeEnum(str, enum.Enum):
    general = "general"
    schedule_visit = "schedule_visit"
    price_negotiation = "price_negotiation"

class InquiryStatusEnum(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"

class PropertyInquiry(Base):
    __tablename__ = "property_inquiries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False)
    buyer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    inquiry_type = Column(Enum(InquiryTypeEnum), default=InquiryTypeEnum.schedule_visit)
    message = Column(Text, nullable=True)
    preferred_date = Column(DateTime, nullable=True)
    status = Column(Enum(InquiryStatusEnum), default=InquiryStatusEnum.pending)
    created_at = Column(DateTime, default=datetime.utcnow)

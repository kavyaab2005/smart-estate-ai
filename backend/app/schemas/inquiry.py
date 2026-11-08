from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.models.inquiry import InquiryTypeEnum, InquiryStatusEnum

class InquiryCreate(BaseModel):
    property_id: UUID
    inquiry_type: InquiryTypeEnum = InquiryTypeEnum.schedule_visit
    message: Optional[str] = None
    preferred_date: Optional[datetime] = None

class InquiryResponse(BaseModel):
    id: UUID
    property_id: UUID
    buyer_id: UUID
    agent_id: UUID
    inquiry_type: InquiryTypeEnum
    message: Optional[str] = None
    preferred_date: Optional[datetime] = None
    status: InquiryStatusEnum
    created_at: datetime

    class Config:
        from_attributes = True


class AgentInquiryResponse(BaseModel):
    id: UUID
    property_id: UUID
    buyer_id: UUID
    agent_id: UUID
    inquiry_type: InquiryTypeEnum
    message: Optional[str] = None
    preferred_date: Optional[datetime] = None
    status: InquiryStatusEnum
    created_at: datetime
    property_title: Optional[str] = None
    property_city: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_email: Optional[str] = None

    class Config:
        from_attributes = True

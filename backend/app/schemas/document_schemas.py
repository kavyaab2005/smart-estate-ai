from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class DocumentUploadResponse(BaseModel):
    document_id: str
    file_url: str


class ExtractedFieldsSchema(BaseModel):
    owner_name: Optional[str] = None
    property_address: Optional[str] = None
    property_id: Optional[str] = None
    epid: Optional[str] = None
    survey_number: Optional[str] = None
    area: Optional[str] = None
    document_date: Optional[str] = None
    registration_number: Optional[str] = None


class FieldMatchResultSchema(BaseModel):
    field: str
    status: str  # "match" | "mismatch" | "not_found"


class DocumentVerifyResponse(BaseModel):
    extracted_fields: ExtractedFieldsSchema
    match_results: List[FieldMatchResultSchema]
    overall_status: str  # "verified" | "mismatch" | "pending"
    disclaimer: str = (
        "This AI verification is for preliminary information checking and does not "
        "replace professional or legal verification."
    )


class PropertyVerifyTarget(BaseModel):
    """Optional payload to override or supply property record details for verification."""
    owner_name: Optional[str] = None
    property_address: Optional[str] = None
    property_id: Optional[str] = None
    epid: Optional[str] = None
    survey_number: Optional[str] = None
    area: Optional[str] = None
    document_date: Optional[str] = None
    registration_number: Optional[str] = None


class DocumentResponse(BaseModel):
    document_id: str
    property_id: str
    doc_type: str
    file_url: str
    uploaded_at: datetime
    verification: Optional[DocumentVerifyResponse] = None

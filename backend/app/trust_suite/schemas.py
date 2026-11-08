import re
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


AADHAAR_PATTERN = re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b')
PAN_PATTERN = re.compile(r'\b[A-Z]{5}\d{4}[A-Z]\b', re.IGNORECASE)


def mask_identifiers(text: str) -> str:
    """
    Mask Aadhaar and PAN numbers in text before storage/logging/LLM calls.
    Returns text with identifiers replaced by masked versions.
    """
    if not text:
        return text

    def mask_aadhaar(match):
        digits = re.sub(r'[-\s]', '', match.group())
        return f"XXXX-XXXX-{digits[-4:]}"

    def mask_pan(match):
        pan = match.group().upper()
        return f"XXXXX{pan[5:9]}X"

    text = AADHAAR_PATTERN.sub(mask_aadhaar, text)
    text = PAN_PATTERN.sub(mask_pan, text)
    return text


def mask_identifiers_in_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively mask identifiers in all string values of a dict."""
    if not isinstance(data, dict):
        return data
    result = {}
    for k, v in data.items():
        if isinstance(v, str):
            result[k] = mask_identifiers(v)
        elif isinstance(v, dict):
            result[k] = mask_identifiers_in_dict(v)
        elif isinstance(v, list):
            result[k] = [mask_identifiers_in_dict(item) if isinstance(item, dict) else mask_identifiers(item) if isinstance(item, str) else item for item in v]
        else:
            result[k] = v
    return result


def mask_identifiers_in_list(data: List[Any]) -> List[Any]:
    """Recursively mask identifiers in all string values of a list."""
    if not isinstance(data, list):
        return data
    return [
        mask_identifiers_in_dict(item) if isinstance(item, dict) else
        mask_identifiers_in_list(item) if isinstance(item, list) else
        mask_identifiers(item) if isinstance(item, str) else item
        for item in data
    ]


class FindingEvidence(BaseModel):
    document_id: UUID
    document_type: str
    page: int
    field: str
    raw_value: str
    normalized_value: str


class TrustFindingSchema(BaseModel):
    """Shared Finding schema used by all trust suite features."""
    check_id: str
    category: str  # "consistency" | "integrity" | "completeness"
    severity: str  # "info" | "warning" | "critical"
    status: str    # "matched" | "mismatch" | "needs_manual_verification"
    field: Optional[str] = None
    evidence: List[FindingEvidence] = Field(default_factory=list)
    why_raised: str
    next_step: str
    seller_message: Optional[str] = None

    class Config:
        from_attributes = True


class TrustFindingSellerView(BaseModel):
    """Seller-facing view: only seller_message + document type/status."""
    category: str
    status: str
    document_type: Optional[str] = None
    seller_message: str

    class Config:
        from_attributes = True


class TrustDocumentSetCreate(BaseModel):
    property_id: UUID


class TrustDocumentSetResponse(BaseModel):
    id: UUID
    property_id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    document_count: int = 0
    review_status: Optional[str] = None

    class Config:
        from_attributes = True


class TrustDocumentCreate(BaseModel):
    document_id: UUID
    doc_type: str
    page_count: int = 0
    file_url: Optional[str] = None


class TrustDocumentResponse(BaseModel):
    id: UUID
    document_set_id: UUID
    document_id: UUID
    doc_type: str
    page_count: int
    file_url: Optional[str] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True


class TrustExtractedFieldResponse(BaseModel):
    id: UUID
    document_id: UUID
    field_name: str
    raw_value: Optional[str] = None
    normalized_value: Optional[str] = None
    page_number: int
    extracted_at: datetime
    extraction_method: Optional[str] = None

    class Config:
        from_attributes = True


class TrustFindingCreate(BaseModel):
    check_id: str
    category: str
    severity: str
    status: str
    field_name: Optional[str] = None
    evidence_json: List[Dict[str, Any]] = Field(default_factory=list)
    why_raised: str
    next_step: str
    seller_message: Optional[str] = None


class TrustFindingResponse(BaseModel):
    id: UUID
    document_set_id: UUID
    check_id: str
    category: str
    severity: str
    status: str
    field_name: Optional[str] = None
    evidence_json: List[Dict[str, Any]] = Field(default_factory=list)
    why_raised: str
    next_step: str
    seller_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TrustReviewQueueResponse(BaseModel):
    id: UUID
    document_set_id: UUID
    property_id: UUID
    status: str
    priority: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TrustAdminChecklistItem(BaseModel):
    item_key: str
    label: str
    is_applicable: bool = True
    verified: bool = False
    note: Optional[str] = None
    evidence_doc_ids: List[UUID] = Field(default_factory=list)


class TrustAdminChecklistResponse(BaseModel):
    id: UUID
    review_queue_id: UUID
    item_key: str
    label: str
    is_applicable: bool
    verified: bool
    note: Optional[str] = None
    evidence_doc_ids: List[UUID] = Field(default_factory=list)
    updated_at: datetime

    class Config:
        from_attributes = True


class TrustAdminDecisionResponse(BaseModel):
    id: UUID
    review_queue_id: UUID
    admin_id: Optional[UUID] = None
    action: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    checklist_snapshot_json: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TrustScoreBreakdownResponse(BaseModel):
    id: UUID
    review_queue_id: UUID
    automated_checks_total: int
    automated_checks_passed: int
    admin_checks_total: int
    admin_checks_passed: int
    score_percentage: Dict[str, float]
    breakdown_json: Dict[str, Any]
    computed_at: datetime

    class Config:
        from_attributes = True


DEFAULT_CHECKLIST_ITEMS = [
    {"item_key": "owner_name_matched", "label": "Owner name matched across documents"},
    {"item_key": "survey_number_matched", "label": "Survey number matched across documents"},
    {"item_key": "area_matched", "label": "Area measurements matched across documents"},
    {"item_key": "ec_checked", "label": "Encumbrance Certificate verified manually"},
    {"item_key": "registration_details_checked", "label": "Registration details verified manually"},
    {"item_key": "dues_checked", "label": "Property dues/taxes checked manually"},
    {"item_key": "identity_verified", "label": "Seller identity verified (with consent)"},
]
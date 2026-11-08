from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.trust_suite.models import (
    TrustDocumentSet,
    TrustDocument,
    TrustExtractedField,
    TrustFinding,
    TrustReviewQueue,
    TrustAdminChecklist,
    TrustAdminDecision,
    TrustScoreBreakdown,
)
from app.models.property import Property, PropertyStatusEnum
from app.models.user import User
from app.models.common import Document
from app.trust_suite.schemas import mask_identifiers, mask_identifiers_in_dict, mask_identifiers_in_list


def create_document_set(db: Session, property_id: UUID, created_by: UUID) -> TrustDocumentSet:
    """Create a new trust document set."""
    doc_set = TrustDocumentSet(
        property_id=property_id,
        created_by=created_by,
    )
    db.add(doc_set)
    db.flush()
    return doc_set


def get_document_set(db: Session, doc_set_id: UUID) -> Optional[TrustDocumentSet]:
    """Get a document set by ID (no lock, for read-only operations)."""
    return db.query(TrustDocumentSet).filter(TrustDocumentSet.id == doc_set_id).first()


def get_document_set_for_update(db: Session, doc_set_id: UUID) -> Optional[TrustDocumentSet]:
    """Get a document set by ID with row lock (SELECT FOR UPDATE).
    
    Use ONLY for write operations where the document set will be modified.
    """
    return db.query(TrustDocumentSet).filter(TrustDocumentSet.id == doc_set_id).with_for_update().first()


def get_document_sets_by_property(db: Session, property_id: UUID) -> List[TrustDocumentSet]:
    """Get all document sets for a property."""
    return db.query(TrustDocumentSet).filter(TrustDocumentSet.property_id == property_id).all()


def get_document_sets_by_owner(db: Session, owner_id: UUID) -> List[TrustDocumentSet]:
    """Get all document sets for properties owned by a user."""
    return db.query(TrustDocumentSet).join(Property).filter(Property.agent_id == owner_id).all()


def create_trust_document(
    db: Session,
    document_set_id: UUID,
    document_id: UUID,
    doc_type: str,
    page_count: int,
    file_url: str,
) -> TrustDocument:
    """Create a trust document record."""
    doc = TrustDocument(
        document_set_id=document_set_id,
        document_id=document_id,
        doc_type=doc_type,
        page_count=page_count,
        file_url=file_url,
    )
    db.add(doc)
    db.flush()
    return doc


def get_trust_documents(db: Session, document_set_id: UUID) -> List[TrustDocument]:
    """Get all trust documents for a document set."""
    return db.query(TrustDocument).filter(TrustDocument.document_set_id == document_set_id).all()


def create_extracted_fields(
    db: Session,
    document_id: UUID,
    fields: List[Dict[str, Any]],
) -> List[TrustExtractedField]:
    """Create extracted field records. Masks Aadhaar/PAN in raw_value and normalized_value before storage."""
    results = []
    for field_data in fields:
        raw_value = field_data.get("raw_value")
        normalized_value = field_data.get("normalized_value")
        field = TrustExtractedField(
            document_id=document_id,
            field_name=field_data["field_name"],
            raw_value=mask_identifiers(raw_value) if raw_value else None,
            normalized_value=mask_identifiers(normalized_value) if normalized_value else None,
            page_number=field_data.get("page_number", 1),
            extraction_method=field_data.get("extraction_method", "unknown"),
        )
        db.add(field)
        results.append(field)
    db.flush()
    return results


def get_extracted_fields(db: Session, document_id: UUID) -> List[TrustExtractedField]:
    """Get all extracted fields for a document."""
    return db.query(TrustExtractedField).filter(TrustExtractedField.document_id == document_id).all()


def create_findings(
    db: Session,
    document_set_id: UUID,
    findings: List[Dict[str, Any]],
) -> List[TrustFinding]:
    """Create finding records. Masks Aadhaar/PAN in why_raised, next_step, seller_message, and evidence_json before storage."""
    results = []
    for finding_data in findings:
        evidence = finding_data.get("evidence", [])
        masked_evidence = mask_identifiers_in_list(evidence) if evidence else []
        finding = TrustFinding(
            document_set_id=document_set_id,
            check_id=finding_data["check_id"],
            category=finding_data["category"],
            severity=finding_data["severity"],
            status=finding_data["status"],
            field_name=finding_data.get("field_name"),
            evidence_json=masked_evidence,
            why_raised=mask_identifiers(finding_data["why_raised"]),
            next_step=mask_identifiers(finding_data["next_step"]),
            seller_message=mask_identifiers(finding_data["seller_message"]) if finding_data.get("seller_message") else None,
        )
        db.add(finding)
        results.append(finding)
    db.flush()
    return results


def get_findings(db: Session, document_set_id: UUID) -> List[TrustFinding]:
    """Get all findings for a document set."""
    return db.query(TrustFinding).filter(TrustFinding.document_set_id == document_set_id).all()


def create_review_queue(
    db: Session,
    document_set_id: UUID,
    property_id: UUID,
    priority: int,
    status: str = "flagged_for_review",
) -> TrustReviewQueue:
    """Create a review queue entry."""
    queue = TrustReviewQueue(
        document_set_id=document_set_id,
        property_id=property_id,
        priority=priority,
        status=status,
    )
    db.add(queue)
    db.flush()
    return queue


def get_review_queue(db: Session, document_set_id: UUID) -> Optional[TrustReviewQueue]:
    """Get review queue by document set ID (no lock, for read-only operations)."""
    return db.query(TrustReviewQueue).filter(TrustReviewQueue.document_set_id == document_set_id).first()


def get_review_queue_no_lock(db: Session, queue_id: UUID) -> Optional[TrustReviewQueue]:
    """Get review queue by queue ID without locking (for read-only operations)."""
    return db.query(TrustReviewQueue).filter(TrustReviewQueue.id == queue_id).first()


def get_review_queue_by_id(db: Session, queue_id: UUID) -> Optional[TrustReviewQueue]:
    """Get review queue by queue ID (alias for get_review_queue_no_lock)."""
    return get_review_queue_no_lock(db, queue_id)


def get_review_queue_for_update(db: Session, queue_id: UUID) -> Optional[TrustReviewQueue]:
    """Get review queue by queue ID with row lock (SELECT FOR UPDATE).
    
    Use ONLY for decision/checklist update operations where a write will follow.
    Lock order: queue row first, then property row (if needed).
    """
    return db.query(TrustReviewQueue).filter(TrustReviewQueue.id == queue_id).with_for_update().first()


def update_review_queue_status(db: Session, queue_id: UUID, status: str) -> Optional[TrustReviewQueue]:
    """Update review queue status."""
    queue = get_review_queue_by_id(db, queue_id)
    if queue:
        queue.status = status
        if status == "in_review" and not queue.started_at:
            queue.started_at = datetime.utcnow()
        elif status in ("approved", "rejected"):
            queue.completed_at = datetime.utcnow()
        db.flush()
    return queue


def get_review_queues(
    db: Session,
    status: Optional[str] = None,
    flagged_first: bool = True,
) -> List[TrustReviewQueue]:
    """Get review queues, optionally filtered by status, with flagged first ordering."""
    query = db.query(TrustReviewQueue)
    if status:
        query = query.filter(TrustReviewQueue.status == status)
    
    if flagged_first:
        query = query.order_by(TrustReviewQueue.priority.asc(), TrustReviewQueue.created_at.asc())
    else:
        query = query.order_by(TrustReviewQueue.created_at.desc())
    
    return query.all()


def create_checklist_items(
    db: Session,
    review_queue_id: UUID,
    items: List[Dict[str, Any]],
) -> List[TrustAdminChecklist]:
    """Create or update checklist items. Masks Aadhaar/PAN in note before storage."""
    results = []
    for item_data in items:
        note = item_data.get("note")
        item = TrustAdminChecklist(
            review_queue_id=review_queue_id,
            item_key=item_data["item_key"],
            label=item_data["label"],
            is_applicable=item_data.get("is_applicable", True),
            verified=item_data.get("verified", False),
            note=mask_identifiers(note) if note else None,
            evidence_doc_ids=item_data.get("evidence_doc_ids", []),
        )
        db.add(item)
        results.append(item)
    db.flush()
    return results


def get_checklist_items(db: Session, review_queue_id: UUID) -> List[TrustAdminChecklist]:
    """Get all checklist items for a review queue."""
    return db.query(TrustAdminChecklist).filter(TrustAdminChecklist.review_queue_id == review_queue_id).all()


def update_checklist_item(
    db: Session,
    item_id: UUID,
    is_applicable: Optional[bool] = None,
    verified: Optional[bool] = None,
    note: Optional[str] = None,
    evidence_doc_ids: Optional[List[UUID]] = None,
) -> Optional[TrustAdminChecklist]:
    """Update a checklist item. Masks Aadhaar/PAN in note before storage."""
    item = db.query(TrustAdminChecklist).filter(TrustAdminChecklist.id == item_id).first()
    if item:
        if is_applicable is not None:
            item.is_applicable = is_applicable
        if verified is not None:
            item.verified = verified
        if note is not None:
            item.note = mask_identifiers(note)
        if evidence_doc_ids is not None:
            item.evidence_doc_ids = evidence_doc_ids
        item.updated_at = datetime.utcnow()
        db.flush()
    return item


def create_admin_decision(
    db: Session,
    review_queue_id: UUID,
    admin_id: UUID,
    action: str,
    previous_status: str,
    new_status: str,
    checklist_snapshot: Dict[str, Any],
    reason: Optional[str] = None,
    notes: Optional[str] = None,
) -> TrustAdminDecision:
    """Create an admin decision record (append-only audit log). Masks Aadhaar/PAN in reason, notes, and checklist_snapshot before storage."""
    masked_checklist_snapshot = mask_identifiers_in_dict(checklist_snapshot) if checklist_snapshot else {}
    decision = TrustAdminDecision(
        review_queue_id=review_queue_id,
        admin_id=admin_id,
        action=action,
        previous_status=previous_status,
        new_status=new_status,
        checklist_snapshot_json=masked_checklist_snapshot,
        reason=mask_identifiers(reason) if reason else None,
        notes=mask_identifiers(notes) if notes else None,
    )
    db.add(decision)
    db.flush()
    return decision


def get_admin_decisions(db: Session, review_queue_id: UUID) -> List[TrustAdminDecision]:
    """Get all admin decisions for a review queue."""
    return db.query(TrustAdminDecision).filter(TrustAdminDecision.review_queue_id == review_queue_id).order_by(TrustAdminDecision.created_at.asc()).all()


def create_score_breakdown(
    db: Session,
    review_queue_id: UUID,
    automated_checks_total: int,
    automated_checks_passed: int,
    admin_checks_total: int,
    admin_checks_passed: int,
    score_percentage: Dict[str, float],
    breakdown_json: Dict[str, Any],
) -> TrustScoreBreakdown:
    """Create or update score breakdown."""
    breakdown = TrustScoreBreakdown(
        review_queue_id=review_queue_id,
        automated_checks_total=automated_checks_total,
        automated_checks_passed=automated_checks_passed,
        admin_checks_total=admin_checks_total,
        admin_checks_passed=admin_checks_passed,
        score_percentage=score_percentage,
        breakdown_json=breakdown_json,
    )
    db.add(breakdown)
    db.flush()
    return breakdown


def get_score_breakdown(db: Session, review_queue_id: UUID) -> Optional[TrustScoreBreakdown]:
    """Get score breakdown for a review queue."""
    return db.query(TrustScoreBreakdown).filter(TrustScoreBreakdown.review_queue_id == review_queue_id).first()


def get_property(db: Session, property_id: UUID) -> Optional[Property]:
    """Get property by ID (no lock, for read-only operations).
    
    Use for: download, seller views, buyer verification endpoints.
    """
    return db.query(Property).filter(Property.id == property_id).first()


def get_property_for_update(db: Session, property_id: UUID) -> Optional[Property]:
    """Get property by ID with row lock (SELECT FOR UPDATE).
    
    Use ONLY for: upload revert-on-reupload path and admin decision path.
    Lock order: queue row first (get_review_queue_for_update), then property row.
    """
    return db.query(Property).filter(Property.id == property_id).with_for_update().first()


def update_property_status(db: Session, property_id: UUID, status: PropertyStatusEnum) -> Optional[Property]:
    """Update property status."""
    prop = get_property(db, property_id)
    if prop:
        prop.status = status
        prop.updated_at = datetime.utcnow()
        db.flush()
    return prop


def get_property_owner_id(db: Session, property_id: UUID) -> Optional[UUID]:
    """Get the owner (agent) ID for a property."""
    prop = get_property(db, property_id)
    return prop.agent_id if prop else None


def get_user(db: Session, user_id: UUID) -> Optional[User]:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_document(db: Session, document_id: UUID) -> Optional[Document]:
    """Get document by ID."""
    return db.query(Document).filter(Document.id == document_id).first()


def get_documents_for_property(db: Session, property_id: UUID) -> List[Document]:
    """Get all documents for a property."""
    return db.query(Document).filter(Document.property_id == property_id).all()

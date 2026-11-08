import os
import uuid
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, RoleEnum
from app.models.property import Property, PropertyStatusEnum
from app.models.common import Document
from app.core.deps import get_current_user, require_role
from app.trust_suite.models import TrustDocument, TrustDocumentSet, TrustAdminChecklist
from app.trust_suite.schemas import (
    TrustDocumentSetCreate,
    TrustDocumentSetResponse,
    TrustDocumentResponse,
    TrustExtractedFieldResponse,
    TrustFindingResponse,
    TrustReviewQueueResponse,
    TrustAdminChecklistItem,
    TrustAdminChecklistResponse,
    TrustAdminDecisionResponse,
    TrustScoreBreakdownResponse,
    mask_identifiers,
    mask_identifiers_in_dict,
)
from app.trust_suite.services import (
    read_pages,
    extract_trust_fields,
    run_cross_checks,
    cross_check_findings_to_schema,
    compute_score,
    queue_priority,
    validate_decision,
    revert_on_reupload,
    to_seller_view,
    DocType,
    normalize_doc_type,
    UnsupportedDocumentType,
)
from app.trust_suite.repository import (
    create_document_set,
    get_document_set,
    get_document_set_for_update,
    get_document_sets_by_property,
    get_document_sets_by_owner,
    create_trust_document,
    get_trust_documents,
    create_extracted_fields,
    get_extracted_fields,
    create_findings,
    get_findings,
    create_review_queue,
    get_review_queue,
    get_review_queue_no_lock,
    get_review_queue_for_update,
    update_review_queue_status,
    get_review_queues,
    create_checklist_items,
    get_checklist_items,
    update_checklist_item,
    create_admin_decision,
    get_admin_decisions,
    create_score_breakdown,
    get_score_breakdown,
    get_property,
    get_property_for_update,
    update_property_status,
    get_property_owner_id,
    get_user,
    get_document,
    get_documents_for_property,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trust", tags=["Trust Suite"])

# Configuration
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

MAGIC_BYTES = {
    ".pdf": b"%PDF",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".png": b"\x89PNG\r\n\x1a\n",
}


def _get_upload_dir() -> Path:
    """Get upload directory, creating it lazily on first use. Reads TRUST_UPLOAD_DIR from env each call."""
    upload_dir = os.getenv("TRUST_UPLOAD_DIR", os.path.join(os.getcwd(), "private_uploads", "trust"))
    upload_path = Path(upload_dir).resolve()
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path


def _validate_extension(filename: str) -> str:
    """Validate file extension against whitelist, return normalized extension."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '{ext}' not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    return ext


def _validate_magic_bytes(file_bytes: bytes, expected_ext: str) -> None:
    """Validate file magic bytes match expected extension."""
    magic = MAGIC_BYTES.get(expected_ext)
    if magic is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No magic byte validation for extension: {expected_ext}",
        )
    if not file_bytes.startswith(magic):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File content does not match extension '{expected_ext}' (magic bytes mismatch)",
        )


def _read_file_chunks(file: UploadFile, max_size: int) -> bytes:
    """Read file in chunks, stopping if size exceeds max_size."""
    chunks = []
    total = 0
    while True:
        chunk = file.file.read(8192)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum allowed ({max_size} bytes)",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _resolve_safe_path(stored_path: str) -> Path:
    """Resolve stored path and verify it's inside TRUST_UPLOAD_DIR."""
    upload_dir = _get_upload_dir()
    file_path = Path(stored_path).resolve()
    try:
        file_path.relative_to(upload_dir)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path (path traversal attempt)",
        )
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return file_path


def _process_uploaded_file(file: UploadFile, doc_id: UUID) -> tuple[str, bytes]:
    """Validate and read uploaded file once, return file_path and file_bytes.
    
    Performs: extension check -> magic bytes check -> chunked read with size limit.
    File is read ONCE and written ONCE by the caller.
    """
    ext = _validate_extension(file.filename or "")
    file_bytes = _read_file_chunks(file, MAX_FILE_SIZE)
    _validate_magic_bytes(file_bytes, ext)
    
    upload_dir = _get_upload_dir()
    safe_filename = f"{doc_id}{ext}"
    file_path = upload_dir / safe_filename
    
    return str(file_path), file_bytes


DEFAULT_CHECKLIST_ITEMS = [
    {"item_key": "owner_name_matched", "label": "Owner name matched across documents"},
    {"item_key": "survey_number_matched", "label": "Survey number matched across documents"},
    {"item_key": "area_matched", "label": "Area measurements matched across documents"},
    {"item_key": "ec_checked", "label": "Encumbrance Certificate verified manually"},
    {"item_key": "registration_details_checked", "label": "Registration details verified manually"},
    {"item_key": "dues_checked", "label": "Property dues/taxes checked manually"},
    {"item_key": "identity_verified", "label": "Seller identity verified (with consent)"},
]


# ============================================================
# SELLER/AGENT ENDPOINTS
# ============================================================

@router.post("/sets", response_model=TrustDocumentSetResponse, status_code=status.HTTP_201_CREATED)
async def create_trust_set(
    property_id: UUID = Form(...),
    files: List[UploadFile] = File(...),
    doc_types: List[str] = Form(...),  # Must match files length
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload documents for a property (seller/agent must own the property).
    Types: sale_deed, ec, khata, rtc, tax_receipt
    """
    # Verify property ownership (read-only, no lock)
    prop = get_property(db, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if prop.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only upload documents for your own properties")

    if len(files) != len(doc_types):
        raise HTTPException(status_code=400, detail="Number of files must match number of doc_types")

    # Parse doc types
    parsed_doc_types = []
    for dt in doc_types:
        try:
            parsed_doc_types.append(normalize_doc_type(dt))
        except UnsupportedDocumentType as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Create document set
    doc_set = create_document_set(db, property_id, current_user.id)

    all_extracted_fields = []
    all_warnings = []
    written_file_paths: List[str] = []

    try:
        # Process each file: validate, read once, write once
        for file, doc_type in zip(files, parsed_doc_types):
            doc_id = uuid.uuid4()
            file_path, file_bytes = _process_uploaded_file(file, doc_id)
            
            # Write file once
            Path(file_path).write_bytes(file_bytes)
            written_file_paths.append(file_path)

            # Read pages from the already-read bytes
            pages = read_pages(file_bytes, file.filename)
            page_count = len(pages)

            # Extract fields
            extracted_fields = extract_trust_fields(
                [{"page": p.page, "text": p.text, "method": p.method, "warnings": p.warnings} for p in pages],
                doc_type_hint=doc_type.value,
            )

            # Convert to dict for cross-checks
            extracted_dicts = [
                {
                    "field_name": f.field_name,
                    "raw_value": f.raw_value,
                    "normalized_value": f.normalized_value,
                    "page_number": f.page_number,
                    "extraction_method": f.extraction_method,
                    "document_id": str(doc_id),
                    "document_type": doc_type.value,
                }
                for f in extracted_fields
            ]

            warnings = []
            for p in pages:
                warnings.extend(p.warnings)

            all_extracted_fields.extend(extracted_dicts)
            all_warnings.extend(warnings)

            # Create trust document record
            trust_doc = create_trust_document(db, doc_set.id, doc_id, doc_type.value, page_count, file_path)

            # Store extracted fields - use trust_doc.id (PK), not doc_id (document_id)
            for field_dict in extracted_dicts:
                field_dict["document_id"] = trust_doc.id
            create_extracted_fields(db, trust_doc.id, extracted_dicts)

        # Run cross-document checks
        cross_findings = run_cross_checks(all_extracted_fields)
        finding_schemas = cross_check_findings_to_schema(cross_findings)

        # Store findings
        create_findings(db, doc_set.id, [f.model_dump() for f in finding_schemas])

        # Determine missing documents
        doc_types_present = set(dt.value for dt in parsed_doc_types)
        required_types = {"sale_deed", "ec"}
        missing_documents = [rt for rt in required_types if rt not in doc_types_present]

        # Determine priority and create review queue
        priority_result = queue_priority(finding_schemas, missing_documents)
        review_queue = create_review_queue(db, doc_set.id, property_id, priority_result.priority, "flagged_for_review")

        # Create default checklist items
        checklist_data = [
            {**item, "review_queue_id": str(review_queue.id)}
            for item in DEFAULT_CHECKLIST_ITEMS
        ]
        create_checklist_items(db, review_queue.id, checklist_data)

        # If property was approved, revert to pending (use get_property_for_update for write)
        if prop.status == PropertyStatusEnum.approved:
            prop_for_update = get_property_for_update(db, property_id)
            if prop_for_update:
                new_status = revert_on_reupload(prop_for_update.status.value)
                update_property_status(db, property_id, PropertyStatusEnum(new_status))

        db.commit()

        # Include review_status from the review queue in the response
        response = TrustDocumentSetResponse.model_validate(doc_set)
        response.review_status = review_queue.status
        return response

    except Exception:
        # Clean up any files written during this request
        for fpath in written_file_paths:
            try:
                Path(fpath).unlink(missing_ok=True)
            except Exception:
                pass  # Best effort cleanup
        db.rollback()
        raise


@router.get("/sets/mine", response_model=List[TrustDocumentSetResponse])
def get_my_trust_sets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all trust document sets for properties owned by the current user."""
    doc_sets = get_document_sets_by_owner(db, current_user.id)
    results = []
    for ds in doc_sets:
        response = TrustDocumentSetResponse.model_validate(ds)
        # Get review queue status
        queue = get_review_queue(db, ds.id)
        if queue:
            response.review_status = queue.status
        results.append(response)
    return results


@router.get("/sets/{doc_set_id}", response_model=TrustDocumentSetResponse)
def get_trust_set(
    doc_set_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a trust document set (seller view only for owner)."""
    doc_set = get_document_set(db, doc_set_id)
    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")

    # Check ownership (read-only, no lock)
    prop = get_property(db, doc_set.property_id)
    if prop.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only view your own document sets")

    response = TrustDocumentSetResponse.model_validate(doc_set)
    # Get review queue status
    queue = get_review_queue(db, doc_set_id)
    if queue:
        response.review_status = queue.status
    return response


@router.get("/sets/{doc_set_id}/seller-view")
def get_seller_view(
    doc_set_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get seller-facing view of a trust document set."""
    doc_set = get_document_set(db, doc_set_id)
    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")

    # Check ownership (read-only, no lock)
    prop = get_property(db, doc_set.property_id)
    if prop.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only view your own document sets")

    review_queue = get_review_queue(db, doc_set_id)
    if not review_queue:
        raise HTTPException(status_code=404, detail="Review queue not found")

    findings = get_findings(db, doc_set_id)
    checklist_items = get_checklist_items(db, review_queue.id)
    admin_decisions = get_admin_decisions(db, review_queue.id)

    # Get latest decision
    latest_decision = None
    if admin_decisions:
        latest = admin_decisions[-1]
        latest_decision = {
            "action": latest.action,
            "reason": latest.reason,
            "notes": latest.notes,
        }

    # Determine missing documents
    doc_types_present = set(doc.doc_type for doc in get_trust_documents(db, doc_set_id))
    required_types = {"sale_deed", "ec"}
    missing_documents = [rt for rt in required_types if rt not in doc_types_present]

    set_data = {
        "review_status": review_queue.status,
    }

    seller_output = to_seller_view(
        set_data=set_data,
        findings=findings,
        missing_documents=missing_documents,
        decision=latest_decision,
    )

    return {
        "review_status": seller_output.review_status,
        "findings": [
            {
                "category": f.category,
                "status": f.status,
                "document_type": f.document_type,
                "seller_message": f.seller_message,
            }
            for f in seller_output.findings
        ],
        "missing_documents": seller_output.missing_documents,
        "decision": {
            "action": seller_output.decision.action,
            "reason": seller_output.decision.reason,
            "summary": seller_output.decision.summary,
        } if seller_output.decision else None,
    }


# ============================================================
# ADMIN ENDPOINTS
# ============================================================

@router.get("/admin/queue", response_model=List[TrustReviewQueueResponse])
def get_admin_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Get admin review queue - flagged first, then clean."""
    queues = get_review_queues(db, flagged_first=True)
    return [TrustReviewQueueResponse.model_validate(q) for q in queues]


@router.get("/admin/review/{queue_id}")
def get_admin_review(
    queue_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Get full review details for admin - everything needed for review."""
    queue = get_review_queue_no_lock(db, queue_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Review queue not found")

    doc_set = get_document_set(db, queue.document_set_id)
    if not doc_set:
        raise HTTPException(status_code=404, detail="Document set not found")

    documents = get_trust_documents(db, doc_set.id)
    findings = get_findings(db, doc_set.id)
    checklist_items = get_checklist_items(db, queue_id)
    admin_decisions = get_admin_decisions(db, queue_id)

    # Get extracted fields for all documents
    extracted_fields = {}
    for doc in documents:
        fields = get_extracted_fields(db, doc.id)
        extracted_fields[str(doc.id)] = [TrustExtractedFieldResponse.model_validate(f).model_dump() for f in fields]

    return {
        "queue": TrustReviewQueueResponse.model_validate(queue),
        "document_set": TrustDocumentSetResponse.model_validate(doc_set),
        "documents": [TrustDocumentResponse.model_validate(d).model_dump() for d in documents],
        "extracted_fields": extracted_fields,
        "findings": [TrustFindingResponse.model_validate(f).model_dump() for f in findings],
        "checklist": [TrustAdminChecklistResponse.model_validate(c).model_dump() for c in checklist_items],
        "decisions": [TrustAdminDecisionResponse.model_validate(d).model_dump() for d in admin_decisions],
    }


@router.put("/admin/review/{queue_id}/checklist", response_model=List[TrustAdminChecklistResponse])
def update_admin_checklist(
    queue_id: UUID,
    items: List[TrustAdminChecklistItem],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Save checklist items (applicable, verified, note)."""
    # Use locking variant for write operation
    queue = get_review_queue_for_update(db, queue_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Review queue not found")

    if queue.status not in ("flagged_for_review", "in_review"):
        raise HTTPException(status_code=400, detail="Checklist can only be updated when status is flagged_for_review or in_review")

    # Update status to in_review if not already
    if queue.status == "flagged_for_review":
        update_review_queue_status(db, queue_id, "in_review")

    # Update each checklist item
    updated_items = []
    for item_data in items:
        # Find existing item
        existing = db.query(TrustAdminChecklist).filter(
            TrustAdminChecklist.review_queue_id == queue_id,
            TrustAdminChecklist.item_key == item_data.item_key
        ).first()

        if existing:
            updated = update_checklist_item(
                db,
                existing.id,
                is_applicable=item_data.is_applicable,
                verified=item_data.verified,
                note=item_data.note,
                evidence_doc_ids=item_data.evidence_doc_ids,
            )
            if updated:
                updated_items.append(updated)

    # Record checklist_update decision
    checklist_snapshot = {
        "items": [item.model_dump() for item in items],
        "updated_by": str(current_user.id),
        "updated_at": datetime.utcnow().isoformat(),
    }
    create_admin_decision(
        db,
        queue_id,
        current_user.id,
        "checklist_update",
        queue.status,
        queue.status,
        checklist_snapshot,
    )

    db.commit()

    return [TrustAdminChecklistResponse.model_validate(i) for i in updated_items]


@router.post("/admin/review/{queue_id}/decision", response_model=TrustAdminDecisionResponse)
def make_admin_decision(
    queue_id: UUID,
    action: str = Form(...),  # "approve" or "reject"
    reason: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """
    Approve or reject a document set.
    In ONE transaction: row lock, validate, update property status, insert audit row, compute score.
    Lock order: queue row first, then property row.
    """
    # Get queue with row lock (first in lock order)
    queue = get_review_queue_for_update(db, queue_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Review queue not found")

    if queue.status != "in_review":
        raise HTTPException(status_code=400, detail="Decision only allowed when status is 'in_review'")

    # Get property with row lock (second in lock order)
    prop = get_property_for_update(db, queue.property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    listing_owner_id = str(prop.agent_id)
    if str(current_user.id) == listing_owner_id:
        raise HTTPException(status_code=403, detail="Approver cannot be the listing owner")

    # Get checklist items and findings
    checklist_items = get_checklist_items(db, queue_id)
    findings = get_findings(db, queue.document_set_id)

    # Convert checklist items to schema format
    checklist_schema = [
        TrustAdminChecklistItem(
            item_key=item.item_key,
            label=item.label,
            is_applicable=item.is_applicable,
            verified=item.verified,
            note=item.note,
            evidence_doc_ids=item.evidence_doc_ids,
        )
        for item in checklist_items
    ]

    # Validate decision
    decision_result = validate_decision(
        current_status=queue.status,
        action=action,
        checklist_items=checklist_schema,
        findings=findings,
        reason=reason,
        notes=notes,
        approver_id=str(current_user.id),
        listing_owner_id=listing_owner_id,
    )

    if not decision_result.ok:
        raise HTTPException(status_code=400, detail="; ".join(decision_result.errors))

    # Update property status
    new_property_status = PropertyStatusEnum.approved if action == "approve" else PropertyStatusEnum.rejected
    update_property_status(db, queue.property_id, new_property_status)

    # Update queue status
    update_review_queue_status(db, queue_id, decision_result.new_status)

    # Create audit decision record
    checklist_snapshot = {
        "items": [item.model_dump() for item in checklist_schema],
    }
    decision_record = create_admin_decision(
        db,
        queue_id,
        current_user.id,
        action,
        queue.status,
        decision_result.new_status,
        checklist_snapshot,
        reason=reason,
        notes=notes,
    )

    # Compute and store score if approved
    if action == "approve":
        score = compute_score(findings, checklist_schema)
        create_score_breakdown(
            db,
            queue_id,
            score.automated_checks_total,
            score.automated_checks_passed,
            score.admin_checks_total,
            score.admin_checks_passed,
            score.score_percentage,
            score.breakdown_json,
        )

    db.commit()

    return TrustAdminDecisionResponse.model_validate(decision_record)


# ============================================================
# DOCUMENT DOWNLOAD
# ============================================================

@router.get("/documents/{document_id}/download")
def download_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download a trust document (owner or admin only)."""
    # Find the trust document
    trust_doc = db.query(TrustDocument).filter(TrustDocument.document_id == document_id).first()
    if not trust_doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc_set = get_document_set(db, trust_doc.document_set_id)
    prop = get_property(db, doc_set.property_id)

    # Check permissions: property owner or admin
    is_owner = prop.agent_id == current_user.id
    is_admin = current_user.role == RoleEnum.admin

    if not is_owner and not is_admin:
        raise HTTPException(status_code=403, detail="You don't have permission to download this document")

    # Resolve and validate file path (path traversal protection)
    file_path = _resolve_safe_path(trust_doc.file_url)

    # Return FileResponse with security headers
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{file_path.name}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


# ============================================================
# BUYER ENDPOINT (public, unchanged)
# ============================================================

@router.get("/properties/{property_id}/verification")
def get_property_verification(
    property_id: UUID,
    db: Session = Depends(get_db),
):
    """Get verification summary for an APPROVED listing (buyer view)."""
    prop = get_property(db, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    if prop.status != PropertyStatusEnum.approved:
        raise HTTPException(status_code=404, detail="Verification only available for approved listings")

    # Find document sets, newest first (re-uploads create newer sets)
    doc_sets = get_document_sets_by_property(db, property_id)
    if not doc_sets:
        raise HTTPException(status_code=404, detail="No approved verification found for this property")

    doc_sets_sorted = sorted(doc_sets, key=lambda ds: ds.created_at, reverse=True)

    # Only the LATEST set matters: if it's not approved, the listing is not verified
    latest_set = doc_sets_sorted[0]
    queue = get_review_queue(db, latest_set.id)
    if not queue or queue.status != "approved":
        raise HTTPException(status_code=404, detail="No approved verification found for this property")

    score_breakdown = get_score_breakdown(db, queue.id)

    if not score_breakdown:
        raise HTTPException(status_code=404, detail="Score breakdown not found")

    # Return buyer-facing verification summary
    return {
        "property_id": str(property_id),
        "verification_status": "approved",
        "display_text": f"{score_breakdown.admin_checks_passed} of {score_breakdown.admin_checks_total} verified",
        "automated_checks": {
            "total": score_breakdown.automated_checks_total,
            "passed": score_breakdown.automated_checks_passed,
            "percentage": score_breakdown.score_percentage.get("automated", 0),
        },
        "admin_checks": {
            "total": score_breakdown.admin_checks_total,
            "passed": score_breakdown.admin_checks_passed,
            "percentage": score_breakdown.score_percentage.get("admin", 0),
        },
        "disclaimer": score_breakdown.disclaimer,
    }
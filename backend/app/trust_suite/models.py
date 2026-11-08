import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, ForeignKey, JSON, Text, CheckConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from app.database import Base


class TrustDocumentSet(Base):
    __tablename__ = "trust_document_sets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    documents = relationship("TrustDocument", back_populates="document_set", cascade="all, delete-orphan")
    findings = relationship("TrustFinding", back_populates="document_set", cascade="all, delete-orphan")
    review_queue = relationship("TrustReviewQueue", back_populates="document_set", uselist=False, cascade="all, delete-orphan")


class TrustDocument(Base):
    __tablename__ = "trust_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_set_id = Column(UUID(as_uuid=True), ForeignKey("trust_document_sets.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    doc_type = Column(String(64), nullable=False)
    page_count = Column(Integer, default=0)
    file_url = Column(String(512))
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    document_set = relationship("TrustDocumentSet", back_populates="documents")
    extracted_fields = relationship("TrustExtractedField", back_populates="document", cascade="all, delete-orphan")


class TrustExtractedField(Base):
    __tablename__ = "trust_extracted_fields"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("trust_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    field_name = Column(String(64), nullable=False)
    raw_value = Column(Text)
    normalized_value = Column(Text)
    page_number = Column(Integer, default=1)
    extracted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    extraction_method = Column(String(16))

    document = relationship("TrustDocument", back_populates="extracted_fields")


class TrustFinding(Base):
    __tablename__ = "trust_findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_set_id = Column(UUID(as_uuid=True), ForeignKey("trust_document_sets.id", ondelete="CASCADE"), nullable=False, index=True)
    check_id = Column(String(64), nullable=False)
    category = Column(String(32), nullable=False)
    severity = Column(String(16), nullable=False)
    status = Column(String(32), nullable=False)
    field_name = Column(String(64))
    evidence_json = Column(JSONB)
    why_raised = Column(Text)
    next_step = Column(Text)
    seller_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    document_set = relationship("TrustDocumentSet", back_populates="findings")

    __table_args__ = (
        CheckConstraint(
            "category IN ('consistency', 'integrity', 'completeness')",
            name="ck_trust_findings_category"
        ),
        CheckConstraint(
            "severity IN ('info', 'warning', 'critical')",
            name="ck_trust_findings_severity"
        ),
        CheckConstraint(
            "status IN ('matched', 'mismatch', 'needs_manual_verification')",
            name="ck_trust_findings_status"
        ),
        Index("ix_trust_findings_docset_category", "document_set_id", "category"),
    )


class TrustReviewQueue(Base):
    __tablename__ = "trust_review_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_set_id = Column(UUID(as_uuid=True), ForeignKey("trust_document_sets.id", ondelete="CASCADE"), nullable=False, unique=True)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="flagged_for_review")
    priority = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    document_set = relationship("TrustDocumentSet", back_populates="review_queue")
    checklist = relationship("TrustAdminChecklist", back_populates="review_queue", cascade="all, delete-orphan")
    decisions = relationship("TrustAdminDecision", back_populates="review_queue", cascade="all, delete-orphan")
    score_breakdown = relationship("TrustScoreBreakdown", back_populates="review_queue", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status IN ('flagged_for_review', 'in_review', 'approved', 'rejected')",
            name="ck_trust_review_queue_status"
        ),
        Index("ix_trust_review_queue_property_status", "property_id", "status"),
    )


class TrustAdminChecklist(Base):
    __tablename__ = "trust_admin_checklist"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_queue_id = Column(UUID(as_uuid=True), ForeignKey("trust_review_queue.id", ondelete="CASCADE"), nullable=False, index=True)
    item_key = Column(String(64), nullable=False)
    label = Column(String(128), nullable=False)
    is_applicable = Column(Boolean, default=True, nullable=False)
    verified = Column(Boolean, default=False, nullable=False)
    note = Column(Text)
    evidence_doc_ids = Column(ARRAY(UUID(as_uuid=True)))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    review_queue = relationship("TrustReviewQueue", back_populates="checklist")

    __table_args__ = (
        CheckConstraint(
            "item_key IN ('owner_name_matched', 'survey_number_matched', 'area_matched', "
            "'ec_checked', 'registration_details_checked', 'dues_checked', 'identity_verified')",
            name="ck_trust_admin_checklist_item_key"
        ),
    )


class TrustAdminDecision(Base):
    __tablename__ = "trust_admin_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_queue_id = Column(UUID(as_uuid=True), ForeignKey("trust_review_queue.id", ondelete="CASCADE"), nullable=False, index=True)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(32), nullable=False)
    previous_status = Column(String(32))
    new_status = Column(String(32))
    checklist_snapshot_json = Column(JSONB)
    reason = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    review_queue = relationship("TrustReviewQueue", back_populates="decisions")

    __table_args__ = (
        CheckConstraint(
            "action IN ('started_review', 'checklist_update', 'rejected', 'approved')",
            name="ck_trust_admin_decisions_action"
        ),
    )


class TrustScoreBreakdown(Base):
    __tablename__ = "trust_score_breakdown"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_queue_id = Column(UUID(as_uuid=True), ForeignKey("trust_review_queue.id", ondelete="CASCADE"), nullable=False, unique=True)
    automated_checks_total = Column(Integer, default=0)
    automated_checks_passed = Column(Integer, default=0)
    admin_checks_total = Column(Integer, default=0)
    admin_checks_passed = Column(Integer, default=0)
    score_percentage = Column(JSONB)
    breakdown_json = Column(JSONB)
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    review_queue = relationship("TrustReviewQueue", back_populates="score_breakdown")

    __table_args__ = (
        CheckConstraint(
            "automated_checks_total >= 0 AND automated_checks_passed >= 0 AND "
            "admin_checks_total >= 0 AND admin_checks_passed >= 0",
            name="ck_trust_score_breakdown_nonnegative"
        ),
    )

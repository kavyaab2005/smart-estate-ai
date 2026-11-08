"""add trust_suite tables

Revision ID: a1b2c3d4e5f6
Revises: 2c3fcf4a7c87
Create Date: 2026-10-20 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '9a54f82ad34a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'trust_document_sets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_trust_document_sets_property_id', 'trust_document_sets', ['property_id'])

    op.create_table(
        'trust_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_set_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('doc_type', sa.String(64), nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('file_url', sa.String(512), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['document_set_id'], ['trust_document_sets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', name='uq_trust_documents_document_id'),
    )
    op.create_index('ix_trust_documents_document_set_id', 'trust_documents', ['document_set_id'])

    op.create_table(
        'trust_extracted_fields',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('field_name', sa.String(64), nullable=False),
        sa.Column('raw_value', sa.Text(), nullable=True),
        sa.Column('normalized_value', sa.Text(), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('extracted_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('extraction_method', sa.String(16), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['trust_documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_trust_extracted_fields_document_id', 'trust_extracted_fields', ['document_id'])

    op.create_table(
        'trust_findings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_set_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('check_id', sa.String(64), nullable=False),
        sa.Column('category', sa.String(32), nullable=False),
        sa.Column('severity', sa.String(16), nullable=False),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('field_name', sa.String(64), nullable=True),
        sa.Column('evidence_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('why_raised', sa.Text(), nullable=True),
        sa.Column('next_step', sa.Text(), nullable=True),
        sa.Column('seller_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['document_set_id'], ['trust_document_sets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_trust_findings_docset_category', 'trust_findings', ['document_set_id', 'category'])
    op.create_check_constraint(
        'ck_trust_findings_category',
        'trust_findings',
        "category IN ('consistency', 'integrity', 'completeness')"
    )
    op.create_check_constraint(
        'ck_trust_findings_severity',
        'trust_findings',
        "severity IN ('info', 'warning', 'critical')"
    )
    op.create_check_constraint(
        'ck_trust_findings_status',
        'trust_findings',
        "status IN ('matched', 'mismatch', 'needs_manual_verification')"
    )

    op.create_table(
        'trust_review_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_set_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='flagged_for_review'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['document_set_id'], ['trust_document_sets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_set_id', name='uq_trust_review_queue_document_set_id'),
    )
    op.create_index('ix_trust_review_queue_property_status', 'trust_review_queue', ['property_id', 'status'])
    op.create_check_constraint(
        'ck_trust_review_queue_status',
        'trust_review_queue',
        "status IN ('flagged_for_review', 'in_review', 'approved', 'rejected')"
    )

    op.create_table(
        'trust_admin_checklist',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('review_queue_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('item_key', sa.String(64), nullable=False),
        sa.Column('label', sa.String(128), nullable=False),
        sa.Column('is_applicable', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('evidence_doc_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['review_queue_id'], ['trust_review_queue.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_trust_admin_checklist_review_queue_id', 'trust_admin_checklist', ['review_queue_id'])
    op.create_check_constraint(
        'ck_trust_admin_checklist_item_key',
        'trust_admin_checklist',
        "item_key IN ('owner_name_matched', 'survey_number_matched', 'area_matched', "
        "'ec_checked', 'registration_details_checked', 'dues_checked', 'identity_verified')"
    )

    op.create_table(
        'trust_admin_decisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('review_queue_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('admin_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(32), nullable=False),
        sa.Column('previous_status', sa.String(32), nullable=True),
        sa.Column('new_status', sa.String(32), nullable=True),
        sa.Column('checklist_snapshot_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['review_queue_id'], ['trust_review_queue.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['admin_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_trust_admin_decisions_review_queue_id', 'trust_admin_decisions', ['review_queue_id'])
    op.create_check_constraint(
        'ck_trust_admin_decisions_action',
        'trust_admin_decisions',
        "action IN ('started_review', 'checklist_update', 'rejected', 'approved')"
    )

    op.create_table(
        'trust_score_breakdown',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('review_queue_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('automated_checks_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('automated_checks_passed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('admin_checks_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('admin_checks_passed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('score_percentage', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('breakdown_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('computed_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['review_queue_id'], ['trust_review_queue.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('review_queue_id', name='uq_trust_score_breakdown_review_queue_id'),
    )
    op.create_check_constraint(
        'ck_trust_score_breakdown_nonnegative',
        'trust_score_breakdown',
        "automated_checks_total >= 0 AND automated_checks_passed >= 0 AND "
        "admin_checks_total >= 0 AND admin_checks_passed >= 0"
    )


def downgrade() -> None:
    op.drop_table('trust_score_breakdown')
    op.drop_table('trust_admin_decisions')
    op.drop_table('trust_admin_checklist')
    op.drop_table('trust_review_queue')
    op.drop_table('trust_findings')
    op.drop_table('trust_extracted_fields')
    op.drop_table('trust_documents')
    op.drop_table('trust_document_sets')

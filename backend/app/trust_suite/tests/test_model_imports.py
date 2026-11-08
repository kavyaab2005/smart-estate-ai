"""
Test that imports trust_suite models and verifies metadata
without connecting to a database.
"""
import os
import sys

# Set a valid DATABASE_URL before any imports
os.environ['DATABASE_URL'] = 'postgresql://user:pass@localhost/testdb'

# Now import the models
import app.models.user  # noqa: F401
import app.models.property  # noqa: F401
import app.models.common  # noqa: F401
from app.trust_suite import models
from sqlalchemy import CheckConstraint, UniqueConstraint

def test_model_imports_and_metadata():
    """Test that models can be imported and have correct metadata."""
    
    # Get all model classes from the module
    model_names = [
        'TrustDocumentSet',
        'TrustDocument',
        'TrustExtractedField',
        'TrustFinding',
        'TrustReviewQueue',
        'TrustAdminChecklist',
        'TrustAdminDecision',
        'TrustScoreBreakdown',
    ]
    
    model_classes = []
    for name in model_names:
        m = getattr(models, name, None)
        assert m is not None, f"Model {name} not found in module"
        model_classes.append(m)
        print(f"  Found: {name}")
    
    print("\nModel classes found:", [m.__name__ for m in model_classes])
    
    # Verify each has a __tablename__
    for m in model_classes:
        assert hasattr(m, '__tablename__'), f"{m.__name__} missing __tablename__"
        assert m.__tablename__.startswith('trust_'), f"{m.__name__} table name doesn't start with trust_: {m.__tablename__}"
        print(f"  {m.__name__} -> {m.__tablename__}")
    
    print("\nAll 8 trust_ tables present:")
    table_names = [m.__tablename__ for m in model_classes]
    expected = [
        'trust_document_sets',
        'trust_documents',
        'trust_extracted_fields',
        'trust_findings',
        'trust_review_queue',
        'trust_admin_checklist',
        'trust_admin_decisions',
        'trust_score_breakdown',
    ]
    for t in expected:
        assert t in table_names, f"Missing table: {t}"
    print("  " + "\n  ".join(sorted(table_names)))
    
    # Inspect constraints on model __table_args__
    print("\nVerifying CHECK constraints...")
    
    # Check TrustFinding CHECK constraints
    finding = models.TrustFinding
    check_constraints = [c for c in finding.__table_args__ if isinstance(c, CheckConstraint)]
    print(f"  TrustFinding: {[c.name for c in check_constraints]}")
    assert any(c.name == 'ck_trust_findings_category' for c in check_constraints)
    assert any(c.name == 'ck_trust_findings_severity' for c in check_constraints)
    assert any(c.name == 'ck_trust_findings_status' for c in check_constraints)
    
    # Check TrustReviewQueue
    rq = models.TrustReviewQueue
    rq_constraints = [c for c in rq.__table_args__ if isinstance(c, CheckConstraint)]
    print(f"  TrustReviewQueue: {[c.name for c in rq_constraints]}")
    assert any(c.name == 'ck_trust_review_queue_status' for c in rq_constraints)
    
    # Check TrustAdminChecklist
    ac = models.TrustAdminChecklist
    ac_constraints = [c for c in ac.__table_args__ if isinstance(c, CheckConstraint)]
    print(f"  TrustAdminChecklist: {[c.name for c in ac_constraints]}")
    assert any(c.name == 'ck_trust_admin_checklist_item_key' for c in ac_constraints)
    
    # Check TrustAdminDecision
    ad = models.TrustAdminDecision
    ad_constraints = [c for c in ad.__table_args__ if isinstance(c, CheckConstraint)]
    print(f"  TrustAdminDecision: {[c.name for c in ad_constraints]}")
    assert any(c.name == 'ck_trust_admin_decisions_action' for c in ad_constraints)
    
    # Check TrustScoreBreakdown
    sb = models.TrustScoreBreakdown
    sb_constraints = [c for c in sb.__table_args__ if isinstance(c, CheckConstraint)]
    print(f"  TrustScoreBreakdown: {[c.name for c in sb_constraints]}")
    assert any(c.name == 'ck_trust_score_breakdown_nonnegative' for c in sb_constraints)
    
    # Verify foreign keys are defined
    print("\nVerifying foreign keys...")
    for m in model_classes:
        fks = list(m.__table__.foreign_keys)
        if fks:
            print(f"  {m.__name__}: {len(fks)} FK(s)")
            for fk in fks:
                print(f"    -> {fk.column.table.name}.{fk.column.name}")
        else:
            print(f"  {m.__name__}: 0 FK(s)")
    
    # Verify indexes
    print("\nVerifying indexes...")
    for m in model_classes:
        indexes = list(m.__table__.indexes)
        if indexes:
            print(f"  {m.__name__}: {len(indexes)} index(es)")
            for idx in indexes:
                print(f"    -> {idx.name}: {idx.columns.keys()}")
    
    # Verify unique constraints
    print("\nVerifying unique constraints...")
    for m in model_classes:
        uqs = [c for c in m.__table__.constraints if isinstance(c, UniqueConstraint)]
        if uqs:
            for uq in uqs:
                print(f"  {m.__name__}: {uq.name} -> {[c.name for c in uq.columns]}")
    
    print("\n✓ All model verification passed!")
    return True


if __name__ == "__main__":
    test_model_imports_and_metadata()
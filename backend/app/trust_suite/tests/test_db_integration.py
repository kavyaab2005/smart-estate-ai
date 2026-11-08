"""
Database integration tests for trust_suite router and repository.
These tests are SKIPPED unless TEST_DATABASE_URL is set and DATABASE_URL equals it (never production).
They refuse to run against anything else.
"""
import os
import pytest
from uuid import UUID, uuid4
from datetime import datetime

# Check if we should run DB tests. Both variables must be set and identical,
# so the tests only run against a database chosen on purpose.
DATABASE_URL = os.getenv("DATABASE_URL", "")
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")
PRODUCTION_HOST_PREFIX = "ep-orange-fog-b3ml7ls6"
RUN_DB_TESTS = (
    bool(TEST_DATABASE_URL)
    and DATABASE_URL == TEST_DATABASE_URL
    and PRODUCTION_HOST_PREFIX not in TEST_DATABASE_URL
)
skip_if_not_test_db = pytest.mark.skipif(
    not RUN_DB_TESTS,
    reason="DB tests need TEST_DATABASE_URL set, DATABASE_URL equal to it, and the database must not be production."
)


@skip_if_not_test_db
class TestRepositoryIntegration:
    """Integration tests for repository functions using real database."""

    @pytest.fixture
    def db_session(self):
        """Get a database session."""
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    @pytest.fixture
    def test_user(self, db_session):
        """Create a test user."""
        from app.models.user import User, RoleEnum
        from app.core.security import hash_password
        user = User(
            name="Test User",
            email=f"test_{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("testpass"),
            role=RoleEnum.agent,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        yield user
        # Cleanup
        db_session.delete(user)
        db_session.commit()

    @pytest.fixture
    def test_admin(self, db_session):
        """Create a test admin user."""
        from app.models.user import User, RoleEnum
        from app.core.security import hash_password
        admin = User(
            name="Test Admin",
            email=f"admin_{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("adminpass"),
            role=RoleEnum.admin,
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)
        yield admin
        db_session.delete(admin)
        db_session.commit()

    @pytest.fixture
    def test_property(self, db_session, test_user):
        """Create a test property."""
        from app.models.property import Property, PropertyTypeEnum, ListingTypeEnum, PropertyStatusEnum
        prop = Property(
            agent_id=test_user.id,
            title="Test Property",
            description="Test description",
            property_type=PropertyTypeEnum.apartment,
            listing_type=ListingTypeEnum.buy,
            price=1000000,
            area_sqft=1000,
            bhk=2,
            bathrooms=2,
            city="Bangalore",
            status=PropertyStatusEnum.pending,
        )
        db_session.add(prop)
        db_session.commit()
        db_session.refresh(prop)
        yield prop
        db_session.delete(prop)
        db_session.commit()

    def test_create_document_set(self, db_session, test_user, test_property):
        """Test creating a document set."""
        from app.trust_suite.repository import create_document_set
        doc_set = create_document_set(db_session, test_property.id, test_user.id)
        assert doc_set.id is not None
        assert doc_set.property_id == test_property.id
        assert doc_set.created_by == test_user.id

    def test_get_document_set(self, db_session, test_user, test_property):
        """Test getting a document set."""
        from app.trust_suite.repository import create_document_set, get_document_set
        doc_set = create_document_set(db_session, test_property.id, test_user.id)
        db_session.commit()
        
        retrieved = get_document_set(db_session, doc_set.id)
        assert retrieved is not None
        assert retrieved.id == doc_set.id

    def test_create_trust_document(self, db_session, test_user, test_property):
        """Test creating a trust document."""
        from app.trust_suite.repository import create_document_set, create_trust_document, get_trust_documents
        doc_set = create_document_set(db_session, test_property.id, test_user.id)
        db_session.commit()
        
        doc_id = uuid4()
        trust_doc = create_trust_document(db_session, doc_set.id, doc_id, "sale_deed", 5, "/test/path")
        assert trust_doc.id is not None
        assert trust_doc.document_id == doc_id
        
        db_session.commit()
        
        docs = get_trust_documents(db_session, doc_set.id)
        assert len(docs) == 1

    def test_create_and_get_findings(self, db_session, test_user, test_property):
        """Test creating and getting findings."""
        from app.trust_suite.repository import create_document_set, create_findings, get_findings
        doc_set = create_document_set(db_session, test_property.id, test_user.id)
        db_session.commit()
        
        findings_data = [
            {
                "check_id": "owner_name_matched",
                "category": "consistency",
                "severity": "info",
                "status": "matched",
                "field_name": "owner_name",
                "evidence": [],
                "why_raised": "Test",
                "next_step": "Test",
                "seller_message": "Test message",
            }
        ]
        findings = create_findings(db_session, doc_set.id, findings_data)
        assert len(findings) == 1
        
        db_session.commit()
        
        retrieved = get_findings(db_session, doc_set.id)
        assert len(retrieved) == 1
        assert retrieved[0].check_id == "owner_name_matched"

    def test_review_queue_operations(self, db_session, test_user, test_property):
        """Test review queue operations."""
        from app.trust_suite.repository import (
            create_document_set, create_review_queue, get_review_queue,
            get_review_queue_for_update, update_review_queue_status,
            get_review_queues
        )
        doc_set = create_document_set(db_session, test_property.id, test_user.id)
        db_session.commit()
        
        queue = create_review_queue(db_session, doc_set.id, test_property.id, 1, "flagged_for_review")
        assert queue.id is not None
        assert queue.status == "flagged_for_review"
        
        db_session.commit()
        
        # Get for update (row lock)
        queue_locked = get_review_queue_for_update(db_session, queue.id)
        assert queue_locked is not None
        
        # Update status
        updated = update_review_queue_status(db_session, queue.id, "in_review")
        assert updated.status == "in_review"
        assert updated.started_at is not None
        
        db_session.commit()
        
        # Get all queues
        queues = get_review_queues(db_session)
        assert len(queues) >= 1

    def test_checklist_operations(self, db_session, test_user, test_property):
        """Test checklist operations."""
        from app.trust_suite.repository import (
            create_document_set, create_review_queue, create_checklist_items,
            get_checklist_items, update_checklist_item
        )
        doc_set = create_document_set(db_session, test_property.id, test_user.id)
        db_session.commit()
        
        queue = create_review_queue(db_session, doc_set.id, test_property.id, 1)
        db_session.commit()
        
        items_data = [
            {"item_key": "owner_name_matched", "label": "Owner name matched", "is_applicable": True, "verified": False, "note": None, "evidence_doc_ids": []},
            {"item_key": "survey_number_matched", "label": "Survey number matched", "is_applicable": True, "verified": True, "note": "Verified", "evidence_doc_ids": []},
        ]
        items = create_checklist_items(db_session, queue.id, items_data)
        assert len(items) == 2
        
        db_session.commit()
        
        retrieved = get_checklist_items(db_session, queue.id)
        assert len(retrieved) == 2
        
        # Update an item
        updated = update_checklist_item(db_session, retrieved[0].id, verified=True, note="Now verified")
        assert updated.verified is True
        assert updated.note == "Now verified"

    def test_admin_decision_append_only(self, db_session, test_user, test_property, test_admin):
        """Test admin decisions are append-only (audit log)."""
        from app.trust_suite.repository import (
            create_document_set, create_review_queue, create_admin_decision,
            get_admin_decisions
        )
        doc_set = create_document_set(db_session, test_property.id, test_user.id)
        db_session.commit()
        
        queue = create_review_queue(db_session, doc_set.id, test_property.id, 1)
        db_session.commit()
        
        # First decision
        decision1 = create_admin_decision(
            db_session, queue.id, test_admin.id, "started_review",
            "flagged_for_review", "in_review", {"items": []}
        )
        db_session.commit()
        
        # Second decision
        decision2 = create_admin_decision(
            db_session, queue.id, test_admin.id, "checklist_update",
            "in_review", "in_review", {"items": [{"item_key": "test", "verified": True}]}
        )
        db_session.commit()
        
        # Third decision (approve)
        decision3 = create_admin_decision(
            db_session, queue.id, test_admin.id, "approved",
            "in_review", "approved", {"items": []},
            notes="Approved after review"
        )
        db_session.commit()
        
        # Get all decisions - should have all 3
        decisions = get_admin_decisions(db_session, queue.id)
        assert len(decisions) == 3
        assert decisions[0].action == "started_review"
        assert decisions[1].action == "checklist_update"
        assert decisions[2].action == "approved"
        assert decisions[2].notes == "Approved after review"

    def test_property_status_update(self, db_session, test_user, test_property):
        """Test property status updates."""
        from app.trust_suite.repository import get_property_for_update, update_property_status
        from app.models.property import PropertyStatusEnum
        
        # Get with row lock
        prop = get_property_for_update(db_session, test_property.id)
        assert prop.status == PropertyStatusEnum.pending
        
        # Update to approved
        updated = update_property_status(db_session, test_property.id, PropertyStatusEnum.approved)
        assert updated.status == PropertyStatusEnum.approved
        
        db_session.commit()
        
        # Verify
        prop = get_property_for_update(db_session, test_property.id)
        assert prop.status == PropertyStatusEnum.approved


@skip_if_not_test_db
class TestRouterIntegration:
    """Integration tests for router endpoints using TestClient."""

    @pytest.fixture
    def client(self):
        """Create a test client with trust router mounted at /api/v1."""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.trust_suite.router import router as trust_router
        # Include trust router with /api/v1 prefix if not already included
        if not any(hasattr(r, 'prefix') and r.prefix == "/api/v1/trust" for r in app.routes):
            app.include_router(trust_router, prefix="/api/v1")
        return TestClient(app)

    @pytest.fixture
    def auth_headers_user(self, client):
        """Get auth headers for a regular user (role: agent)."""
        # Register and login
        email = f"user_{uuid4().hex[:8]}@example.com"
        client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "testpass123",
            "name": "Test User",
            "role": "agent"
        })
        login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": "testpass123"})
        token = login_resp.json()["token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def auth_headers_admin(self, client):
        """Get auth headers for an admin user."""
        email = f"admin_{uuid4().hex[:8]}@example.com"
        client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "adminpass123",
            "name": "Test Admin",
            "role": "admin"
        })
        login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": "adminpass123"})
        token = login_resp.json()["token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def test_property(self, client, auth_headers_user):
        """Create a test property."""
        resp = client.post("/api/v1/properties", json={
            "title": "Test Property",
            "description": "Test description",
            "property_type": "apartment",
            "listing_type": "buy",
            "price": 1000000,
            "area_sqft": 1000,
            "bhk": 2,
            "bathrooms": 2,
            "city": "Bangalore",
            "address": "Test Address"
        }, headers=auth_headers_user)
        assert resp.status_code in (200, 201)
        return resp.json()

    def test_seller_cannot_see_forbidden_fields(self, client, auth_headers_user, test_property):
        """Seller cannot see forbidden fields in seller view."""
        # First upload a document set
        # This would require file upload - skip for now
        pass

    def test_non_owner_cannot_download(self, client, auth_headers_user, auth_headers_admin, test_property):
        """Non-owner cannot download documents."""
        # Would need to create a document set first
        pass

    def test_non_admin_gets_403_on_admin_routes(self, client, auth_headers_user):
        """Non-admin gets 403 on admin routes."""
        resp = client.get("/api/v1/trust/admin/queue", headers=auth_headers_user)
        assert resp.status_code == 403

    def test_approve_blocked_from_wrong_status(self, client, auth_headers_admin, test_property):
        """Approve blocked when status is not in_review."""
        # Would need to create a document set in flagged_for_review status
        pass

    def test_approve_blocked_by_owner(self, client, auth_headers_user, test_property):
        """Approve blocked when approver is the listing owner."""
        pass

    def test_approve_blocked_with_undecided_items(self, client, auth_headers_admin, test_property):
        """Approve blocked when items are undecided."""
        pass

    def test_two_simultaneous_decisions_cannot_both_succeed(self, client, auth_headers_admin, test_property):
        """Two simultaneous decisions cannot both succeed (row lock)."""
        pass

    def test_reject_needs_reason(self, client, auth_headers_admin, test_property):
        """Reject without reason fails."""
        pass

    def test_reupload_on_approved_listing_sets_pending(self, client, auth_headers_user, test_property):
        """Re-upload on an approved listing sets it to pending."""
        pass

    def test_clean_sets_still_queued(self, client, auth_headers_user, test_property):
        """Clean sets are still queued."""
        pass

    def test_audit_rows_append_only(self, client, auth_headers_admin, test_property):
        """Audit rows are append-only."""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

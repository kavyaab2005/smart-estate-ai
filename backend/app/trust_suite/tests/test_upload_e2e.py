"""
End-to-end database integration tests for trust upload route.
These tests are SKIPPED unless TEST_DATABASE_URL is set and DATABASE_URL equals it (never production).
They refuse to run against anything else.
"""
import os
import pytest
from uuid import UUID, uuid4
from pathlib import Path

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
class TestUploadE2E:
    """End-to-end tests for trust document upload and download flow."""

    @pytest.fixture(autouse=True)
    def _set_upload_dir(self, tmp_path, monkeypatch):
        """Set TRUST_UPLOAD_DIR to a temp directory before router is used.
        Monkeypatch the module's internal env var read to ensure isolation."""
        upload_dir = tmp_path / "trust_uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Monkeypatch the module's os.getenv call to return our temp dir
        import app.trust_suite.router as router_module
        original_getenv = os.getenv
        def patched_getenv(key, default=None):
            if key == "TRUST_UPLOAD_DIR":
                return str(upload_dir)
            return original_getenv(key, default)
        monkeypatch.setattr(router_module.os, "getenv", patched_getenv)
        
        # Also set the env var for any other code that reads it directly
        monkeypatch.setenv("TRUST_UPLOAD_DIR", str(upload_dir))
        
        # Verify no files exist in the default location before test
        default_dir = Path.cwd() / "private_uploads" / "trust"
        if default_dir.exists():
            existing_files = list(default_dir.rglob("*"))
            if existing_files:
                pytest.fail(f"Default upload dir already has files: {existing_files}")
        
        yield
        
        # Assert no files were written to the default location
        if default_dir.exists():
            new_files = list(default_dir.rglob("*"))
            if new_files:
                pytest.fail(f"Files written to default upload dir: {new_files}")

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
    def auth_headers_agent(self, client):
        """Get auth headers for a regular agent user."""
        email = f"agent_{uuid4().hex[:8]}@example.com"
        resp = client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "testpass123",
            "name": "Test Agent",
            "role": "agent"
        })
        assert resp.status_code == 200, f"Register failed: {resp.text}"
        token = resp.json()["token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def auth_headers_other_agent(self, client):
        """Get auth headers for another agent user."""
        email = f"agent2_{uuid4().hex[:8]}@example.com"
        resp = client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "testpass123",
            "name": "Test Agent 2",
            "role": "agent"
        })
        assert resp.status_code == 200, f"Register failed: {resp.text}"
        token = resp.json()["token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def auth_headers_admin(self, client):
        """Get auth headers for an admin user."""
        email = f"admin_{uuid4().hex[:8]}@example.com"
        resp = client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "adminpass123",
            "name": "Test Admin",
            "role": "admin"
        })
        # If admin registration fails, the test will fail here
        if resp.status_code != 200:
            pytest.fail(f"Admin registration failed: {resp.status_code} {resp.text} - /register may not allow admin role")
        token = resp.json()["token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def test_property(self, client, auth_headers_agent):
        """Create a test property owned by the agent."""
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
        }, headers=auth_headers_agent)
        assert resp.status_code in (200, 201), f"Property creation failed: {resp.text}"
        return resp.json()

    def _make_pdf_with_text(self, text_content: str) -> bytes:
        """Generate a minimal valid PDF with a text stream containing the given text.
        Uses a simple PDF structure with a text object that can be extracted."""
        # Escape parentheses and backslashes for PDF string
        escaped = text_content.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        
        pdf = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td ({escaped}) Tj ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000218 00000 n 
0000000305 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
410
%%EOF"""
        return pdf.encode('latin-1')

    def _make_png_bytes(self):
        """Generate a tiny valid PNG in memory (1x1 transparent pixel)."""
        return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf6\x178\x02\x00\x00\x00\x00IEND\xaeB`\x82"

    def _make_bad_pdf_bytes(self):
        """Generate bytes that look like PDF but have wrong magic bytes."""
        return b"NOTAPDF-1.4\nfake content"

    def _make_html_bytes(self):
        """Generate HTML file bytes (disallowed extension)."""
        return b"<html><body>Bad file</body></html>"

    def test_upload_success_creates_documents_and_queue(self, client, auth_headers_agent, test_property):
        """Upload valid PDF and PNG, assert success, queue flagged_for_review, trust_documents rows exist."""
        # Create PDF with extractable text containing fake Aadhaar
        pdf_text = "Owner Name: Test Owner\nSurvey Number: 123/4\nAadhaar: 1234 5678 9012\nProperty Area: 1000 sq ft"
        pdf_bytes = self._make_pdf_with_text(pdf_text)
        png_bytes = self._make_png_bytes()

        files = [
            ("files", ("sale_deed.pdf", pdf_bytes, "application/pdf")),
            ("files", ("ec.png", png_bytes, "image/png")),
        ]
        data = {
            "property_id": test_property["id"],
            "doc_types": ["sale_deed", "ec"],
        }

        resp = client.post("/api/v1/trust/sets", files=files, data=data, headers=auth_headers_agent)
        assert resp.status_code == 201, f"Upload failed: {resp.text}"

        doc_set = resp.json()
        assert "id" in doc_set
        assert doc_set["property_id"] == test_property["id"]
        # New upload starts with review queue status "flagged_for_review" (router.py:297)
        assert doc_set["review_status"] == "flagged_for_review", f"Expected flagged_for_review but got {doc_set['review_status']}"

        # Verify trust_documents rows exist via database query
        from app.database import SessionLocal
        from app.trust_suite.models import TrustDocument, TrustReviewQueue, TrustDocumentSet
        db = SessionLocal()
        try:
            docs = db.query(TrustDocument).filter(TrustDocument.document_set_id == doc_set["id"]).all()
            assert len(docs) == 2, f"Expected 2 trust_documents, got {len(docs)}"
            doc_types = {d.doc_type for d in docs}
            assert doc_types == {"sale_deed", "ec"}, f"Expected sale_deed and ec, got {doc_types}"

            # Verify review queue exists with the actual status
            queue = db.query(TrustReviewQueue).filter(TrustReviewQueue.document_set_id == doc_set["id"]).first()
            assert queue is not None
            assert queue.status == "flagged_for_review", f"Queue status is {queue.status}, expected flagged_for_review"
        finally:
            db.close()

    def test_bad_extension_rejected(self, client, auth_headers_agent, test_property):
        """Upload .html file rejected with 400, no rows created."""
        html_bytes = self._make_html_bytes()

        files = [
            ("files", ("bad.html", html_bytes, "text/html")),
        ]
        data = {
            "property_id": test_property["id"],
            "doc_types": ["sale_deed"],
        }

        resp = client.post("/api/v1/trust/sets", files=files, data=data, headers=auth_headers_agent)
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
        assert "not allowed" in resp.json()["detail"].lower()

        # Verify no trust_documents rows created
        from app.database import SessionLocal
        from app.trust_suite.models import TrustDocument, TrustDocumentSet
        db = SessionLocal()
        try:
            docs = db.query(TrustDocument).join(TrustDocument.document_set).filter(
                TrustDocumentSet.property_id == test_property["id"]
            ).all()
            assert len(docs) == 0, "No documents should be created for bad extension"
        finally:
            db.close()

    def test_wrong_magic_bytes_rejected(self, client, auth_headers_agent, test_property):
        """Upload file with PDF extension but wrong magic bytes rejected with 400."""
        bad_pdf_bytes = self._make_bad_pdf_bytes()

        files = [
            ("files", ("fake.pdf", bad_pdf_bytes, "application/pdf")),
        ]
        data = {
            "property_id": test_property["id"],
            "doc_types": ["sale_deed"],
        }

        resp = client.post("/api/v1/trust/sets", files=files, data=data, headers=auth_headers_agent)
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
        assert "magic bytes mismatch" in resp.json()["detail"].lower()

        # Verify no trust_documents rows created
        from app.database import SessionLocal
        from app.trust_suite.models import TrustDocument, TrustDocumentSet
        db = SessionLocal()
        try:
            docs = db.query(TrustDocument).join(TrustDocument.document_set).filter(
                TrustDocumentSet.property_id == test_property["id"]
            ).all()
            assert len(docs) == 0, "No documents should be created for wrong magic bytes"
        finally:
            db.close()

    def test_download_owner_gets_file(self, client, auth_headers_agent, test_property):
        """Owner can download the uploaded file with Content-Disposition attachment."""
        pdf_text = "Owner Name: Test Owner\nSurvey Number: 123/4\nProperty Area: 1000 sq ft"
        pdf_bytes = self._make_pdf_with_text(pdf_text)

        files = [
            ("files", ("sale_deed.pdf", pdf_bytes, "application/pdf")),
        ]
        data = {
            "property_id": test_property["id"],
            "doc_types": ["sale_deed"],
        }

        # Upload
        resp = client.post("/api/v1/trust/sets", files=files, data=data, headers=auth_headers_agent)
        assert resp.status_code == 201
        doc_set = resp.json()

        # Get the document_id from the database
        from app.database import SessionLocal
        from app.trust_suite.models import TrustDocument
        db = SessionLocal()
        try:
            trust_doc = db.query(TrustDocument).filter(TrustDocument.document_set_id == doc_set["id"]).first()
            assert trust_doc is not None
            document_id = str(trust_doc.document_id)
        finally:
            db.close()

        # Download as owner
        resp = client.get(f"/api/v1/trust/documents/{document_id}/download", headers=auth_headers_agent)
        assert resp.status_code == 200
        assert resp.content == pdf_bytes
        assert "attachment" in resp.headers.get("content-disposition", "")
        cd = resp.headers.get("content-disposition", "")
        assert cd.startswith("attachment"), f"Content-Disposition does not start with attachment: {cd}"
        assert cd.endswith('.pdf"'), f"Content-Disposition does not end with .pdf\": {cd}"
        assert resp.headers.get("x-content-type-options") == "nosniff"

    def test_download_other_agent_gets_403(self, client, auth_headers_agent, auth_headers_other_agent, test_property):
        """Another agent cannot download (403)."""
        pdf_text = "Owner Name: Test Owner\nSurvey Number: 123/4\nProperty Area: 1000 sq ft"
        pdf_bytes = self._make_pdf_with_text(pdf_text)

        files = [
            ("files", ("sale_deed.pdf", pdf_bytes, "application/pdf")),
        ]
        data = {
            "property_id": test_property["id"],
            "doc_types": ["sale_deed"],
        }

        resp = client.post("/api/v1/trust/sets", files=files, data=data, headers=auth_headers_agent)
        assert resp.status_code == 201
        doc_set = resp.json()

        from app.database import SessionLocal
        from app.trust_suite.models import TrustDocument
        db = SessionLocal()
        try:
            trust_doc = db.query(TrustDocument).filter(TrustDocument.document_set_id == doc_set["id"]).first()
            document_id = str(trust_doc.document_id)
        finally:
            db.close()

        resp = client.get(f"/api/v1/trust/documents/{document_id}/download", headers=auth_headers_other_agent)
        assert resp.status_code == 403

    def test_download_admin_gets_file(self, client, auth_headers_agent, auth_headers_admin, test_property):
        """Admin can download the uploaded file."""
        pdf_text = "Owner Name: Test Owner\nSurvey Number: 123/4\nProperty Area: 1000 sq ft"
        pdf_bytes = self._make_pdf_with_text(pdf_text)

        files = [
            ("files", ("sale_deed.pdf", pdf_bytes, "application/pdf")),
        ]
        data = {
            "property_id": test_property["id"],
            "doc_types": ["sale_deed"],
        }

        resp = client.post("/api/v1/trust/sets", files=files, data=data, headers=auth_headers_agent)
        assert resp.status_code == 201
        doc_set = resp.json()

        from app.database import SessionLocal
        from app.trust_suite.models import TrustDocument
        db = SessionLocal()
        try:
            trust_doc = db.query(TrustDocument).filter(TrustDocument.document_set_id == doc_set["id"]).first()
            document_id = str(trust_doc.document_id)
        finally:
            db.close()

        resp = client.get(f"/api/v1/trust/documents/{document_id}/download", headers=auth_headers_admin)
        assert resp.status_code == 200
        assert resp.content == pdf_bytes

    def test_seller_view_no_forbidden_fields(self, client, auth_headers_agent, test_property):
        """Seller view response contains no forbidden keys/text."""
        pdf_text = "Owner Name: Test Owner\nSurvey Number: 123/4\nProperty Area: 1000 sq ft"
        pdf_bytes = self._make_pdf_with_text(pdf_text)

        files = [
            ("files", ("sale_deed.pdf", pdf_bytes, "application/pdf")),
        ]
        data = {
            "property_id": test_property["id"],
            "doc_types": ["sale_deed"],
        }

        resp = client.post("/api/v1/trust/sets", files=files, data=data, headers=auth_headers_agent)
        assert resp.status_code == 201
        doc_set = resp.json()

        # Get seller view
        resp = client.get(f"/api/v1/trust/sets/{doc_set['id']}/seller-view", headers=auth_headers_agent)
        assert resp.status_code == 200
        seller_view = resp.json()

        # Check forbidden keys are not present in the response
        forbidden_keys = ["check_id", "evidence", "threshold", "forged", "fraud"]
        response_str = str(seller_view).lower()
        for key in forbidden_keys:
            assert key not in response_str, f"Forbidden key/text '{key}' found in seller view: {seller_view}"

        # Verify expected structure
        assert "review_status" in seller_view
        assert "findings" in seller_view
        assert "missing_documents" in seller_view
        assert "decision" in seller_view

        # Each finding should only have seller-facing fields
        for finding in seller_view["findings"]:
            allowed_keys = {"category", "status", "document_type", "seller_message"}
            assert set(finding.keys()) == allowed_keys, f"Finding has unexpected keys: {finding.keys()}"

    def test_aadhaar_masked_in_stored_fields_and_response(self, client, auth_headers_agent, test_property):
        """Aadhaar-like number in document text is masked in stored extracted fields and API responses.
        Also asserts extraction produced at least one field so masking assertion is not vacuous."""
        # Create PDF with extractable text containing fake Aadhaar
        pdf_text = "Owner Name: Test Owner\nSurvey Number: 123/4\nAadhaar: 1234 5678 9012\nProperty Area: 1000 sq ft"
        pdf_bytes = self._make_pdf_with_text(pdf_text)

        files = [
            ("files", ("sale_deed.pdf", pdf_bytes, "application/pdf")),
        ]
        data = {
            "property_id": test_property["id"],
            "doc_types": ["sale_deed"],
        }

        resp = client.post("/api/v1/trust/sets", files=files, data=data, headers=auth_headers_agent)
        assert resp.status_code == 201
        doc_set = resp.json()

        # Check stored extracted fields in database
        from app.database import SessionLocal
        from app.trust_suite.models import TrustExtractedField, TrustDocument
        db = SessionLocal()
        try:
            docs = db.query(TrustDocument).filter(TrustDocument.document_set_id == doc_set["id"]).all()
            total_fields = 0
            for doc in docs:
                fields = db.query(TrustExtractedField).filter(TrustExtractedField.document_id == doc.id).all()
                total_fields += len(fields)
                for field in fields:
                    # No full 12-digit number should appear in raw_value or normalized_value
                    for val in [field.raw_value, field.normalized_value]:
                        if val:
                            # Check for 12 consecutive digits (unmasked Aadhaar)
                            import re
                            assert not re.search(r'\d{12}', val), f"Unmasked 12-digit number found in field {field.field_name}: {val}"
                            # Check for common Aadhaar patterns (4-4-4 with spaces/hyphens)
                            assert not re.search(r'\d{4}[-\s]\d{4}[-\s]\d{4}', val), f"Unmasked Aadhaar pattern found in field {field.field_name}: {val}"
            
            # Assert extraction produced at least one field (non-vacuous masking test)
            assert total_fields > 0, "No fields extracted - masking test would be vacuous"
        finally:
            db.close()

        # Also check seller view response doesn't leak Aadhaar
        resp = client.get(f"/api/v1/trust/sets/{doc_set['id']}/seller-view", headers=auth_headers_agent)
        assert resp.status_code == 200
        seller_view = resp.json()
        response_str = str(seller_view)
        import re
        assert not re.search(r'\d{12}', response_str), f"Unmasked 12-digit number found in seller view: {response_str}"
        assert not re.search(r'\d{4}[-\s]\d{4}[-\s]\d{4}', response_str), f"Unmasked Aadhaar pattern found in seller view: {response_str}"

    def test_admin_decision_before_checklist_rejected(self, client, auth_headers_agent, auth_headers_admin, test_property):
        """Admin decision on flagged_for_review queue rejected with 400; after checklist update, status becomes in_review."""
        pdf_text = "Owner Name: Test Owner\nSurvey Number: 123/4\nProperty Area: 1000 sq ft"
        pdf_bytes = self._make_pdf_with_text(pdf_text)

        files = [
            ("files", ("sale_deed.pdf", pdf_bytes, "application/pdf")),
        ]
        data = {
            "property_id": test_property["id"],
            "doc_types": ["sale_deed"],
        }

        # Upload as agent
        resp = client.post("/api/v1/trust/sets", files=files, data=data, headers=auth_headers_agent)
        assert resp.status_code == 201
        doc_set = resp.json()

        # Get queue_id from database
        from app.database import SessionLocal
        from app.trust_suite.models import TrustReviewQueue, TrustAdminDecision
        db = SessionLocal()
        try:
            queue = db.query(TrustReviewQueue).filter(TrustReviewQueue.document_set_id == doc_set["id"]).first()
            assert queue is not None
            queue_id = str(queue.id)
            assert queue.status == "flagged_for_review"
        finally:
            db.close()

        # Admin tries to POST decision (approve) BEFORE checklist update
        # Router.py:560 returns 400 "Decision only allowed when status is 'in_review'"
        resp = client.post(
            f"/api/v1/trust/admin/review/{queue_id}/decision",
            data={"action": "approve", "reason": "Test approve"},
            headers=auth_headers_admin,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
        assert "Decision only allowed when status is 'in_review'" in resp.json()["detail"]

        # Verify property status unchanged and no decision row exists
        db = SessionLocal()
        try:
            from app.models.property import Property
            prop = db.query(Property).filter(Property.id == test_property["id"]).first()
            assert prop.status.value == "pending", f"Property status changed unexpectedly: {prop.status}"

            decisions = db.query(TrustAdminDecision).filter(TrustAdminDecision.review_queue_id == queue_id).all()
            assert len(decisions) == 0, f"Decision row created prematurely: {decisions}"
        finally:
            db.close()

        # Admin updates one checklist item via checklist endpoint
        checklist_payload = [
            {
                "item_key": "owner_name_matched",
                "label": "Owner name matched across documents",
                "is_applicable": True,
                "verified": True,
                "note": "Verified by admin",
                "evidence_doc_ids": [],
            }
        ]
        resp = client.put(
            f"/api/v1/trust/admin/review/{queue_id}/checklist",
            json=checklist_payload,
            headers=auth_headers_admin,
        )
        assert resp.status_code == 200, f"Checklist update failed: {resp.text}"

        # Verify queue status is now "in_review"
        db = SessionLocal()
        try:
            queue = db.query(TrustReviewQueue).filter(TrustReviewQueue.id == queue_id).first()
            assert queue is not None
            assert queue.status == "in_review", f"Queue status is {queue.status}, expected in_review after checklist update"
        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
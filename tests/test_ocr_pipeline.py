import os
import sys
import unittest
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.main import app
from app.ocr.field_extractor import extract_fields
from app.ocr.document_verifier import verify_document_fields, MANDATORY_DISCLAIMER


class TestDocumentIntelligencePipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.sample_docs_dir = os.path.join(os.path.dirname(__file__), "sample_docs")
        cls.clean_doc_path = os.path.join(cls.sample_docs_dir, "sample_sale_deed_clean.txt")
        cls.mismatch_doc_path = os.path.join(cls.sample_docs_dir, "sample_sale_deed_mismatch.txt")

    def test_01_field_extraction_clean_document(self):
        with open(self.clean_doc_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        fields = extract_fields(raw_text)

        self.assertIsNotNone(fields["owner_name"], "owner_name should be extracted")
        self.assertIn("Rajesh", fields["owner_name"])
        self.assertIsNotNone(fields["property_id"])
        self.assertEqual(fields["property_id"], "PROP-1002")
        self.assertEqual(fields["survey_number"], "124/2A")
        self.assertIsNotNone(fields["area"])
        self.assertIn("1200", fields["area"])
        self.assertEqual(fields["document_date"], "15/08/2023")
        self.assertEqual(fields["registration_number"], "REG/2023/8892")

    def test_02_verification_match_case(self):
        with open(self.clean_doc_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        fields = extract_fields(raw_text)
        
        target_property = {
            "owner_name": "Rajesh Kumar",
            "property_address": "Plot No. 42, Sunrise Enclave, MG Road, Bengaluru",
            "property_id": "PROP-1002",
            "survey_number": "124/2A",
            "area": "1200 sq ft",
            "document_date": "15/08/2023",
            "registration_number": "REG/2023/8892"
        }

        report = verify_document_fields(fields, target_property)

        self.assertEqual(report["overall_status"], "verified")
        self.assertEqual(report["disclaimer"], MANDATORY_DISCLAIMER)

    def test_03_verification_mismatch_case(self):
        with open(self.mismatch_doc_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        fields = extract_fields(raw_text)

        target_property = {
            "owner_name": "Rajesh Kumar",
            "property_address": "Plot No. 42, Sunrise Enclave, MG Road, Bengaluru",
            "property_id": "PROP-1002",
            "survey_number": "124/2A",
            "area": "1200 sq ft",
            "document_date": "15/08/2023",
            "registration_number": "REG/2023/8892"
        }

        report = verify_document_fields(fields, target_property)

        self.assertEqual(report["overall_status"], "mismatch")
        mismatched_fields = [item["field"] for item in report["match_results"] if item["status"] == "mismatch"]
        self.assertGreater(len(mismatched_fields), 0, "Should detect mismatched fields")
        self.assertEqual(report["disclaimer"], MANDATORY_DISCLAIMER)

    def test_04_api_endpoints_end_to_end(self):
        # 1. Upload
        with open(self.clean_doc_path, "rb") as f:
            response = self.client.post(
                "/api/v1/documents/upload",
                data={"property_id": "PROP-1002", "doc_type": "sale_deed"},
                files={"file": ("sample_sale_deed_clean.txt", f, "text/plain")}
            )
        self.assertEqual(response.status_code, 201)
        upload_data = response.json()
        self.assertIn("document_id", upload_data)
        doc_id = upload_data["document_id"]

        # 2. Verify
        target_payload = {
            "owner_name": "Rajesh Kumar",
            "property_address": "Plot No. 42, Sunrise Enclave, MG Road, Bengaluru",
            "property_id": "PROP-1002",
            "survey_number": "124/2A",
            "area": "1200 sq ft",
            "document_date": "15/08/2023",
            "registration_number": "REG/2023/8892"
        }
        verify_response = self.client.post(f"/api/v1/documents/{doc_id}/verify", json=target_payload)
        self.assertEqual(verify_response.status_code, 200)
        verify_data = verify_response.json()
        self.assertEqual(verify_data["overall_status"], "verified")
        self.assertEqual(verify_data["disclaimer"], MANDATORY_DISCLAIMER)

        # 3. GET Document details
        get_response = self.client.get(f"/api/v1/documents/{doc_id}")
        self.assertEqual(get_response.status_code, 200)
        doc_data = get_response.json()
        self.assertEqual(doc_data["document_id"], doc_id)
        self.assertIsNotNone(doc_data["verification"])


if __name__ == "__main__":
    unittest.main()

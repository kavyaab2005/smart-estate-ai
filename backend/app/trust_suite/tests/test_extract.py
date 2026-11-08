import unittest
from app.trust_suite.services.extract import extract_trust_fields, ExtractedField
from app.trust_suite.schemas import mask_identifiers


class TestExtract(unittest.TestCase):

    def test_extract_preserves_page_numbers(self):
        pages = [
            {"page": 1, "text": "Owner Name: Rajesh Kumar\nSurvey Number: 123/2", "method": "text_layer", "warnings": []},
            {"page": 2, "text": "Area: 1200 sq ft", "method": "text_layer", "warnings": []},
        ]
        result = extract_trust_fields(pages, doc_type_hint="sale_deed")
        page_nums = [f.page_number for f in result]
        self.assertIn(1, page_nums)
        self.assertIn(2, page_nums)

    def test_extract_drops_pan_aadhaar(self):
        pages = [
            {"page": 1, "text": "PAN: ABCDE1234F\nAadhaar: 1234 5678 9012\nOwner: Rajesh", "method": "text_layer", "warnings": []},
        ]
        result = extract_trust_fields(pages)
        field_names = [f.field_name for f in result]
        self.assertNotIn("pan_number", field_names)
        self.assertNotIn("aadhaar_masked", field_names)

    def test_extract_masks_values(self):
        pages = [
            {"page": 1, "text": "Owner: Rajesh Kumar\nPAN: ABCDE1234F", "method": "text_layer", "warnings": []},
        ]
        result = extract_trust_fields(pages)
        for f in result:
            self.assertNotIn("ABCDE1234F", f.raw_value)
            self.assertNotIn("ABCDE1234F", f.normalized_value)

    def test_extract_returns_extractedfield_dataclass(self):
        pages = [
            {"page": 1, "text": "Owner: Rajesh Kumar", "method": "text_layer", "warnings": []},
        ]
        result = extract_trust_fields(pages)
        self.assertTrue(all(isinstance(f, ExtractedField) for f in result))
        self.assertTrue(hasattr(result[0], "field_name"))
        self.assertTrue(hasattr(result[0], "raw_value"))
        self.assertTrue(hasattr(result[0], "normalized_value"))
        self.assertTrue(hasattr(result[0], "page_number"))
        self.assertTrue(hasattr(result[0], "extraction_method"))

    def test_extract_empty_pages(self):
        pages = [
            {"page": 1, "text": "", "method": "text_layer", "warnings": []},
            {"page": 2, "text": "   ", "method": "text_layer", "warnings": []},
        ]
        result = extract_trust_fields(pages)
        self.assertEqual(len(result), 0)

    def test_extract_synthetic_multipage(self):
        pages = [
            {"page": 1, "text": "Owner Name: Rajesh Kumar\nSurvey Number: 123/2", "method": "text_layer", "warnings": []},
            {"page": 2, "text": "Property Address: 123 Main St, Bangalore\nArea: 1200 sq ft", "method": "text_layer", "warnings": []},
            {"page": 3, "text": "Registration Date: 15/08/2023\nRegistration Number: REG/2023/123", "method": "text_layer", "warnings": []},
        ]
        result = extract_trust_fields(pages, doc_type_hint="sale_deed")
        self.assertEqual(len(result), 6)
        page_counts = {}
        for f in result:
            page_counts[f.page_number] = page_counts.get(f.page_number, 0) + 1
        self.assertEqual(page_counts[1], 2)
        self.assertEqual(page_counts[2], 2)
        self.assertEqual(page_counts[3], 2)


if __name__ == "__main__":
    unittest.main()

import unittest
from app.trust_suite.schemas import mask_identifiers, mask_identifiers_in_dict


class TestMaskIdentifiers(unittest.TestCase):

    def test_aadhaar_12_digit_contiguous(self):
        text = "Aadhaar: 123456789012"
        result = mask_identifiers(text)
        self.assertEqual(result, "Aadhaar: XXXX-XXXX-9012")

    def test_aadhaar_with_spaces(self):
        text = "Aadhaar: 1234 5678 9012"
        result = mask_identifiers(text)
        self.assertEqual(result, "Aadhaar: XXXX-XXXX-9012")

    def test_aadhaar_with_hyphens(self):
        text = "Aadhaar: 1234-5678-9012"
        result = mask_identifiers(text)
        self.assertEqual(result, "Aadhaar: XXXX-XXXX-9012")

    def test_aadhaar_mixed_separators(self):
        text = "Aadhaar: 1234 5678-9012"
        result = mask_identifiers(text)
        self.assertEqual(result, "Aadhaar: XXXX-XXXX-9012")

    def test_multiple_aadhaar(self):
        text = "First: 111122223333, Second: 444455556666"
        result = mask_identifiers(text)
        self.assertEqual(result, "First: XXXX-XXXX-3333, Second: XXXX-XXXX-6666")

    def test_pan_basic(self):
        text = "PAN: ABCDE1234F"
        result = mask_identifiers(text)
        self.assertEqual(result, "PAN: XXXXX1234X")

    def test_pan_lowercase(self):
        text = "Pan: abcde1234f"
        result = mask_identifiers(text)
        self.assertEqual(result, "Pan: XXXXX1234X")

    def test_pan_mixed_case(self):
        text = "Pan: AbCdE1234F"
        result = mask_identifiers(text)
        self.assertEqual(result, "Pan: XXXXX1234X")

    def test_both_aadhaar_and_pan(self):
        text = "Aadhaar 123456789012 PAN ABCDE1234F"
        result = mask_identifiers(text)
        self.assertEqual(result, "Aadhaar XXXX-XXXX-9012 PAN XXXXX1234X")

    def test_survey_number_not_masked(self):
        text = "Survey Number: 124/2A"
        result = mask_identifiers(text)
        self.assertEqual(result, "Survey Number: 124/2A")

    def test_survey_number_with_sy_no_not_masked(self):
        text = "Sy No 45/2"
        result = mask_identifiers(text)
        self.assertEqual(result, "Sy No 45/2")

    def test_date_not_masked(self):
        text = "Date: 15/08/2023"
        result = mask_identifiers(text)
        self.assertEqual(result, "Date: 15/08/2023")

    def test_date_dash_not_masked(self):
        text = "Date: 15-08-2023"
        result = mask_identifiers(text)
        self.assertEqual(result, "Date: 15-08-2023")

    def test_registration_number_not_masked(self):
        text = "Registration: REG/2023/8892"
        result = mask_identifiers(text)
        self.assertEqual(result, "Registration: REG/2023/8892")

    def test_property_id_not_masked(self):
        text = "Property ID: PROP-1002"
        result = mask_identifiers(text)
        self.assertEqual(result, "Property ID: PROP-1002")

    def test_area_not_masked(self):
        text = "Area: 1200 sq ft"
        result = mask_identifiers(text)
        self.assertEqual(result, "Area: 1200 sq ft")

    def test_empty_string(self):
        result = mask_identifiers("")
        self.assertEqual(result, "")

    def test_none_input(self):
        result = mask_identifiers(None)
        self.assertIsNone(result)

    def test_no_identifiers(self):
        text = "Owner: Rajesh Kumar, Address: Bengaluru"
        result = mask_identifiers(text)
        self.assertEqual(result, "Owner: Rajesh Kumar, Address: Bengaluru")

    def test_aadhaar_partial_not_matched(self):
        text = "Number: 12345678901"  # 11 digits
        result = mask_identifiers(text)
        self.assertEqual(result, "Number: 12345678901")

    def test_aadhaar_too_long_not_matched(self):
        text = "Number: 1234567890123"  # 13 digits
        result = mask_identifiers(text)
        self.assertEqual(result, "Number: 1234567890123")

    def test_mask_identifiers_in_dict(self):
        data = {
            "owner_name": "Rajesh Kumar",
            "aadhaar": "123456789012",
            "pan": "ABCDE1234F",
            "nested": {
                "survey_number": "124/2A",
                "aadhaar": "111122223333"
            },
            "items": [
                {"field": "aadhaar", "value": "444455556666"},
                {"field": "survey", "value": "45/2"}
            ]
        }
        result = mask_identifiers_in_dict(data)
        self.assertEqual(result["owner_name"], "Rajesh Kumar")
        self.assertEqual(result["aadhaar"], "XXXX-XXXX-9012")
        self.assertEqual(result["pan"], "XXXXX1234X")
        self.assertEqual(result["nested"]["survey_number"], "124/2A")
        self.assertEqual(result["nested"]["aadhaar"], "XXXX-XXXX-3333")
        self.assertEqual(result["items"][0]["value"], "XXXX-XXXX-6666")
        self.assertEqual(result["items"][1]["value"], "45/2")


if __name__ == "__main__":
    unittest.main()
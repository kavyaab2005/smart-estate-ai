import unittest
from app.trust_suite.services.doc_types import (
    DocType,
    normalize_doc_type,
    detect_rtc,
    UnsupportedDocumentType,
)


class TestDocTypes(unittest.TestCase):

    def test_normalize_sale_deed_variants(self):
        self.assertEqual(normalize_doc_type("sale_deed"), DocType.SALE_DEED)
        self.assertEqual(normalize_doc_type("sale deed"), DocType.SALE_DEED)
        self.assertEqual(normalize_doc_type("title_deed"), DocType.SALE_DEED)
        self.assertEqual(normalize_doc_type("title deed"), DocType.SALE_DEED)

    def test_normalize_ec_variants(self):
        self.assertEqual(normalize_doc_type("encumbrance_certificate"), DocType.EC)
        self.assertEqual(normalize_doc_type("encumbrance certificate"), DocType.EC)
        self.assertEqual(normalize_doc_type("ec"), DocType.EC)

    def test_normalize_khata_variants(self):
        self.assertEqual(normalize_doc_type("khata"), DocType.KHATA)
        self.assertEqual(normalize_doc_type("khata_certificate"), DocType.KHATA)
        self.assertEqual(normalize_doc_type("khata certificate"), DocType.KHATA)
        self.assertEqual(normalize_doc_type("khata_extract"), DocType.KHATA)

    def test_normalize_tax_receipt_variants(self):
        self.assertEqual(normalize_doc_type("property_tax_receipt"), DocType.TAX_RECEIPT)
        self.assertEqual(normalize_doc_type("tax_receipt"), DocType.TAX_RECEIPT)
        self.assertEqual(normalize_doc_type("tax receipt"), DocType.TAX_RECEIPT)

    def test_normalize_rtc_variants(self):
        self.assertEqual(normalize_doc_type("rtc"), DocType.RTC)
        self.assertEqual(normalize_doc_type("pahani"), DocType.RTC)
        self.assertEqual(normalize_doc_type("record_of_rights"), DocType.RTC)
        self.assertEqual(normalize_doc_type("tenancy_and_crops"), DocType.RTC)

    def test_normalize_other_variants(self):
        self.assertEqual(normalize_doc_type("approved_plan"), DocType.OTHER)
        self.assertEqual(normalize_doc_type("other"), DocType.OTHER)
        self.assertEqual(normalize_doc_type("unknown"), DocType.OTHER)
        self.assertEqual(normalize_doc_type("random"), DocType.OTHER)

    def test_unsupported_id_documents(self):
        for dt in ["seller_id", "aadhaar", "pan", "voter", "passport", "driving_licence", "driving_license", "identity_proof", "id_proof"]:
            with self.assertRaises(UnsupportedDocumentType):
                normalize_doc_type(dt)

    def test_detect_rtc_positive(self):
        texts = [
            "RTC\nSurvey No: 123",
            "Pahani extract for property",
            "Record of Rights\nKhatedar: John",
            "Tenancy and Crops Register",
            "Revenue Department RTC",
        ]
        for text in texts:
            self.assertTrue(detect_rtc(text), f"Should detect RTC in: {text}")

    def test_detect_rtc_negative(self):
        texts = [
            "Sale Deed\nOwner: Rajesh",
            "Encumbrance Certificate",
            "Khata Certificate",
            "Property Tax Receipt",
            "",
            None,
        ]
        for text in texts:
            self.assertFalse(detect_rtc(text or ""))


if __name__ == "__main__":
    unittest.main()

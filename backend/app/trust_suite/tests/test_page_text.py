import unittest
from app.trust_suite.services.page_text import read_pages


class TestPageText(unittest.TestCase):

    def test_read_pages_pdf_garbage(self):
        """Garbage bytes should not raise, return error entry"""
        result = read_pages(b"not a pdf", "test.pdf")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].method, "error")
        self.assertTrue(any("pdf_unreadable" in w for w in result[0].warnings))

    def test_read_pages_image(self):
        """Image files return needs_ocr"""
        result = read_pages(b"fake image", "test.jpg")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].method, "needs_ocr")
        self.assertEqual(result[0].page, 1)

    def test_read_pages_text(self):
        """Text files return plain_text"""
        result = read_pages(b"Hello world", "test.txt")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].method, "plain_text")
        self.assertEqual(result[0].text, "Hello world")

    def test_read_pages_unknown_extension(self):
        """Unknown extension tries as image"""
        result = read_pages(b"data", "test.xyz")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].method, "needs_ocr")


if __name__ == "__main__":
    unittest.main()

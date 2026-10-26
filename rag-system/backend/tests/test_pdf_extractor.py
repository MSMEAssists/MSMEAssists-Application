import os
import unittest

from app.extractors.pdf_extractor import extract_pdf
from app.processors.cleaner import clean_pdf_pages

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class TestPdfExtractor(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(FIXTURE_DIR, "notification.pdf"), "rb") as f:
            self.raw = f.read()

    def test_page_texts_preserved(self):
        result = extract_pdf(self.raw)
        self.assertIsNotNone(result.page_texts)
        self.assertEqual(len(result.page_texts), 3)

    def test_content_extracted_per_page(self):
        result = extract_pdf(self.raw)
        self.assertIn("Tender No", result.page_texts[0])
        self.assertIn("Eligibility", result.page_texts[1])
        self.assertIn("Least Cost Selection", result.page_texts[2])

    def test_repeated_header_footer_removed(self):
        result = extract_pdf(self.raw)
        cleaned_pages = clean_pdf_pages(result.page_texts)
        # The repeated title/tender-number header appeared on all 3 pages
        # and should be stripped by the header/footer detector.
        occurrences = sum(1 for p in cleaned_pages if "Government e-Procurement Notification" in p)
        self.assertEqual(occurrences, 0)
        # But page-specific content must remain.
        self.assertIn("Eligibility", cleaned_pages[1])


if __name__ == "__main__":
    unittest.main()

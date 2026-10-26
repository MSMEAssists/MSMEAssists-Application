import os
import unittest

from app.extractors.html_extractor import extract_html

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class TestHtmlExtractor(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(FIXTURE_DIR, "scheme_page.html"), encoding="utf-8") as f:
            self.html = f.read()

    def test_title_extracted(self):
        result = extract_html(self.html, "https://www.msme.gov.in/schemes/pmegp")
        self.assertIn("PMEGP", result.title)

    def test_nav_and_scripts_removed(self):
        result = extract_html(self.html, "https://www.msme.gov.in/schemes/pmegp")
        self.assertNotIn("console.log", result.text)
        self.assertNotIn("Home | Schemes | About | Contact", result.text)

    def test_headings_and_lists_extracted(self):
        result = extract_html(self.html, "https://www.msme.gov.in/schemes/pmegp")
        self.assertIn("Eligibility", result.headings)
        self.assertIn("Financial Assistance", result.headings)
        self.assertTrue(any("Proof of identity" in item for lst in result.lists for item in lst))

    def test_key_content_preserved(self):
        result = extract_html(self.html, "https://www.msme.gov.in/schemes/pmegp")
        self.assertIn("15% to 35%", result.text)
        self.assertIn("Rs. 50 lakh", result.text)


if __name__ == "__main__":
    unittest.main()

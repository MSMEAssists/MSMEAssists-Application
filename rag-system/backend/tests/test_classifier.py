import os
import unittest

from app.extractors.html_extractor import extract_html
from app.models.entities import KnowledgeType
from app.processors.classifier import classify, extract_fields

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load(name):
    with open(os.path.join(FIXTURE_DIR, name), encoding="utf-8") as f:
        return f.read()


class TestClassifier(unittest.TestCase):
    def test_scheme_classified_as_scheme(self):
        html = _load("scheme_page.html")
        extracted = extract_html(html, "https://www.msme.gov.in/schemes/pmegp")
        result = classify(extracted.title, extracted.text)
        self.assertEqual(result, KnowledgeType.SCHEME)

    def test_loan_classified_as_loan_not_scheme(self):
        html = _load("loan_page.html")
        extracted = extract_html(html, "https://www.sidbi.in/en/loans/wctl")
        result = classify(extracted.title, extracted.text)
        self.assertEqual(result, KnowledgeType.LOAN)

    def test_procurement_notification_classified(self):
        text = "This tender notice invites e-procurement bids for supply of equipment via the e-tendering portal."
        result = classify("GeM Tender Notice", text)
        self.assertEqual(result, KnowledgeType.PROCUREMENT)

    def test_unrelated_page_classified_other(self):
        result = classify("Contact Us", "Phone: 011-12345678. Address: New Delhi.")
        self.assertEqual(result, KnowledgeType.OTHER)

    def test_scheme_field_extraction_no_invented_fields(self):
        html = _load("scheme_page.html")
        extracted = extract_html(html, "https://www.msme.gov.in/schemes/pmegp")
        fields = extract_fields(KnowledgeType.SCHEME, extracted.title, extracted.text, extracted.headings)
        self.assertIsNotNone(fields["eligibility"])
        self.assertIn("18 years", fields["eligibility"])
        self.assertIsNotNone(fields["financial_assistance"])
        # A field with no corresponding section in the source must stay
        # unavailable (None) -- never guessed/invented.
        self.assertIsNone(fields.get("subsidy_details"))

    def test_loan_field_extraction_no_fabricated_interest_rate(self):
        html = _load("loan_page.html")
        extracted = extract_html(html, "https://www.sidbi.in/en/loans/wctl")
        fields = extract_fields(KnowledgeType.LOAN, extracted.title, extracted.text, extracted.headings)
        self.assertIsNotNone(fields["interest_information"])
        # The source explicitly says the rate is decided case-to-case --
        # the extractor must preserve that ambiguity, never invent a number.
        self.assertNotRegex(fields["interest_information"], r"\d+(\.\d+)?\s*%")


if __name__ == "__main__":
    unittest.main()

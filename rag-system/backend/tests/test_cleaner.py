import unittest

from app.processors.cleaner import clean_text, normalize_whitespace, remove_duplicate_lines


class TestCleaner(unittest.TestCase):
    def test_whitespace_normalized(self):
        text = "Eligibility:    Any\u00a0individual   above 18\n\n\n\nyears."
        out = normalize_whitespace(text)
        self.assertNotIn("   ", out)
        self.assertNotIn("\n\n\n", out)

    def test_important_content_preserved(self):
        text = "Eligibility: Any individual above 18 years.\nSubsidy: 35% of project cost.\nApply before 31 March 2027."
        out = clean_text(text)
        self.assertIn("35%", out)
        self.assertIn("31 March 2027", out)
        self.assertIn("Eligibility", out)

    def test_duplicate_long_lines_removed(self):
        text = "This is a fairly long repeated boilerplate footer line.\nSome real content here.\nThis is a fairly long repeated boilerplate footer line."
        out = remove_duplicate_lines(text)
        self.assertEqual(out.count("This is a fairly long repeated boilerplate footer line."), 1)

    def test_short_lines_not_over_collapsed(self):
        text = "Rs. 50 lakh\nSome content\nRs. 50 lakh"
        out = remove_duplicate_lines(text)
        # Short lines (dates/amounts) may legitimately repeat -- kept as-is.
        self.assertEqual(out.count("Rs. 50 lakh"), 2)


if __name__ == "__main__":
    unittest.main()

import unittest

from app.chunking.chunker import chunk_document, chunk_text


class TestChunker(unittest.TestCase):
    def test_short_text_single_chunk(self):
        spans = chunk_text("Short scheme description.", chunk_size=900, chunk_overlap=150)
        self.assertEqual(len(spans), 1)

    def test_long_text_splits_into_multiple_chunks(self):
        paragraph = "Eligibility criteria and application details. " * 60  # long
        spans = chunk_text(paragraph, chunk_size=500, chunk_overlap=100)
        self.assertGreater(len(spans), 1)
        for span in spans:
            self.assertLessEqual(len(span.text), 500 + 5)  # small slack for boundary rounding

    def test_overlap_present_between_consecutive_chunks(self):
        text = "\n\n".join([f"Section {i}: " + ("content word " * 40) for i in range(6)])
        spans = chunk_text(text, chunk_size=400, chunk_overlap=100)
        self.assertGreater(len(spans), 1)
        # Some tail of chunk N should reappear at the head of chunk N+1.
        tail = spans[0].text[-50:]
        self.assertTrue(any(tail[:20] in spans[i].text for i in range(1, len(spans))))

    def test_pdf_chunking_preserves_page_numbers(self):
        page_texts = ["Page one content about eligibility.", "Page two content about documents required."]
        spans = chunk_document(text="", page_texts=page_texts, chunk_size=900, chunk_overlap=100)
        pages_seen = {s.page_number for s in spans}
        self.assertEqual(pages_seen, {1, 2})


if __name__ == "__main__":
    unittest.main()

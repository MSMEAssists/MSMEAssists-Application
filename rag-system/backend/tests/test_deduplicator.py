import unittest

from app.processors.deduplicator import decide


class TestDeduplicator(unittest.TestCase):
    def test_new_document(self):
        result = decide(b"hello world", existing_document_id=None, existing_content_hash=None)
        self.assertTrue(result.is_new)
        self.assertFalse(result.is_unchanged)

    def test_unchanged_document(self):
        content = b"same content"
        first = decide(content, None, None)
        second = decide(content, existing_document_id="doc_1", existing_content_hash=first.new_content_hash)
        self.assertFalse(second.is_new)
        self.assertTrue(second.is_unchanged)

    def test_changed_document_triggers_new_version_not_new_document(self):
        old_hash = decide(b"version one text", None, None).new_content_hash
        result = decide(b"version two text, updated", existing_document_id="doc_1", existing_content_hash=old_hash)
        self.assertFalse(result.is_new)
        self.assertFalse(result.is_unchanged)
        self.assertEqual(result.existing_document_id, "doc_1")


if __name__ == "__main__":
    unittest.main()

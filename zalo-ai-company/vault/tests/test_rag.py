"""QA — Company Vault RAG (PR-004). Offline keyword retriever; embeddings gated."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from rag import Vault, chunk  # noqa: E402


class TestVault(unittest.TestCase):
    def test_chunk(self):
        self.assertEqual(chunk(""), [])
        self.assertTrue(len(chunk("x" * 1000, size=400, overlap=40)) >= 2)

    def test_ingest_and_search(self):
        v = Vault()
        v.ingest("policy1", "Chính sách bảo hành sản phẩm Premium trong 12 tháng.", {"src": "drive"})
        v.ingest("policy2", "Hướng dẫn thanh toán và hoàn tiền.", {})
        hits = v.search("bảo hành Premium", k=3)
        self.assertTrue(hits)
        self.assertEqual(hits[0]["doc_id"], "policy1")

    def test_search_empty_query(self):
        self.assertEqual(Vault().search(""), [])

    def test_retriever_mode_dry_run_by_default(self):
        v = Vault(env={})
        self.assertEqual(v.health()["retriever"], "keyword(dry-run)")
        self.assertFalse(v.drive_enabled())

    def test_embeddings_gated_by_env(self):
        v = Vault(env={"OPENAI_API_KEY": "x"})
        self.assertTrue(v.embeddings_enabled())
        self.assertEqual(v.health()["retriever"], "embeddings")


if __name__ == "__main__":
    unittest.main()

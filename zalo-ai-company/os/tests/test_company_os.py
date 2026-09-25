"""QA — Company OS façade (PRD-016). E2E compose 6 thành phần."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from company_os import CompanyOS  # noqa: E402


class TestCompanyOS(unittest.TestCase):
    def test_handle_resolves_and_logs(self):
        os_ = CompanyOS()
        r = os_.handle("Cho mình báo giá gói Premium")
        self.assertTrue(r["resolved"])
        self.assertEqual(r["agent_id"], "ag-sales-01")
        self.assertEqual(os_.qa.summary()["pass"], 1)

    def test_status_composition(self):
        os_ = CompanyOS()
        st = os_.status()
        self.assertEqual(st["agents"]["registered"], 9)
        self.assertEqual(st["skills"]["registered"], 6)

    def test_gate_and_rollback_persist(self):
        with tempfile.TemporaryDirectory() as d:
            os_ = CompanyOS(qa_store=os.path.join(d, "qa.json"),
                            rollback_store=os.path.join(d, "rb.json"))
            os_.qa_gate("regression", "full-suite", "PASS")
            os_.record_rollback("WF005", "gate fail simuln", "v2", "v1")
            os2 = CompanyOS(qa_store=os.path.join(d, "qa.json"),
                            rollback_store=os.path.join(d, "rb.json"))
            self.assertGreaterEqual(os2.qa.summary()["total"], 1)
            self.assertEqual(os2.rollback.last()["target"], "WF005")


if __name__ == "__main__":
    unittest.main()

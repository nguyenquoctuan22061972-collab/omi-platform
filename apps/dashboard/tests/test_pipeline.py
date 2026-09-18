"""QA — Pipeline (PRD-006 C)."""
import json
import os
import unittest

D = os.path.join(os.path.dirname(__file__), "..", "pipeline")
STAGES = ["lead", "contacted", "qualified", "proposal", "won", "lost"]


def r(*p):
    with open(os.path.join(D, *p), encoding="utf-8") as f:
        return f.read()


class TestPipeline(unittest.TestCase):
    def test_files_exist(self):
        for f in ("index.html", "pipeline.js", os.path.join("mock", "deals.json")):
            self.assertTrue(os.path.isfile(os.path.join(D, f)), f)

    def test_stages_match_prd001(self):
        js = r("pipeline.js")
        for s in STAGES:
            self.assertIn(s, js)

    def test_deal_detail_and_timeline(self):
        js = r("pipeline.js")
        self.assertIn("activity", js)
        self.assertIn("timeline", js.lower())

    def test_mock_valid(self):
        data = json.loads(r("mock", "deals.json"))
        self.assertTrue(isinstance(data, list) and data)
        for d in data:
            self.assertIn(d["stage"], STAGES)


if __name__ == "__main__":
    unittest.main()

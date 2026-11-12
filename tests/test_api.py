"""Contract tests for the JSON API behind the Audit Desk web app.

Uses a temporary case database so the local investigation register is untouched.
"""
import os
import tempfile
import unittest
from pathlib import Path

_TMP = tempfile.TemporaryDirectory()
os.environ["AUDIT_DB_PATH"] = str(Path(_TMP.name) / "cases.db")

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402
from src.audit_research import demo_rates  # noqa: E402
from src.generate_data import generate_finance_operations  # noqa: E402


class AuditApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        _TMP.cleanup()

    def get(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_overview_department_filter_narrows_totals(self):
        everything = self.get("/api/overview")
        one = self.get(f"/api/overview?department={everything['departments'][0]}")
        self.assertLess(one["kpis"]["transactions"], everything["kpis"]["transactions"])
        self.assertAlmostEqual(sum(row["spend"] for row in everything["by_department"]), everything["kpis"]["spend"], places=4)

    def test_queue_is_ten_percent_with_reasons(self):
        overview = self.get("/api/overview")
        queue = self.get("/api/queue")
        self.assertEqual(len(queue["rows"]), -(-overview["kpis"]["transactions"] // 10))
        self.assertTrue(all(row["reasons"] for row in queue["rows"]))
        scores = [row["score"] for row in queue["rows"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_case_save_history_and_conflict(self):
        transaction_id = self.get("/api/queue")["rows"][0]["id"]
        first = self.client.put(f"/api/cases/{transaction_id}", json={"status": "In review", "reviewer": "Ana", "notes": "Checking", "version": 0})
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["case"]["version"], 1)
        stale = self.client.put(f"/api/cases/{transaction_id}", json={"status": "Resolved", "version": 0})
        self.assertEqual(stale.status_code, 409)
        detail = self.get(f"/api/transactions/{transaction_id}")
        self.assertEqual(detail["case"]["status"], "In review")
        self.assertEqual(len(detail["history"]), 1)
        listed = self.get("/api/cases")["rows"]
        self.assertIn(transaction_id, [row["transaction_id"] for row in listed])
        self.assertEqual(self.client.put(f"/api/cases/{transaction_id}", json={"status": "Lost", "version": 1}).status_code, 400)

    def test_research_reports_each_method(self):
        research = self.get("/api/research")
        self.assertEqual(len(research["methods"]), 3)
        self.assertEqual(sum(method["selected"] for method in research["methods"]), 1)

    def test_upload_valid_and_invalid_files(self):
        good = self.client.post("/api/upload", json={
            "transactions_csv": generate_finance_operations(600).to_csv(index=False),
            "rates_csv": demo_rates().to_csv(index=False),
        })
        self.assertEqual(good.status_code, 200, good.text)
        self.assertEqual(self.get(f"/api/overview?dataset={good.json()['dataset']}")["kpis"]["transactions"] > 0, True)
        bad = self.client.post("/api/upload", json={"transactions_csv": "a,b\n1,2", "rates_csv": "x\n1"})
        self.assertEqual(bad.status_code, 422)
        self.assertEqual(self.client.get("/api/overview?dataset=upload-missing").status_code, 404)


if __name__ == "__main__":
    unittest.main()

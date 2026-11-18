"""USAspending scoring tests with hand-made rows in the API's format (no network)."""
import unittest
from unittest import mock

from src import public_spending


def rows():
    data = []
    for i in range(60):
        data.append({"Award ID": f"A{i:03d}", "Mod": "0", "Recipient Name": f"VENDOR {i % 12}", "Recipient UEI": f"U{i % 12}",
                     "Action Date": f"2026-03-{(i % 20) + 2:02d}", "Transaction Amount": 20_000 + 731 * i,
                     "Awarding Agency": "Department of Health and Human Services", "Awarding Sub Agency": ["NIH", "CDC", "FDA"][i % 3],
                     "Award Type": "PURCHASE ORDER", "Transaction Description": "SUPPLIES", "naics_description": "WHOLESALE",
                     "product_or_service_description": "LAB EQUIPMENT", "generated_internal_id": f"CONT_{i}"})
    data[0].update({"Transaction Amount": 50_000_000})                                   # very large, round
    data[1].update({"Transaction Amount": -12_000, "Mod": "2"})                          # money returned
    data[2].update({"Recipient Name": "REPEAT LLC", "Transaction Amount": 77_777, "Action Date": "2026-03-02"})
    data[3].update({"Recipient Name": "REPEAT LLC", "Transaction Amount": 77_777, "Action Date": "2026-03-05", "Award ID": "B003"})
    return data


class PublicSpendingTests(unittest.TestCase):
    def setUp(self):
        self.df, self.meta = public_spending.score(public_spending.prepare(rows()))

    def by_id(self, award):
        return self.df[self.df.award_id == award].iloc[0]

    def test_reasons_are_plain_and_specific(self):
        self.assertIn("Among this agency's largest 5%", self.by_id("A000").flag_reasons)
        self.assertIn("Round amount", self.by_id("A000").flag_reasons)
        self.assertIn("Same amount to the same recipient within 7 days", self.by_id("B003").flag_reasons)
        self.assertIn("Money returned (de-obligation)", self.by_id("A001").flag_reasons)

    def test_refunds_are_never_queued_and_queue_is_ten_percent(self):
        self.assertEqual(self.by_id("A001").model_prediction, 0)
        self.assertEqual(int(self.df.model_prediction.sum()), 6)  # ceil(10% of 60)
        self.assertEqual(self.by_id("A000").model_prediction, 1)

    def test_metadata_is_honest_about_labels(self):
        self.assertFalse(self.meta["labelled"])
        self.assertIn("not evidence of wrongdoing", self.meta["interpretation"])
        self.assertTrue((self.df.is_anomaly == 0).all())

    def test_fetch_samples_every_month_and_caches(self):
        calls = []

        def fake_request(body):
            calls.append(body["filters"]["time_period"][0]["start_date"])
            return {"results": rows()[:2]}

        with mock.patch.object(public_spending, "_request", side_effect=fake_request), \
             mock.patch.object(public_spending, "CACHE", public_spending.CACHE.parent / "test-usaspending"):
            result = public_spending.fetch("hhs", 2026, refresh=True)
            cached = public_spending.fetch("hhs", 2026)
        self.assertEqual(calls[0], "2025-10-01")
        self.assertEqual(calls[-1], "2026-09-01")
        self.assertEqual(len(calls), 12)
        self.assertEqual(len(result), 24)
        self.assertEqual(cached, result)

    def test_unknown_agency_is_rejected(self):
        with self.assertRaises(ValueError):
            public_spending.fetch("nope", 2026)


if __name__ == "__main__":
    unittest.main()

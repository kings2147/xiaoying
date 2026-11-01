import copy
import unittest

from xiaoying_agents.core import Store, run
from xiaoying_agents.media import MediaTask
from xiaoying_agents.models import MockModel


BASE = {"request_id": "m-test", "material_ids": ["M01"],
        "requirements": {"M01": {"slot": "2026-11-02T18:00:00+08:00", "hard": True}}}


class MediaTests(unittest.TestCase):
    def execute(self, **changes):
        request = copy.deepcopy(BASE)
        request.update(changes)
        return run(MediaTask(request, Store()), MockModel())

    def test_normal_and_no_publication(self):
        result = self.execute()["result"]
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["draft"]["payload"]["state"], "draft")
        self.assertEqual(result["publication_status"], "not_published")

    def test_missing_material_and_metadata(self):
        for mid in ["M03", "unknown"]:
            result = self.execute(material_ids=[mid])["result"]
            self.assertEqual(result["status"], "needs_information")
            self.assertIsNone(result["draft"])

    def test_rule_risk_blocked(self):
        result = self.execute(material_ids=["M02"])["result"]
        self.assertEqual(result["status"], "blocked")
        self.assertIn("rights_not_cleared", result["items"][0]["risks"])

    def test_conflict_requires_explicit_approval(self):
        result = self.execute(occupied_slots=[BASE["requirements"]["M01"]["slot"]])["result"]
        self.assertEqual(result["status"], "awaiting_confirmation")
        self.assertTrue(result["items"][0]["pending_confirmation"])
        result = self.execute(occupied_slots=[BASE["requirements"]["M01"]["slot"]], confirmed_changes={"M01": "2026-11-02T19:00:00+08:00"})["result"]
        self.assertEqual(result["status"], "completed")

    def test_repeat_save_and_failure(self):
        store = Store()
        first = run(MediaTask(BASE, store), MockModel())
        second = run(MediaTask(BASE, store), MockModel())
        self.assertEqual(first["result"]["draft"]["id"], second["result"]["draft"]["id"])
        self.assertTrue(second["result"]["draft"]["duplicate"])
        result = self.execute(simulate_failures={"save_draft": -1})["result"]
        self.assertEqual(result["status"], "failed")
        self.assertIsNone(result["draft"])

    def test_cross_material_conflict_and_timezone_equivalence(self):
        request = copy.deepcopy(BASE)
        request.update(material_ids=["M01", "M04"], materials={"M04": {"title": "other", "rights_cleared": True, "sensitive": False}})
        request["requirements"]["M04"] = copy.deepcopy(request["requirements"]["M01"])
        result = run(MediaTask(request, Store()), MockModel())["result"]
        self.assertEqual(len({i["suggested_slot"] for i in result["items"]}), 2)
        result = self.execute(occupied_slots=["2026-11-02T10:00:00+00:00"])["result"]
        self.assertTrue(result["items"][0]["pending_confirmation"])

    def test_guard_rejects_bypassed_review(self):
        task = MediaTask(BASE, Store())
        self.assertFalse(task.execute("propose_slot", {"material_id": "M01", "slot": BASE["requirements"]["M01"]["slot"]})["ok"])
        self.assertFalse(task.execute("save_draft", {})["ok"])

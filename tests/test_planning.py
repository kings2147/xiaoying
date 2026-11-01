import copy
import unittest

from xiaoying_agents.core import Store, run
from xiaoying_agents.models import MockModel
from xiaoying_agents.planning import PlanningTask


BASE = {"request_id":"plan-test","topic":"字幕活动","budget":15,"start_at":"2026-11-02T09:00:00+08:00","deadline":"2026-11-02T12:00:00+08:00"}


class PlanningTests(unittest.TestCase):
    def execute(self, **changes):
        request = copy.deepcopy(BASE)
        request.update(changes)
        return run(PlanningTask(request, Store()), MockModel())

    def test_normal_cost_and_dependencies(self):
        result = self.execute()["result"]
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["total_cost"], 12)
        self.assertEqual(result["saved_plan"]["payload"]["steps"][2]["depends_on"], ["estimate"])

    def test_budget_replanning_12_to_8(self):
        output = self.execute(budget=10)
        self.assertFalse(output["result"]["estimates"]["premium"]["feasible"])
        self.assertEqual(output["result"]["total_cost"], 8)
        self.assertEqual(output["result"]["saved_plan"]["payload"]["script"]["package"], "lean")

    def test_missing_budget_and_deadline(self):
        for key in ["budget", "deadline"]:
            self.assertEqual(self.execute(**{key:None})["result"]["status"], "needs_information")

    def test_failure_preserves_success_and_resumes(self):
        store = Store()
        request = copy.deepcopy(BASE)
        request["simulate_failures"] = {"generate_script":-1}
        first = run(PlanningTask(request, store), MockModel())
        self.assertEqual(first["result"]["status"], "incomplete")
        self.assertTrue(first["result"]["assets"])
        self.assertFalse(first["result"]["successful_scripts"])
        request.pop("simulate_failures")
        second = run(PlanningTask(request, store), MockModel())
        self.assertEqual(second["result"]["status"], "completed")
        self.assertTrue(second["result"]["resumed_from_checkpoint"])
        self.assertNotIn("search_assets", [s["action"]["tool"] for s in second["trace"]])

    def test_no_feasible_budget_or_deadline(self):
        result = self.execute(budget=3)["result"]
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["estimates"]["basic"]["budget_gap"], 2)
        self.assertIsNone(result["saved_plan"])
        self.assertEqual(self.execute(deadline="2026-11-02T09:10:00+08:00")["result"]["status"], "incomplete")

    def test_duplicate_and_overbudget_guard(self):
        store = Store()
        first = run(PlanningTask(BASE,store),MockModel())
        second = run(PlanningTask(BASE,store),MockModel())
        self.assertEqual(first["result"]["saved_plan"]["id"],second["result"]["saved_plan"]["id"])
        self.assertTrue(second["result"]["saved_plan"]["duplicate"])
        task = PlanningTask({**BASE,"budget":3},Store())
        task.execute("search_assets",{"query":"字幕"})
        task.execute("estimate_plan",{"package":"premium"})
        self.assertFalse(task.execute("generate_script",{"package":"premium"})["ok"])
        self.assertFalse(task.execute("save_plan",{"package":"premium"})["ok"])

    def test_nonfinite_or_boolean_budget(self):
        for value in [float("nan"),float("inf"),True,-1]:
            self.assertEqual(self.execute(budget=value)["result"]["status"],"needs_information")

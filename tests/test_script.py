import unittest

from xiaoying_agents.core import Store, run
from xiaoying_agents.models import MockModel
from xiaoying_agents.script import ScriptTask


BASE={"topic":"字幕功能","audience":"新手创作者","platform":"短视频","target_seconds":30,"style":"清晰演示"}


class ScriptTests(unittest.TestCase):
    def execute(self, **changes):
        return run(ScriptTask({**BASE,**changes},Store()),MockModel())

    def test_normal_generated_script_and_sources(self):
        result = self.execute(target_seconds=60)["result"]
        self.assertEqual(result["status"],"completed")
        self.assertTrue(result["script"]["scenes"])
        self.assertEqual(result["rule_check"]["citations"][0]["quote"],"支持字幕")
        self.assertEqual(result["duration"]["total_seconds"],sum(s["seconds"] for s in result["duration"]["scenes"]))

    def test_missing_information_and_no_materials(self):
        self.assertEqual(self.execute(audience=None)["result"]["status"],"needs_information")
        result = self.execute(topic="星际发动机")["result"]
        self.assertEqual(result["status"],"needs_materials")
        self.assertIsNone(result["script"])

    def test_tool_failure(self):
        result = self.execute(simulate_failures={"estimate_duration":-1})["result"]
        self.assertEqual(result["status"],"incomplete")
        self.assertIsNone(result["duration"])

    def test_duration_revision_rechecked(self):
        result = self.execute()["result"]
        self.assertEqual(result["status"],"completed")
        self.assertFalse(result["previous_revisions"][0]["duration"]["passed"])
        self.assertTrue(result["duration"]["passed"])
        self.assertEqual(result["duration"]["revision"],result["rule_check"]["revision"])

    def test_impossible_duration_returns_incomplete(self):
        result = self.execute(target_seconds=1)["result"]
        self.assertEqual(result["status"],"incomplete")
        self.assertFalse(result["duration"]["passed"])

    def test_unsupported_claims_cannot_be_injected(self):
        result = self.execute(topic="字幕效率提升80%")["result"]
        self.assertEqual(result["status"],"incomplete")
        self.assertIn("unsupported_number:80%",result["rule_check"]["risks"])
        task=ScriptTask(BASE,Store())
        task.execute("search_materials",{"query":"字幕"})
        forged={"source_id":"P01","fact_id":"invented","visual":"展示素材","transition_id":"none","hold_seconds":1}
        self.assertFalse(task.execute("draft_script",{"title":"字幕功能","scenes":[forged]})["ok"])
        forged.update(fact_id="P01-F1", visual="剪辑界面特写")
        self.assertFalse(task.execute("draft_script",{"title":"字幕功能","scenes":[forged]})["ok"])

    def test_revision_invalidates_previous_checks(self):
        task=ScriptTask(BASE,Store())
        task.execute("search_materials",{"query":"字幕"})
        scene={"source_id":"P01","fact_id":"P01-F1","visual":"展示素材","transition_id":"none","hold_seconds":1}
        task.execute("draft_script",{"title":"字幕功能","scenes":[scene]})
        task.execute("estimate_duration",{})
        task.execute("check_rules",{})
        self.assertEqual(task.result()["status"],"completed")
        task.execute("draft_script",{"title":"字幕功能","scenes":[scene]})
        self.assertEqual(task.result()["status"],"incomplete")

import unittest

from xiaoying_agents.core import Store, run
from xiaoying_agents.knowledge import KnowledgeTask
from xiaoying_agents.models import MockModel


class KnowledgeTests(unittest.TestCase):
    def execute(self, **changes):
        return run(KnowledgeTask({"question":"报销期限多久", **changes},Store()),MockModel())

    def test_clear_answer_has_exact_support(self):
        result = self.execute(document_scope=["D01"])["result"]
        self.assertEqual(result["status"],"completed")
        self.assertIn("30天",result["answer"])
        self.assertEqual(result["citations"][0]["quote"],"报销申请须在费用发生后30天内提交。")

    def test_conflict_does_not_choose_latest(self):
        result = self.execute()["result"]
        self.assertEqual(result["status"],"conflict")
        self.assertEqual(result["conflicts"]["reimbursement_days"],["15天","30天"])
        self.assertEqual({c["document_id"] for c in result["citations"]},{"D01","D02"})

    def test_outside_knowledge_and_rewritten_query(self):
        output = self.execute(question="火星地表的温度是多少")
        self.assertEqual(output["result"]["status"],"out_of_scope")
        self.assertEqual(sum(h["action"]["tool"]=="search_documents" for h in output["trace"]),2)
        self.assertIsNone(output["result"]["answer"])

    def test_paraphrase_and_followup(self):
        for question,history in [("报账能在几天内完成",[]),("那多久要交",[{"role":"user","content":"我想问报销"}])]:
            result = self.execute(question=question,history=history,document_scope=["D01"])["result"]
            self.assertEqual(result["status"],"completed")
            self.assertIn("30天",result["answer"])

    def test_tool_failure_never_fabricates_answer(self):
        result = self.execute(simulate_failures={"read_document":-1})["result"]
        self.assertEqual(result["status"],"incomplete")
        self.assertIsNone(result["answer"])

    def test_changed_original_changes_answer(self):
        docs=[{"id":"X01","version_date":"2026-11-01","topic":"报销","title":"报销制度","text":"报销期限是7天。","facts":{"reimbursement_days":"7天"}}]
        result = self.execute(documents=docs)["result"]
        self.assertIn("7天",result["answer"])
        self.assertNotIn("30天",result["answer"])

    def test_guard_against_cherry_picking_and_unread_source(self):
        task = KnowledgeTask({"question":"报销"},Store())
        task.execute("search_documents",{"query":"报销"})
        task.execute("read_document",{"document_id":"D01"})
        self.assertFalse(task.execute("answer_from_sources",{"document_ids":["D01"]})["ok"])
        self.assertFalse(task.execute("answer_from_sources",{"document_ids":["D01","D02"]})["ok"])

    def test_inconsistent_fact_index_rejected(self):
        docs=[{"id":"X","version_date":"2026-11-01","topic":"报销","title":"报销制度","text":"报销期限是7天。","facts":{"days":"30天"}}]
        self.assertEqual(self.execute(documents=docs)["result"]["status"],"incomplete")

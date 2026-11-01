import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from xiaoying_agents.core import Store, Task, action, run


class FakeTask(Task):
    def result(self):
        return {"status": "completed"}


class CoreTests(unittest.TestCase):
    def test_concurrent_duplicates_are_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "db.sqlite3")
            Store(path).close()
            def save(_):
                store = Store(path)
                try:
                    return store.save("draft", "same-id", {"a": 1})
                finally:
                    store.close()
            with ThreadPoolExecutor(max_workers=8) as executor:
                results = list(executor.map(save, range(8)))
            self.assertTrue(all(r["ok"] for r in results))
            self.assertEqual(sum(not r["duplicate"] for r in results), 1)
            self.assertEqual(len({r["id"] for r in results}), 1)

    def test_durable_idempotency_and_conflicting_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "db.sqlite3")
            store = Store(path)
            self.assertFalse(store.save("draft", "r", {"a": 1})["duplicate"])
            store.close()
            store = Store(path)
            self.assertTrue(store.save("draft", "r", {"a": 1})["duplicate"])
            self.assertEqual(store.save("draft", "r", {"a": 2})["error"], "idempotency_conflict")
            store.close()

    def test_infinite_model_hits_limit(self):
        class Model:
            name, real = "test", False
            def choose(self, task, history):
                return action("unknown")
        result = run(FakeTask({}, Store()), Model(), 2)
        self.assertEqual(result["result"]["status"], "incomplete")
        self.assertEqual(result["termination"], "step_limit")
        self.assertEqual(len(result["trace"]), 2)

    def test_invalid_model_reply_and_redacted_failure(self):
        class Model:
            name, real = "test", False
            def choose(self, task, history):
                raise RuntimeError("secret")
        result = run(FakeTask({}, Store()), Model())
        self.assertEqual(result["termination"], "model_error")
        self.assertNotIn("secret", str(result))

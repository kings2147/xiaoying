"""Model decisions, validated tools, durable idempotency and factual traces."""
from __future__ import annotations

import copy
import hashlib
import inspect
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class Store:
    """SQLite uniqueness + transaction: atomic retries, no duplicate durable artifacts."""

    def __init__(self, path: str = ":memory:"):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=10)
        self.db.execute("CREATE TABLE IF NOT EXISTS artifacts (kind TEXT, key TEXT, payload TEXT, PRIMARY KEY(kind,key))")
        self.db.commit()

    def save(self, kind: str, key: str, payload: dict) -> dict:
        serialized = canonical(payload)
        with self.db:
            cursor = self.db.execute("INSERT OR IGNORE INTO artifacts VALUES (?,?,?)", (kind, key, serialized))
            row = self.db.execute("SELECT payload FROM artifacts WHERE kind=? AND key=?", (kind, key)).fetchone()
            if row[0] != serialized:
                return {"ok": False, "error": "idempotency_conflict", "message": "Same request ID has different content"}
            duplicate = cursor.rowcount == 0
        return {"ok": True, "id": f"{kind}-{key}", "duplicate": duplicate, "payload": json.loads(row[0])}

    def get(self, kind: str, key: str) -> dict | None:
        row = self.db.execute("SELECT payload FROM artifacts WHERE kind=? AND key=?", (kind, key)).fetchone()
        return json.loads(row[0]) if row else None

    def close(self):
        self.db.close()

    def checkpoint(self, key: str, payload: dict):
        """Mutable execution checkpoint, separate from immutable deliverable artifacts."""
        with self.db:
            self.db.execute("INSERT INTO artifacts VALUES ('checkpoint',?,?) ON CONFLICT(kind,key) DO UPDATE SET payload=excluded.payload",
                            (key, canonical(payload)))


@dataclass
class Tool:
    function: Callable
    description: str

    def specification(self) -> dict:
        signature = inspect.signature(self.function)
        return {"description": self.description, "arguments": {name: str(p.annotation) for name, p in signature.parameters.items()},
                "required": [name for name, p in signature.parameters.items() if p.default is inspect.Parameter.empty]}

    def call(self, arguments: dict) -> dict:
        inspect.signature(self.function).bind(**arguments)
        return self.function(**arguments)


class Task:
    name = "base"
    instructions = ""

    def __init__(self, request: dict, store: Store):
        self.request = copy.deepcopy(request)
        self.store = store
        self.tools: dict[str, Tool] = {}
        self.errors: list[dict] = []
        self._failure_counts: dict[str, int] = {}

    def tool(self, name: str, function: Callable, description: str):
        self.tools[name] = Tool(function, description)

    def fail(self, tool: str):
        """Explicit, synthetic fault injection; negative count means always fail."""
        config = self.request.get("simulate_failures", {})
        limit = config.get(tool, 0)
        count = self._failure_counts.get(tool, 0)
        if limit < 0 or count < limit:
            self._failure_counts[tool] = count + 1
            raise OSError(f"synthetic {tool} failure")

    def execute(self, name: str, arguments: dict) -> dict:
        try:
            if name not in self.tools:
                raise ValueError("unknown_tool")
            self.fail(name)
            result = self.tools[name].call(arguments)
            if not isinstance(result, dict):
                raise ValueError("tool returned a non-object")
            return result
        except (ValueError, TypeError, KeyError, OSError, sqlite3.Error) as exc:
            result = {"ok": False, "error": type(exc).__name__, "message": str(exc)[:300]}
            self.errors.append({"tool": name, **result})
            return result

    def context(self) -> dict:
        return {}

    def result(self) -> dict:
        raise NotImplementedError

    def mock_action(self, history: list[dict]) -> dict:
        raise NotImplementedError


def action(tool: str, arguments: dict | None = None, reason: str = "") -> dict:
    return {"tool": tool, "arguments": arguments or {}, "reason": reason}


def run(task: Task, model, max_steps: int = 16) -> dict:
    if not 1 <= max_steps <= 64:
        raise ValueError("max_steps must be between 1 and 64")
    history: list[dict] = []
    termination = "step_limit"
    model_error = None
    for step in range(1, max_steps + 1):
        try:
            choice = model.choose(task, copy.deepcopy(history))
            if not isinstance(choice, dict) or set(choice) != {"tool", "arguments", "reason"}:
                raise ValueError("decision must contain exactly tool, arguments, reason")
            if not isinstance(choice["arguments"], dict) or not isinstance(choice["reason"], str) or not isinstance(choice["tool"], str):
                raise ValueError("invalid action types")
            if choice["tool"] == "finish":
                history.append({"step": step, "action": choice, "observation": {"ok": True, "message": "finish requested"}})
                termination = "model_finished"
                break
            observation = task.execute(choice["tool"], choice["arguments"])
            history.append({"step": step, "action": choice, "observation": observation})
        except Exception as exc:
            # Provider messages are intentionally redacted (HTTP bodies may echo secrets).
            model_error = type(exc).__name__
            termination = "model_error"
            break
    result = task.result()
    if termination != "model_finished":
        result["status"] = "incomplete"
        result["incomplete_reason"] = termination
    return {"task": task.name, "provider": model.name, "real_model": model.real,
            "termination": termination, "model_error": model_error,
            "input": task.request, "result": result, "trace": history}

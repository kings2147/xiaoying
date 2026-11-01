from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import Store, run
from .models import make_model


def get_task(name):
    if name == "media":
        from .media import MediaTask
        return MediaTask
    if name == "planning":
        from .planning import PlanningTask
        return PlanningTask
    if name == "knowledge":
        from .knowledge import KnowledgeTask
        return KnowledgeTask
    raise ValueError(f"Unknown task: {name}")


def main():
    parser = argparse.ArgumentParser(description="Run a bounded content agent; JSON input/output and factual Trace")
    parser.add_argument("task", choices=["media", "planning", "knowledge"])
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--provider", choices=["mock", "codex", "openai"], default="mock")
    parser.add_argument("--state", default=".runtime/state.sqlite3")
    parser.add_argument("--max-steps", type=int, default=16)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    store = None
    try:
        request = json.loads(args.input.read_text(encoding="utf-8-sig"))
        if not isinstance(request, dict):
            raise ValueError("input must be a JSON object")
        store = Store(args.state)
        result = run(get_task(args.task)(request, store), make_model(args.provider), args.max_steps)
        text = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
        return 0 if result["result"]["status"] in {"completed", "awaiting_confirmation", "needs_information", "needs_materials", "blocked", "partial", "conflict", "out_of_scope"} else 1
    except Exception as exc:
        print(json.dumps({"status": "error", "error_type": type(exc).__name__, "message": "Check input, environment, or provider configuration"}))
        return 2
    finally:
        if store:
            store.close()

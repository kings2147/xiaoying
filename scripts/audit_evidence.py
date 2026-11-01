"""Replay recorded actions against actual tools without invoking a model/network."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from xiaoying_agents.cli import get_task
from xiaoying_agents.core import Store, canonical, run


class Replay:
    name = "replay"
    real = False

    def __init__(self, output):
        self.actions = iter(step["action"] for step in output["trace"])

    def choose(self, task, history):
        return next(self.actions)


def replay(output, store):
    return run(get_task(output["task"])(output["input"], store), Replay(output))


def check(output, path, store):
    replayed = replay(output, store)
    errors = []
    for key in ["trace", "result", "termination"]:
        if canonical(replayed[key]) != canonical(output[key]):
            errors.append("replayed_" + key + "_mismatch")
    if output["real_model"] != (output["provider"] == "codex" or output["provider"] == "openai"):
        errors.append("provider_provenance_mismatch")
    if output["termination"] != "model_finished":
        errors.append("execution_did_not_finish")
    result = output["result"]
    if result["status"] == "completed":
        if output["task"] == "media" and (not result["draft"] or result["publication_status"] != "not_published"):
            errors.append("media_artifact_invalid")
        if output["task"] == "planning" and (not result["saved_plan"] or result["total_cost"] > output["input"]["budget"]):
            errors.append("plan_budget_or_artifact_invalid")
        if output["task"] == "knowledge" and not result["citations"]:
            errors.append("answer_without_citations")
        if output["task"] == "script":
            if not result["rule_check"]["passed"] or not result["duration"]["passed"] or result["duration"]["revision"] != result["script"]["revision"]:
                errors.append("unchecked_script")
            if result["duration"]["total_seconds"] != sum(s["seconds"] for s in result["duration"]["scenes"]):
                errors.append("scene_duration_sum_invalid")
    if output["task"] == "knowledge" and result["status"] == "conflict" and (len(result["citations"]) < 2 or not result["gaps"]):
        errors.append("conflict_without_evidence_or_clarification")
    return {"file": path.relative_to(ROOT).as_posix(), "passed": not errors, "errors": errors}


def main():
    report = {"audited_at_utc": datetime.now(timezone.utc).isoformat(), "method": "recorded actions replayed against current real business tools; no model called", "files": []}
    for task in ["media", "planning", "knowledge", "script"]:
        folder = ROOT / "examples" / task
        for path in sorted(folder.glob("*.json")):
            output = json.loads(path.read_text(encoding="utf-8"))
            if "trace" not in output:
                continue
            store = Store()
            if path.name.startswith("duplicate."):
                original = folder / path.name.replace("duplicate.", "normal.")
                replay(json.loads(original.read_text(encoding="utf-8")), store)
            report["files"].append(check(output, path, store))
            store.close()
    report["passed"] = bool(report["files"]) and all(item["passed"] for item in report["files"])
    (ROOT / "examples/evidence_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"files": len(report["files"]), "passed": report["passed"], "failures": [item for item in report["files"] if not item["passed"]]}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

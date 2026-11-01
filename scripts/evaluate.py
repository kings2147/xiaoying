"""Reproduce real executions and store outputs, traces, assertions and test reports."""
from __future__ import annotations

import argparse
import io
import json
import platform
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from xiaoying_agents.cli import get_task
from xiaoying_agents.core import Store, run
from xiaoying_agents.models import make_model


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("task")
    parser.add_argument("--provider", choices=["mock", "codex", "openai"], default="mock")
    parser.add_argument("--cases", nargs="*")
    parser.add_argument("--tests", action="store_true")
    parser.add_argument("--merge", action="store_true", help="Keep earlier case evidence when rerunning selected cases")
    args = parser.parse_args()
    started = time.monotonic()
    folder = ROOT / "examples" / args.task
    expectations = json.loads((folder / "expectations.json").read_text(encoding="utf-8"))
    cases = args.cases or list(expectations)
    model = make_model(args.provider)
    report_path = folder / f"evaluation.{args.provider}.json"
    previous = json.loads(report_path.read_text(encoding="utf-8")) if args.merge and report_path.exists() else {}
    report = {"provider": args.provider, "real_model": model.real, "python": platform.python_version(),
              "executed_at_utc": datetime.now(timezone.utc).isoformat(), "cases": previous.get("cases", [])}
    for previous_case in report["cases"]:
        previous_case.setdefault("report_started_at_utc", previous.get("executed_at_utc"))
    for case in cases:
        request = json.loads((folder / f"{case}.input.json").read_text(encoding="utf-8"))
        store = Store()
        output = run(get_task(args.task)(request, store), model)
        write(folder / f"{case}.{args.provider}.json", output)
        entry = {"case": case, "expected": expectations[case], "actual": output["result"]["status"],
                 "termination": output["termination"], "steps": len(output["trace"]), "report_started_at_utc": report["executed_at_utc"]}
        entry["passed"] = entry["actual"] == entry["expected"] and entry["termination"] == "model_finished"
        if args.task in {"media", "planning"} and case == "normal":
            repeated = run(get_task(args.task)(request, store), model)
            write(folder / f"duplicate.{args.provider}.json", repeated)
            artifact = repeated["result"].get("draft") or repeated["result"].get("saved_plan")
            entry["duplicate_passed"] = bool(artifact and artifact["duplicate"])
            entry["passed"] &= entry["duplicate_passed"]
        report["cases"] = [prior for prior in report["cases"] if prior["case"] != case] + [entry]
        store.close()
        print(json.dumps(entry, ensure_ascii=False), flush=True)
    if args.tests:
        stream = io.StringIO()
        suite = unittest.defaultTestLoader.loadTestsFromNames(["tests.test_core", f"tests.test_{args.task}"])
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
        (folder / "tests.txt").write_text(stream.getvalue(), encoding="utf-8")
        report["tests"] = {"run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "passed": result.wasSuccessful()}
    report["passed"] = all(e["passed"] for e in report["cases"]) and report.get("tests", {}).get("passed", True)
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["elapsed_seconds"] = round(time.monotonic() - started, 3)
    write(report_path, report)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

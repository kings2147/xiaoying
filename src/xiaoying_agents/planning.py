from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta
from pathlib import Path

from .core import Task, action, fingerprint


class PlanningTask(Task):
    name = "planning"
    instructions = (
        "Required: request_id, topic, finite nonnegative budget, start_at and deadline with timezones. "
        "search_assets(topic), estimate_plan(package), generate_script(package), save_plan(package). "
        "Start with premium to evaluate quality; if over budget/deadline choose lean, then basic, re-estimating before generation. "
        "Use only feasible packages. A generation failure may retry once or choose another feasible package. "
        "Preserve successful assets/estimates/scripts (context may contain checkpoint state). Reuse them instead of repeating. "
        "No feasible package: finish incomplete with gap. Saving failure: retry once or finish. "
        "Tool costs are planned campaign simulation units, not real charges for exploratory calls."
    )

    def __init__(self, request, store):
        super().__init__(request, store)
        self.data = json.loads((Path(__file__).resolve().parents[2] / "data/planning.json").read_text(encoding="utf-8"))
        self.cache_key = "planning:" + fingerprint({k: v for k, v in request.items() if k != "simulate_failures"})
        cached = store.get("checkpoint", self.cache_key) or {}
        self.assets = cached.get("assets", [])
        self.estimates = cached.get("estimates", {})
        self.scripts = cached.get("scripts", {})
        self.saved = None
        self.resumed = bool(cached)
        self.tool("search_assets", self.search_assets, "Search synthetic material by query; completed results are checkpointed")
        self.tool("estimate_plan", self.estimate_plan, "Compute package's total planned cost and end time; package: premium, lean, basic")
        self.tool("generate_script", self.generate_script, "Generate script from retrieved facts for an estimated feasible package")
        self.tool("save_plan", self.save_plan, "Save complete feasible package only, idempotent by request_id")

    def missing(self):
        import math
        fields = [k for k in ("request_id", "topic", "budget", "start_at", "deadline") if self.request.get(k) is None or self.request.get(k) == ""]
        budget = self.request.get("budget")
        if isinstance(budget, bool) or not isinstance(budget, (float, int)) or not math.isfinite(budget) or budget < 0:
            fields.append("valid_budget")
        for key in ("start_at", "deadline"):
            try:
                if datetime.fromisoformat(self.request[key]).tzinfo is None:
                    fields.append(key + "_timezone")
            except (KeyError, TypeError, ValueError):
                fields.append(key + "_iso_timestamp")
        return fields

    def checkpoint(self):
        self.store.checkpoint(self.cache_key, {"assets": self.assets, "estimates": self.estimates, "scripts": self.scripts})

    def context(self):
        return {"missing": self.missing(), "packages": self.data["packages"], "assets": self.assets,
                "estimates": self.estimates, "scripts": self.scripts, "saved": self.saved, "resumed": self.resumed}

    def search_assets(self, query: str):
        if self.missing():
            raise ValueError("required input missing or invalid")
        self.assets = [a for a in self.data["assets"] if any(k.casefold() in query.casefold() for k in a["keywords"])]
        self.checkpoint()
        return {"ok": bool(self.assets), "assets": self.assets, "error": None if self.assets else "no_materials"}

    def estimate_plan(self, package: str):
        if self.missing() or not self.assets:
            raise ValueError("valid inputs and retrieved assets required")
        item = self.data["packages"][package]
        total = sum(item["costs"].values())
        finish = datetime.fromisoformat(self.request["start_at"]) + timedelta(minutes=item["minutes"])
        deadline = datetime.fromisoformat(self.request["deadline"])
        estimate = {"ok": True, "package": package, "cost_breakdown": item["costs"], "total_cost": total,
                    "minutes": item["minutes"], "end_at": finish.isoformat(), "budget_gap": max(0, total - self.request["budget"]),
                    "deadline_gap_minutes": max(0, (finish - deadline).total_seconds() / 60),
                    "feasible": total <= self.request["budget"] and finish <= deadline}
        self.estimates[package] = estimate
        self.checkpoint()
        return estimate

    def generate_script(self, package: str):
        if not self.estimates.get(package, {}).get("feasible"):
            raise ValueError("estimate a feasible package before generating")
        script = {"package": package, "text": self.request["topic"] + "：" + "；".join(a["fact"] for a in self.assets),
                  "source_ids": [a["id"] for a in self.assets]}
        self.scripts[package] = script
        self.checkpoint()
        return {"ok": True, "script": script}

    def save_plan(self, package: str):
        estimate = self.estimates.get(package, {})
        if not estimate.get("feasible") or package not in self.scripts:
            raise ValueError("feasible estimate and successful script are prerequisites")
        payload = {"topic": self.request["topic"], "budget": self.request["budget"], "deadline": self.request["deadline"],
                   "estimate": estimate, "script": self.scripts[package], "assets": self.assets,
                   "steps": [{"id": "assets", "depends_on": [], "status": "succeeded"},
                             {"id": "estimate", "depends_on": ["assets"], "status": "succeeded"},
                             {"id": "script", "depends_on": ["estimate"], "status": "succeeded"}]}
        saved = self.store.save("plan", self.request["request_id"], payload)
        if saved["ok"]:
            self.saved = saved
        return saved

    def result(self):
        missing = self.missing()
        status = "needs_information" if missing else "completed" if self.saved else "incomplete"
        feasible = [e for e in self.estimates.values() if e["feasible"]]
        reason = None
        if not missing and not self.saved:
            reason = "tool_failure" if self.errors else "no_feasible_plan" if self.estimates and not feasible else "unfinished_steps"
        return {"status": status, "missing": missing, "incomplete_reason": reason, "assets": self.assets,
                "estimates": self.estimates, "successful_scripts": self.scripts, "saved_plan": self.saved,
                "total_cost": self.saved["payload"]["estimate"]["total_cost"] if self.saved else None,
                "resumed_from_checkpoint": self.resumed, "errors": self.errors}

    def mock_action(self, history):
        if self.missing() or self.saved:
            return action("finish", reason="Clarification needed or saved successfully")
        if not self.assets:
            if history:
                return action("finish", reason="No assets or search failed")
            return action("search_assets", {"query": self.request["topic"]}, "Retrieve campaign assets")
        for package in self.data["packages"]:
            if package not in self.estimates:
                return action("estimate_plan", {"package": package}, "Evaluate quality/cost/deadline")
            if self.estimates[package]["feasible"]:
                if package not in self.scripts:
                    attempts = sum(h["action"]["tool"] == "generate_script" and h["action"]["arguments"].get("package") == package for h in history)
                    if attempts >= 2:
                        continue
                    return action("generate_script", {"package": package}, "Generate within observed constraints")
                saves = sum(h["action"]["tool"] == "save_plan" for h in history)
                if saves < 2:
                    return action("save_plan", {"package": package}, "Preserve successful results and save")
                return action("finish", reason="Save failed repeatedly")
        return action("finish", reason="No feasible package remains; report actual gap")

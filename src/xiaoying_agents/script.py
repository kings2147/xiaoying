from __future__ import annotations

import copy
import json
import math
import re
from pathlib import Path

from .core import Task, action


class ScriptTask(Task):
    name = "script"
    instructions = (
        "Required topic,audience,platform,target_seconds,style. Search materials for topic. Empty results: rewrite once or stop for materials. "
        "Create editable scenes via draft_script(title, scenes). title must be topic or topic+'｜功能演示'. Each scene has exactly "
        "source_id,fact_id,visual,transition_id,hold_seconds. Use retrieved facts and allowed visuals/transitions from context. "
        "Narration is compiled from the selected transition + exact fact to keep factual support. "
        "Initial draft: prefer three scenes with opening/detail/closing transitions and 8-second holds to evaluate a detailed version. "
        "Then estimate_duration and check_rules. Observe duration: if over target, shorten holds, remove transitions or scenes, "
        "call draft_script again and rerun BOTH checks. Do not finish completed without current-version passing checks. "
        "No feasible minimum duration or missing facts: stop and disclose limits; tool failure retry once or stop. "
        "Facts like efficiency percentages may not be invented."
    )

    def __init__(self, request, store):
        super().__init__(request, store)
        self.data = json.loads((Path(__file__).resolve().parents[2] / "data/script.json").read_text(encoding="utf-8"))
        if "materials" in request:
            self.data["materials"] = request["materials"]
        self.materials = {}
        self.searches = []
        self.draft = None
        self.duration = None
        self.rules = None
        self.revisions = []
        self.tool("search_materials", self.search_materials, "Search synthetic product facts using a concise query")
        self.tool("draft_script", self.draft_script, "Model selects title and ordered scenes; resets checks for each revision")
        self.tool("estimate_duration", self.estimate_duration, "Estimate current draft's scene and total duration; compare target")
        self.tool("check_rules", self.check_rules, "Check current draft's citations, allowed text and brand rules")

    def missing(self):
        fields = [key for key in ("topic", "audience", "platform", "target_seconds", "style") if self.request.get(key) is None or self.request.get(key) == ""]
        seconds = self.request.get("target_seconds")
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or not 1 <= seconds <= 300:
            fields.append("valid_target_seconds_1_to_300")
        return fields

    def context(self):
        return {"missing": self.missing(), "materials": self.materials, "transitions": self.data["transitions"],
                "allowed_visuals": self.data["visuals"], "draft": self.draft, "duration": self.duration,
                "rules": self.rules, "revision_count": len(self.revisions)}

    def search_materials(self, query: str):
        if self.missing():
            raise ValueError("missing or invalid key input")
        matches = [m for m in self.data["materials"] if any(k.casefold() in query.casefold() for k in m["keywords"])]
        self.materials.update({m["id"]: m for m in matches})
        self.searches.append(query)
        return {"ok": True, "materials": matches}

    def draft_script(self, title: str, scenes: list):
        if self.missing() or not self.materials:
            raise ValueError("valid inputs and retrieved facts required")
        if title not in [self.request["topic"], self.request["topic"] + "｜功能演示"]:
            raise ValueError("title must use the requested topic without invented claims")
        if not isinstance(scenes, list) or not 1 <= len(scenes) <= 6:
            raise ValueError("provide 1 to 6 scenes")
        built = []
        for index, scene in enumerate(scenes, 1):
            if set(scene) != {"source_id", "fact_id", "visual", "transition_id", "hold_seconds"}:
                raise ValueError("scene fields do not match specification")
            source = self.materials[scene["source_id"]]
            facts = {f["id"]: f["text"] for f in source["facts"]}
            text = facts[scene["fact_id"]]
            transition = self.data["transitions"][scene["transition_id"]]
            hold = scene["hold_seconds"]
            if isinstance(hold, bool) or not isinstance(hold, (int, float)) or not math.isfinite(hold) or not 1 <= hold <= 15:
                raise ValueError("hold_seconds must be finite and between 1 and 15")
            if scene["visual"] not in self.data["source_visuals"].get(source["id"], ["展示素材", "片尾卡片"]):
                raise ValueError("visual must be supported by this source's storyboard actions")
            built.append({"scene": index, **scene, "narration": transition + text + "。", "fact_quote": text})
        if self.draft:
            self.revisions.append({"draft": copy.deepcopy(self.draft), "duration": self.duration, "rules": self.rules})
        self.draft = {"revision": len(self.revisions) + 1, "title": title, "scenes": built,
                      "audience": self.request["audience"], "platform": self.request["platform"], "style": self.request["style"]}
        self.duration = None
        self.rules = None
        return {"ok": True, "draft": self.draft, "checks_invalidated": True}

    def estimate_duration(self):
        if not self.draft:
            raise ValueError("draft a script first")
        timings = []
        for scene in self.draft["scenes"]:
            characters = len(re.sub(r"\W", "", scene["narration"]))
            seconds = math.ceil(characters / self.data["speech_characters_per_second"]) + scene["hold_seconds"]
            timings.append({"scene": scene["scene"], "seconds": seconds, "source_id": scene["source_id"]})
        total = sum(s["seconds"] for s in timings)
        self.duration = {"revision": self.draft["revision"], "scenes": timings, "total_seconds": total,
                         "target_seconds": self.request["target_seconds"], "passed": total <= self.request["target_seconds"]}
        return {"ok": True, **self.duration}

    def check_rules(self):
        if not self.draft:
            raise ValueError("draft a script first")
        text = self.draft["title"] + " ".join(s["narration"] for s in self.draft["scenes"])
        risks = [term for term in self.data["forbidden_terms"] if term in text]
        supported = " ".join(f["text"] for m in self.materials.values() for f in m["facts"])
        for number in re.findall(r"\d+(?:\.\d+)?%?", text):
            if number not in supported:
                risks.append("unsupported_number:" + number)
        self.rules = {"revision": self.draft["revision"], "passed": not risks, "risks": risks,
                      "citations": [{"source_id": s["source_id"], "fact_id": s["fact_id"], "quote": s["fact_quote"]} for s in self.draft["scenes"]]}
        return {"ok": True, **self.rules}

    def result(self):
        missing = self.missing()
        passed = bool(self.draft and self.duration and self.rules and self.duration["passed"] and self.rules["passed"])
        status = "needs_information" if missing else "completed" if passed else "needs_materials" if self.searches and not self.materials else "incomplete"
        return {"status": status, "missing": missing, "script": self.draft, "duration": self.duration,
                "rule_check": self.rules, "previous_revisions": self.revisions, "errors": self.errors,
                "incomplete_reason": None if passed else "missing inputs/materials, failed tools, or current draft checks not passing"}

    def mock_action(self, history):
        if self.missing():
            return action("finish", reason="Missing required script brief")
        if not self.materials:
            if len(self.searches) >= 2 or (history and not history[-1]["observation"].get("ok")):
                return action("finish", reason="No supported facts or failed retrieval")
            query = self.request["topic"] if not self.searches else self.request["topic"] + " 产品功能"
            return action("search_materials", {"query": query}, "Retrieve product facts")
        if not self.draft:
            source = next(iter(self.materials.values()))
            fact = source["facts"][0]
            scenes = [{"source_id": source["id"], "fact_id": fact["id"], "visual": "展示素材", "transition_id": transition, "hold_seconds": 8}
                      for transition in ["opening", "detail", "closing"]]
            return action("draft_script", {"title": self.request["topic"], "scenes": scenes}, "Construct initial detailed storyboard using sourced facts")
        for tool, result in [("estimate_duration", self.duration), ("check_rules", self.rules)]:
            if result is None:
                attempts = sum(h["action"]["tool"] == tool for h in history[-3:])
                if attempts >= 2:
                    return action("finish", reason="Check tool failed repeatedly")
                return action(tool, reason="Validate the current script revision")
        if self.duration["passed"] and self.rules["passed"]:
            return action("finish", reason="Current revision passes duration and facts rules")
        if not self.revisions:
            scene = {k: v for k,v in self.draft["scenes"][0].items() if k in {"source_id","fact_id","visual","transition_id","hold_seconds"}}
            scene.update(transition_id="none", hold_seconds=1)
            return action("draft_script", {"title": self.request["topic"], "scenes": [scene]}, "Compress after observing failed duration check")
        return action("finish", reason="Minimum supported revision still cannot meet constraints")

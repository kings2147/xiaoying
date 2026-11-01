from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .core import Task, action


def time_key(value: str) -> str:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("slot must have an explicit timezone")
    return str(parsed.timestamp())


class MediaTask(Task):
    name = "media"
    instructions = (
        "For each material_id: read_material, check_rules, query_slots, then propose_slot for a returned available slot. "
        "Missing metadata or rules risks: do not propose that material. Conflict: choose a returned alternative; "
        "hard requirements require exact confirmed_changes[material_id] approval; otherwise draft remains pending_confirmation. "
        "Propose remaining valid materials before save_draft once. Only drafts, never actual publication. "
        "If required request_id/material_ids/requirements are absent finish for clarification. "
        "After a save failure retry at most once, then finish with failure."
    )

    def __init__(self, request, store):
        super().__init__(request, store)
        self.data = json.loads((Path(__file__).resolve().parents[2] / "data/media.json").read_text(encoding="utf-8"))
        self.data["materials"].update(request.get("materials", {}))
        self.items = {mid: {"material_id": mid, "review_status": "unread", "risks": [], "suggested_slot": None,
                           "pending_confirmation": False} for mid in request.get("material_ids", [])}
        self.queries = {}
        self.saved = None
        self.tool("read_material", self.read_material, "Read metadata for one requested material_id")
        self.tool("check_rules", self.check_rules, "Check completeness, rights and sensitive-content rules after reading")
        self.tool("query_slots", self.query_slots, "Find conflict and available slots after rules passed")
        self.tool("propose_slot", self.propose_slot, "Select available slot; marks unapproved hard changes pending")
        self.tool("save_draft", self.save_draft, "Persist a single idempotent draft for all proposed materials; no publication")

    def context(self):
        return {"items": self.items, "slot_queries": self.queries, "saved": self.saved}

    def read_material(self, material_id: str):
        item = self.items[material_id]
        material = self.data["materials"].get(material_id)
        item["metadata"] = material
        item["review_status"] = "read" if material else "needs_information"
        return {"ok": bool(material), "material": material, "missing": [] if material else ["material"]}

    def check_rules(self, material_id: str):
        item = self.items[material_id]
        if item["review_status"] != "read":
            raise ValueError("read material before checking rules")
        material = item["metadata"]
        missing = [k for k in ("title", "rights_cleared", "sensitive") if k not in material or material[k] is None or material[k] == ""]
        risks = []
        if material.get("rights_cleared") is not True:
            risks.append("rights_not_cleared")
        if material.get("sensitive") is not False:
            risks.append("sensitive_content_or_unknown")
        item.update(review_status="needs_information" if missing else "blocked" if risks else "approved", risks=risks, missing=missing)
        return {"ok": not missing and not risks, "review_status": item["review_status"], "risks": risks, "missing": missing}

    def query_slots(self, material_id: str):
        if self.items[material_id]["review_status"] != "approved":
            raise ValueError("material must pass rules")
        requirement = self.request.get("requirements", {}).get(material_id, {})
        if not requirement.get("slot") or not isinstance(requirement.get("hard"), bool):
            self.items[material_id]["review_status"] = "needs_information"
            return {"ok": False, "error": "missing_slot_or_hard_flag"}
        requested = requirement["slot"]
        occupied = {time_key(s) for s in self.request.get("occupied_slots", [])}
        occupied |= {time_key(i["suggested_slot"]) for mid, i in self.items.items() if mid != material_id and i["suggested_slot"]}
        slots = self.request.get("available_slots", self.data["slots"])
        available = [s for s in slots if time_key(s) not in occupied]
        result = {"ok": True, "requested_slot": requested, "conflict": time_key(requested) in occupied,
                  "available_slots": available}
        self.queries[material_id] = result
        return result

    def propose_slot(self, material_id: str, slot: str):
        item = self.items[material_id]
        query = self.queries.get(material_id)
        if item["review_status"] != "approved" or not query or slot not in query["available_slots"]:
            raise ValueError("slot must come from a successful query for an approved material")
        if any(mid != material_id and other["suggested_slot"] and time_key(other["suggested_slot"]) == time_key(slot) for mid, other in self.items.items()):
            raise ValueError("slot conflicts with another proposed material")
        requirement = self.request["requirements"][material_id]
        changed = time_key(slot) != time_key(requirement["slot"])
        confirmed = self.request.get("confirmed_changes", {}).get(material_id)
        pending = bool(changed and requirement["hard"] and (not confirmed or time_key(confirmed) != time_key(slot)))
        item.update(suggested_slot=slot, pending_confirmation=pending)
        return {"ok": True, "suggested_slot": slot, "pending_confirmation": pending, "state": "draft_proposal"}

    def save_draft(self):
        if not self.request.get("request_id"):
            raise ValueError("request_id required for idempotency")
        if not any(i["suggested_slot"] for i in self.items.values()):
            raise ValueError("no valid proposal to save")
        if any(i["review_status"] in {"unread", "read"} or (i["review_status"] == "approved" and not i["suggested_slot"]) for i in self.items.values()):
            raise ValueError("review/propose all requested materials before saving")
        payload = {"state": "draft", "items": list(self.items.values())}
        result = self.store.save("media", self.request["request_id"], payload)
        if result["ok"]:
            self.saved = result
        return result

    def result(self):
        missing = [k for k in ("request_id", "material_ids", "requirements") if not self.request.get(k)]
        items = list(self.items.values())
        if missing or any(i["review_status"] == "needs_information" for i in items):
            status = "needs_information"
        elif self.saved:
            status = "awaiting_confirmation" if any(i["pending_confirmation"] for i in items) else "completed"
            if any(i["review_status"] == "blocked" for i in items):
                status = "partial"
        elif any(i["review_status"] == "blocked" for i in items):
            status = "blocked"
        elif any(e["tool"] == "save_draft" for e in self.errors):
            status = "failed"
        else:
            status = "incomplete"
        return {"status": status, "items": items, "missing": missing, "draft": self.saved,
                "publication_status": "not_published", "errors": self.errors}

    def mock_action(self, history):
        if self.result()["missing"]:
            return action("finish", reason="Required input missing")
        for mid, item in self.items.items():
            if item["review_status"] == "unread":
                return action("read_material", {"material_id": mid}, "Read supplied material")
            if item["review_status"] == "read":
                return action("check_rules", {"material_id": mid}, "Check observed metadata")
            if item["review_status"] == "approved" and not item["suggested_slot"]:
                if mid not in self.queries:
                    if history and history[-1]["action"]["tool"] == "query_slots" and not history[-1]["observation"]["ok"]:
                        return action("finish", reason="Slot query failed")
                    return action("query_slots", {"material_id": mid}, "Look up availability")
                query = self.queries[mid]
                slots = query["available_slots"]
                if not slots:
                    return action("finish", reason="No available slot")
                requested = query["requested_slot"]
                slot = requested if requested in slots else slots[0]
                return action("propose_slot", {"material_id": mid, "slot": slot}, "Use available slot; preserve confirmation boundary")
        attempts = sum(h["action"]["tool"] == "save_draft" for h in history)
        if any(i["suggested_slot"] for i in self.items.values()) and not self.saved and attempts < 2:
            return action("save_draft", reason="Save reviewed proposals idempotently")
        return action("finish", reason="Return actual draft or unresolved state")

from __future__ import annotations

import json
import re
from pathlib import Path

from .core import Task, action


def normalize(text):
    text = text.casefold()
    for term in ["报账", "报支", "费用申请", "费用报账"]:
        text = text.replace(term, "报销")
    for term in ["多久", "几天", "多长时间", "有效期"]:
        text = text.replace(term, "期限")
    return re.sub(r"\W", "", text)


class KnowledgeTask(Task):
    name = "knowledge"
    instructions = (
        "Answer questions using synthetic policy sources only. Tools: search_documents(query), read_document(document_id), "
        "answer_from_sources(document_ids). A question may be a follow-up: use prior user history to resolve the topic. "
        "Search a concise topic (e.g. 报销) and if no results rewrite the query once; then stop for missing sources. "
        "Read ALL returned relevant documents before answer_from_sources; conflicting values require clarification, "
        "never choose by date alone without applicability/priority evidence. answer_from_sources constructs cited text and conflict state. "
        "On tool failure retry once or stop; do not invent an answer."
    )

    def __init__(self, request, store):
        super().__init__(request, store)
        docs = request.get("documents")
        if docs is None:
            docs = json.loads((Path(__file__).resolve().parents[2] / "data/knowledge.json").read_text(encoding="utf-8"))
        scope = request.get("document_scope")
        self.documents = {d["id"]: d for d in docs if scope is None or d["id"] in scope}
        self.candidates = {}
        self.read = {}
        self.searches = []
        self.answer = None
        self.tool("search_documents", self.search_documents, "Search all in-scope documents with Chinese lexical/synonym retrieval")
        self.tool("read_document", self.read_document, "Read exact original text and version for a retrieved document_id")
        self.tool("answer_from_sources", self.answer_from_sources, "Build supported answer/conflict with exact quotes from ALL retrieved sources")

    def context(self):
        return {"retrieved": self.candidates, "read": self.read, "searches": self.searches, "answer": self.answer}

    def query_context(self):
        history = self.request.get("history", [])
        return " ".join(str(h.get("content", "")) for h in history if h.get("role") == "user") + " " + self.request.get("question", "")

    def search_documents(self, query: str):
        if not self.request.get("question") or not query.strip():
            raise ValueError("question and nonempty query required")
        normalized = normalize(query)
        grams = {normalized[i:i+2] for i in range(max(0, len(normalized)-1))}
        matches = []
        for document in self.documents.values():
            text = normalize(document["title"] + document["topic"] + document["text"])
            score = sum(g in text for g in grams)
            if score:
                summary = {"id": document["id"], "version_date": document["version_date"], "title": document["title"], "score": score}
                self.candidates[document["id"]] = summary
                matches.append(summary)
        matches.sort(key=lambda d: (-d["score"], d["id"]))
        self.searches.append({"query": query, "matches": len(matches)})
        return {"ok": True, "matches": matches}

    def read_document(self, document_id: str):
        if document_id not in self.candidates:
            raise ValueError("retrieve source before reading")
        document = self.documents[document_id]
        if any(str(value) not in document["text"] for value in document.get("facts", {}).values()):
            raise ValueError("corpus fact index inconsistent with original text; repair data")
        self.read[document_id] = document
        return {"ok": True, "document": document}

    def answer_from_sources(self, document_ids: list):
        if not document_ids or set(document_ids) != set(self.candidates) or not set(document_ids) <= set(self.read):
            raise ValueError("read and cite all retrieved relevant sources before answering")
        sources = [self.read[k] for k in dict.fromkeys(document_ids)]
        values = {}
        for document in sources:
            for key, value in document.get("facts", {}).items():
                values.setdefault(key, set()).add(str(value))
        conflicts = {key: sorted(value) for key, value in values.items() if len(value) > 1}
        citations = [{"document_id": d["id"], "version_date": d["version_date"], "quote": d["text"]} for d in sources]
        self.answer = {"status": "conflict" if conflicts else "completed",
                       "answer": "；".join(f"{d['id']}（{d['version_date']}）：{d['text']}" for d in sources),
                       "citations": citations, "conflicts": conflicts,
                       "gaps": ["请确认适用制度范围或明确的优先级；日期本身不构成适用依据。"] if conflicts else []}
        return {"ok": True, **self.answer}

    def result(self):
        if self.answer:
            return {**self.answer, "errors": self.errors}
        status = "needs_information" if not self.request.get("question") else "incomplete" if self.errors or self.candidates else "out_of_scope" if self.searches else "incomplete"
        return {"status": status, "answer": None, "citations": [], "conflicts": {},
                "gaps": ["工具读取失败或资料未读全" if self.errors or self.candidates else "需要问题或相关资料"], "errors": self.errors}

    def mock_action(self, history):
        if not self.request.get("question") or self.answer:
            return action("finish", reason="Answer constructed or question missing")
        if not self.searches:
            if history:
                return action("finish", reason="Search tool failed")
            return action("search_documents", {"query": self.query_context()}, "Search with dialogue context")
        if not self.candidates:
            if len(self.searches) < 2:
                return action("search_documents", {"query": normalize(self.query_context())}, "Rewrite empty retrieval query")
            return action("finish", reason="No supporting sources")
        for document_id in self.candidates:
            if document_id not in self.read:
                attempts = sum(h["action"]["tool"] == "read_document" and h["action"]["arguments"].get("document_id") == document_id for h in history)
                if attempts >= 2:
                    return action("finish", reason="Source read failed; no unsupported answer")
                return action("read_document", {"document_id": document_id}, "Verify original text and version")
        return action("answer_from_sources", {"document_ids": list(self.candidates)}, "Cite all read sources and disclose conflicting values")

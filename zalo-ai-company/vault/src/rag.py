"""Company Vault RAG (PR-004). Ingest + retrieve tài liệu nội bộ.

DRY-RUN offline: chunk + retriever keyword (TF overlap) — chạy được KHÔNG cần API.
Nâng cấp embeddings/Google Drive cần env (GOOGLE_DRIVE_*, OPENAI_API_KEY...) → PR-004 permission.
Thuần stdlib, không network.
"""
from __future__ import annotations

import re
from typing import Dict, List, Mapping, Optional

_WORD = re.compile(r"\w+", re.UNICODE)


def _tok(s: str) -> List[str]:
    return [w.lower() for w in _WORD.findall(s or "")]


def chunk(text: str, size: int = 400, overlap: int = 40) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    out, i = [], 0
    while i < len(text):
        out.append(text[i:i + size])
        i += max(1, size - overlap)
    return out


class Vault:
    def __init__(self, env: Optional[Mapping[str, str]] = None):
        self.env = env or {}
        self._docs: Dict[str, Dict] = {}        # doc_id -> {meta, chunks:[{text,tokens}]}

    # ---- capability gating ----
    def embeddings_enabled(self) -> bool:
        return bool(self.env.get("OPENAI_API_KEY") or self.env.get("VERTEX_MODEL"))

    def drive_enabled(self) -> bool:
        return bool(self.env.get("GOOGLE_DRIVE_TOKEN") or self.env.get("GDRIVE_OAUTH"))

    def health(self) -> Dict:
        return {"docs": len(self._docs),
                "retriever": "embeddings" if self.embeddings_enabled() else "keyword(dry-run)",
                "drive": self.drive_enabled(),
                "missing_for_upgrade": [] if self.embeddings_enabled() else ["OPENAI_API_KEY|VERTEX_MODEL"]}

    # ---- ingest / search ----
    def ingest(self, doc_id: str, text: str, meta: Optional[Dict] = None) -> Dict:
        chunks = [{"text": c, "tokens": _tok(c)} for c in chunk(text)]
        self._docs[doc_id] = {"meta": meta or {}, "chunks": chunks}
        return {"doc_id": doc_id, "chunks": len(chunks)}

    def search(self, query: str, k: int = 3) -> List[Dict]:
        q = set(_tok(query))
        if not q:
            return []
        scored = []
        for doc_id, d in self._docs.items():
            for idx, ch in enumerate(d["chunks"]):
                overlap = len(q & set(ch["tokens"]))
                if overlap:
                    score = overlap / (len(q) or 1)
                    scored.append({"doc_id": doc_id, "chunk": idx,
                                   "score": round(score, 4), "text": ch["text"][:200]})
        scored.sort(key=lambda r: r["score"], reverse=True)
        return scored[:k]

"""Build a deterministic audit view of relationship evidence.

This file reports what the repository has reviewed. It does not treat a deep
URL as proof that the cited page entails the relationship claim.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
REL_PATH = ROOT / "data" / "relations.json"
SOURCE_REGISTER_PATH = ROOT / "data" / "source_register.json"
OUT_PATH = ROOT / "data" / "evidence_manifest.json"


def url_scope(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    if not path:
        return "domain"
    if path in {"/report", "/reports", "/news", "/search", "/content"}:
        return "channel"
    return "deep_link"


def _local_note_path(note: str | None) -> tuple[str | None, str | None, bool]:
    prefix = "本地研究摘要："
    if not note or prefix not in note:
        return None, None, False
    value = note.split(prefix, 1)[1]
    path, _, fragment = value.partition("#")
    return path, fragment or None, (ROOT / path).exists()


def build() -> dict:
    rel_doc = json.loads(REL_PATH.read_text(encoding="utf-8"))
    source_doc = json.loads(SOURCE_REGISTER_PATH.read_text(encoding="utf-8"))
    source_by_url = {item["url"]: item for item in source_doc.get("sources", [])}
    rows = []

    for rel in rel_doc["relations"]:
        support = rel["claim_support"]
        for index, evidence in enumerate(rel.get("evidence", []), start=1):
            registered = source_by_url.get(evidence["url"])
            local_path, local_fragment, local_exists = _local_note_path(evidence.get("note"))
            locator = evidence.get("evidence_locator", "")
            rows.append({
                "relationship_id": rel["relationship_id"],
                "evidence_index": index,
                "claim_support": support,
                "relevance_tier": rel["relevance_tier"],
                "source_type": evidence["source_type"],
                "source_name": evidence["source_name"],
                "url": evidence["url"],
                "url_scope": url_scope(evidence["url"]),
                "publisher": registered.get("publisher") if registered else None,
                "source_id": registered.get("source_id") if registered else None,
                "registry_source_type": registered.get("source_type") if registered else None,
                "source_type_matches_registry": (
                    evidence["source_type"] == registered.get("source_type")
                    if registered else False
                ),
                "access_status": (
                    registered.get("access_status") or registered.get("verification_status")
                    if registered else "unregistered"
                ),
                "last_checked": (
                    registered.get("last_checked") or source_doc.get("verified_at")
                    if registered else None
                ),
                "registry_review_note": registered.get("note") if registered else None,
                "published_date": evidence.get("published_date"),
                "retrieved_date": evidence.get("retrieved_date"),
                "origin_id": evidence.get("origin_id"),
                "evidence_locator": locator,
                "locator_specific": any(token in locator for token in ("p.", "pp.", "表", "检索", "正文", "章节", "公告")),
                "local_research_note": local_path,
                "local_fragment": local_fragment,
                "local_research_note_exists": local_exists,
                "content_review_status": {
                    "direct": "claim_directly_supported",
                    "indirect": "claim_supported_with_stated_inference",
                    "unsupported": "candidate_only_not_supported",
                    "conflicted": "unresolved_conflict",
                }[support],
            })

    summary = {
        "total_evidence_refs": len(rows),
        "registered_source_refs": sum(row["source_id"] is not None for row in rows),
        "unregistered_source_refs": sum(row["source_id"] is None for row in rows),
        "source_type_mismatch_refs": sum(not row["source_type_matches_registry"] for row in rows),
        "specific_locator_refs": sum(row["locator_specific"] for row in rows),
        "local_research_note_missing": sum(not row["local_research_note_exists"] for row in rows),
        "direct_support_refs": sum(row["claim_support"] == "direct" for row in rows),
        "indirect_support_refs": sum(row["claim_support"] == "indirect" for row in rows),
        "candidate_only_refs": sum(row["claim_support"] == "unsupported" for row in rows),
    }
    return {
        "as_of": rel_doc.get("as_of"),
        "generated_from": "data/relations.json",
        "source_register": "data/source_register.json",
        "interpretation": "URL depth and registration are traceability checks, not claim-verification substitutes.",
        "summary": summary,
        "evidence": rows,
    }


def main() -> int:
    OUT_PATH.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(build()["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

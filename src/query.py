"""Shared relation-query semantics for the CLI and HTTP API."""
from __future__ import annotations

from datetime import date
from typing import Any, Iterable

RELATION_TYPES = (
    "supplier",
    "customer",
    "partner",
    "investor_or_investee",
    "peer",
)
TIERS = ("core", "supplementary", "candidate")
STATUSES = ("fact", "inference", "unknown")
SOURCE_TYPES = (
    "primary_regulatory",
    "primary_official",
    "primary_procurement",
    "authoritative_media",
    "general_media",
    "commercial_database",
    "industry_research",
)
DEFAULT_LIMIT = 100
MAX_LIMIT = 500


class QueryValidationError(ValueError):
    """A user-supplied query cannot be interpreted safely."""


def parse_date(value: str | date | None, field: str) -> date | None:
    if value is None or isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise QueryValidationError(f"{field} must be an ISO date YYYY-MM-DD") from exc


def _validate_choice(value: str | None, field: str, choices: Iterable[str]) -> None:
    if value is not None and value not in choices:
        allowed = ", ".join(choices)
        raise QueryValidationError(f"invalid {field}={value!r}; choose one of: {allowed}")


def filter_relations(
    rels: list[dict[str, Any]],
    *,
    relation_type: str | None = None,
    tier: str | None = None,
    status: str | None = None,
    needs_validation: bool | None = None,
    entity: str | None = None,
    entity_ids: Iterable[str] | None = None,
    date_from: str | date | None = None,
    date_to: str | date | None = None,
    min_confidence: float | None = None,
    include_candidates: bool = False,
) -> list[dict[str, Any]]:
    _validate_choice(relation_type, "type", RELATION_TYPES)
    _validate_choice(tier, "tier", TIERS)
    _validate_choice(status, "status", STATUSES)
    if entity is not None and entity_ids is not None and entity not in set(entity_ids):
        raise QueryValidationError(f"unknown entity={entity!r}")

    start_bound = parse_date(date_from, "date_from")
    end_bound = parse_date(date_to, "date_to")
    if start_bound and end_bound and start_bound > end_bound:
        raise QueryValidationError("date_from must be on or before date_to")
    if min_confidence is not None and not 0 <= min_confidence <= 100:
        raise QueryValidationError("min_confidence must be between 0 and 100")

    result = []
    for rel in rels:
        if relation_type and rel.get("relation_type") != relation_type:
            continue
        if tier and rel.get("relevance_tier") != tier:
            continue
        if not tier and not include_candidates and rel.get("relevance_tier") == "candidate":
            continue
        if status and rel.get("status") != status:
            continue
        if needs_validation is not None and rel.get("needs_human_validation") != needs_validation:
            continue
        if entity and entity not in (rel.get("subject_entity_id"), rel.get("object_entity_id")):
            continue
        if min_confidence is not None and rel.get("confidence_score", 0) < min_confidence:
            continue

        rel_start = parse_date(rel.get("effective_start"), "effective_start")
        rel_end = parse_date(rel.get("effective_end"), "effective_end")
        # Unknown boundaries are retained rather than silently discarded.
        if end_bound and rel_start and rel_start > end_bound:
            continue
        if start_bound and rel_end and rel_end < start_bound:
            continue
        result.append(rel)

    return sorted(result, key=lambda r: r.get("confidence_score", 0), reverse=True)


def filter_evidence(
    rels: list[dict[str, Any]],
    *,
    relationship_id: str | None = None,
    source_type: str | None = None,
) -> list[dict[str, Any]]:
    _validate_choice(source_type, "source_type", SOURCE_TYPES)
    rows = []
    for rel in rels:
        if relationship_id and rel.get("relationship_id") != relationship_id:
            continue
        for index, evidence in enumerate(rel.get("evidence", []), start=1):
            if source_type and evidence.get("source_type") != source_type:
                continue
            rows.append({
                "relationship_id": rel["relationship_id"],
                "evidence_index": index,
                "claim_support": rel.get("claim_support"),
                "relevance_tier": rel.get("relevance_tier"),
                **evidence,
            })
    return rows


def paginate(items: list[dict[str, Any]], offset: int = 0, limit: int = DEFAULT_LIMIT) -> dict[str, Any]:
    if offset < 0:
        raise QueryValidationError("offset must be >= 0")
    if limit < 1 or limit > MAX_LIMIT:
        raise QueryValidationError(f"limit must be between 1 and {MAX_LIMIT}")
    page = items[offset:offset + limit]
    next_offset = offset + limit if offset + limit < len(items) else None
    return {
        "items": page,
        "total": len(items),
        "offset": offset,
        "limit": limit,
        "next_offset": next_offset,
    }

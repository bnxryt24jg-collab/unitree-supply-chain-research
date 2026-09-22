"""Evidence-confidence scoring, kept separate from business relevance."""
from __future__ import annotations

from datetime import date

from schema import (
    ClaimSupport,
    ConfidenceBreakdown,
    Relationship,
    SourceType,
    Status,
)

AS_OF = date(2026, 9, 20)

WEIGHTS = {
    "direct_support": 0.30,
    "source_authority": 0.25,
    "independent_corroboration": 0.20,
    "entity_direction_certainty": 0.15,
    "timeliness": 0.10,
}

PRIMARY_TYPES = {
    SourceType.PRIMARY_REGULATORY,
    SourceType.PRIMARY_OFFICIAL,
    SourceType.PRIMARY_PROCUREMENT,
}
SECONDARY_TYPES = set(SourceType) - PRIMARY_TYPES


def _support_value(value: ClaimSupport) -> float:
    return {
        ClaimSupport.DIRECT: 100.0,
        ClaimSupport.INDIRECT: 70.0,
        ClaimSupport.CONFLICTED: 50.0,
        ClaimSupport.UNSUPPORTED: 20.0,
    }[value]


def _source_authority(source_type: SourceType) -> float:
    return {
        SourceType.PRIMARY_REGULATORY: 100.0,
        SourceType.PRIMARY_OFFICIAL: 95.0,
        SourceType.PRIMARY_PROCUREMENT: 95.0,
        SourceType.AUTHORITATIVE_MEDIA: 80.0,
        SourceType.GENERAL_MEDIA: 65.0,
        SourceType.COMMERCIAL_DATABASE: 60.0,
        SourceType.INDUSTRY_RESEARCH: 55.0,
    }[source_type]


def _corroboration(rel: Relationship) -> float:
    origins = {e.origin_id for e in rel.evidence}
    if len(origins) >= 3:
        return 100.0
    if len(origins) == 2:
        return 85.0
    return 50.0


def _timeliness(rel: Relationship) -> float:
    if rel.effective_end and rel.effective_end < AS_OF:
        return 40.0
    dates = [e.published_date or e.retrieved_date for e in rel.evidence]
    newest = max(dates) if dates else None
    if newest is None:
        return 50.0
    months = max(0, (AS_OF - newest).days) / 30.44
    if months <= 12:
        return 100.0
    if months <= 24:
        return 80.0
    return 60.0


def compute_confidence(rel: Relationship) -> ConfidenceBreakdown:
    direct = _support_value(rel.claim_support)
    authority = max(_source_authority(e.source_type) for e in rel.evidence)
    corroboration = _corroboration(rel)
    timeliness = _timeliness(rel)
    weighted = (
        direct * WEIGHTS["direct_support"]
        + authority * WEIGHTS["source_authority"]
        + corroboration * WEIGHTS["independent_corroboration"]
        + rel.entity_direction_certainty * WEIGHTS["entity_direction_certainty"]
        + timeliness * WEIGHTS["timeliness"]
    )

    caps: list[tuple[float, str]] = []
    origins = {e.origin_id for e in rel.evidence}
    if rel.claim_support == ClaimSupport.UNSUPPORTED:
        caps.append((40.0, "unsupported_claim_max_40"))
    if rel.claim_support == ClaimSupport.CONFLICTED:
        caps.append((60.0, "unresolved_conflict_max_60"))
    if len(origins) == 1 and all(e.source_type in SECONDARY_TYPES for e in rel.evidence):
        caps.append((70.0, "single_secondary_origin_max_70"))

    final = min([weighted, *(cap for cap, _ in caps)])
    return ConfidenceBreakdown(
        direct_support=direct,
        source_authority=authority,
        independent_corroboration=corroboration,
        entity_direction_certainty=rel.entity_direction_certainty,
        timeliness=timeliness,
        weighted_score=round(weighted, 1),
        applied_caps=[label for _, label in caps],
        final_score=round(final, 1),
    )


def score_relationship(rel: Relationship) -> None:
    breakdown = compute_confidence(rel)
    rel.confidence_breakdown = breakdown
    rel.confidence_score = breakdown.final_score
    rel.needs_human_validation = (
        rel.relevance_tier.value == "candidate"
        or rel.status != Status.FACT
        or breakdown.final_score < 70
    )

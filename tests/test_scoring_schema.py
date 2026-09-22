"""Confidence scoring and semantic-gate tests."""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from schema import (  # noqa: E402
    ClaimSupport,
    EvidenceRef,
    RelationSubtype,
    Relationship,
    RelevanceTier,
    SourceType,
    Status,
    Uncertainty,
)
from scoring import compute_confidence, score_relationship  # noqa: E402


def _evidence(source_type, origin="origin-1"):
    return EvidenceRef(
        source_type=source_type,
        source_name="测试源",
        url=f"https://example.com/{origin}",
        published_date=dt.date(2026, 8, 14),
        evidence_locator="p.3 表格",
        origin_id=origin,
    )


def _rel(*, support=ClaimSupport.DIRECT, tier=RelevanceTier.CORE,
         status=Status.FACT, evidence=None, certainty=95):
    return Relationship(
        relationship_id="test",
        subject_entity_id="SH.688836",
        object_entity_id="X",
        relation_type="supplier",
        relation_subtype=RelationSubtype.CONFIRMED_SUPPLIER,
        status=status,
        claim_support=support,
        is_indirect=False,
        uncertainty=Uncertainty.LOW if status == Status.FACT else Uncertainty.HIGH,
        entity_direction_certainty=certainty,
        natural_statement="测试关系",
        evidence=evidence or [_evidence(SourceType.PRIMARY_REGULATORY)],
        relevance_tier=tier,
    )


def test_primary_source_does_not_rescue_unsupported_claim():
    rel = _rel(
        support=ClaimSupport.UNSUPPORTED,
        tier=RelevanceTier.CANDIDATE,
        status=Status.UNKNOWN,
    )
    score_relationship(rel)
    assert rel.confidence_score <= 40
    assert "unsupported_claim_max_40" in rel.confidence_breakdown.applied_caps


def test_single_secondary_origin_is_capped_at_70():
    rel = _rel(evidence=[_evidence(SourceType.AUTHORITATIVE_MEDIA)])
    score_relationship(rel)
    assert rel.confidence_score == 70
    assert "single_secondary_origin_max_70" in rel.confidence_breakdown.applied_caps


def test_unresolved_conflict_is_capped_at_60():
    rel = _rel(
        support=ClaimSupport.CONFLICTED,
        tier=RelevanceTier.SUPPLEMENTARY,
        status=Status.INFERENCE,
        evidence=[
            _evidence(SourceType.PRIMARY_REGULATORY, "a"),
            _evidence(SourceType.PRIMARY_OFFICIAL, "b"),
        ],
    )
    score_relationship(rel)
    assert rel.confidence_score <= 60


def test_reposts_with_same_origin_are_not_independent():
    rel = _rel(evidence=[
        _evidence(SourceType.AUTHORITATIVE_MEDIA, "same"),
        _evidence(SourceType.GENERAL_MEDIA, "same"),
    ])
    score = compute_confidence(rel)
    assert score.independent_corroboration == 50
    assert "single_secondary_origin_max_70" in score.applied_caps


def test_official_direct_proof_can_score_above_80_but_is_not_automatic_100():
    rel = _rel(evidence=[_evidence(SourceType.PRIMARY_REGULATORY)])
    score_relationship(rel)
    assert 80 <= rel.confidence_score < 100


def test_relevance_is_independent_from_confidence():
    rel = _rel(tier=RelevanceTier.SUPPLEMENTARY)
    score_relationship(rel)
    assert rel.confidence_score >= 80
    assert rel.relevance_tier == RelevanceTier.SUPPLEMENTARY
    assert rel.needs_human_validation is False


def test_schema_rejects_fact_without_support():
    with pytest.raises(Exception, match="fact requires"):
        _rel(support=ClaimSupport.UNSUPPORTED, tier=RelevanceTier.CANDIDATE)

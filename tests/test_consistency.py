"""Dataset invariants and corrected high-risk claims."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "validate"))

from check_consistency import CHECKS, load  # noqa: E402


@pytest.fixture(scope="module")
def data():
    return load()


@pytest.mark.parametrize("name,fn", CHECKS)
def test_consistency_checks(data, name, fn):
    ents, rels = data
    bad = fn(rels) if fn.__code__.co_argcount == 1 else fn(ents, rels)
    assert bad == [], f"{name} 未通过：{bad}"


def test_all_five_relation_types_and_three_tiers_are_present(data):
    _, rels = data
    assert {r["relation_type"] for r in rels} == {
        "supplier", "customer", "partner", "investor_or_investee", "peer"
    }
    assert {r["relevance_tier"] for r in rels} == {"core", "supplementary", "candidate"}


def test_corrected_high_risk_relations(data):
    _, rels = data
    by_id = {r["relationship_id"]: r for r in rels}
    assert by_id["r-deepseek-inv"]["is_indirect"] is False
    assert by_id["r-deepseek-inv"]["effective_start"] == "2026-08-14"
    assert "933,399" in by_id["r-deepseek-inv"]["natural_statement"]
    assert "0.0198%" in by_id["r-zhongke-inv"]["natural_statement"]
    assert by_id["r-chinatelecom-tower"]["relevance_tier"] == "candidate"
    assert by_id["r-deepmind-partner"]["relevance_tier"] == "candidate"
    assert by_id["r-tongji"]["is_indirect"] is True
    assert "G1 EDU" in by_id["r-tongji"]["natural_statement"]


def test_named_prospectus_supplier_claims_are_not_facts(data):
    _, rels = data
    named = [r for r in rels if r["relationship_id"] in {
        "r-green-harmonic", "r-mingzhi", "r-orbbec", "r-beite", "r-bester",
        "r-meihu", "r-ruixin", "r-nasda", "r-robotec", "r-wolan",
    }]
    assert len(named) == 10
    assert all(r["status"] == "unknown" for r in named)
    assert all(r["claim_support"] == "unsupported" for r in named)
    assert all(r["confidence_score"] <= 40 for r in named)

"""Evidence manifest must stay synchronized without equating URLs with proof."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from build_evidence_manifest import build  # noqa: E402


def test_manifest_covers_every_reference_and_registered_source():
    rel_doc = json.loads((ROOT / "data" / "relations.json").read_text())
    manifest = build()
    expected = sum(len(r.get("evidence", [])) for r in rel_doc["relations"])
    assert manifest["summary"]["total_evidence_refs"] == expected
    assert manifest["summary"]["unregistered_source_refs"] == 0
    assert manifest["summary"]["source_type_mismatch_refs"] == 0
    assert all(row["local_research_note_exists"] for row in manifest["evidence"])


def test_snapshot_cutoff_is_distinct_from_later_verification():
    manifest = build()
    source_register = json.loads((ROOT / "data" / "source_register.json").read_text())
    assert manifest["as_of"] == source_register["as_of"] == "2026-09-20"
    assert source_register["verified_at"] == "2026-09-22"
    assert all(
        not row["published_date"] or row["published_date"] <= manifest["as_of"]
        for row in manifest["evidence"]
    )


def test_manifest_separates_traceability_from_claim_review():
    manifest = build()
    assert "not claim-verification" in manifest["interpretation"]
    candidates = [r for r in manifest["evidence"] if r["claim_support"] == "unsupported"]
    assert len(candidates) == 13
    assert all(r["content_review_status"] == "candidate_only_not_supported" for r in candidates)
    assert manifest["summary"]["specific_locator_refs"] == manifest["summary"]["total_evidence_refs"]
    assert all(not r["evidence_locator"].startswith("页面正文") for r in manifest["evidence"])


def test_http_only_people_links_are_transparently_registered():
    manifest = build()
    people_rows = [r for r in manifest["evidence"] if ".people.com.cn/" in r["url"]]
    assert len(people_rows) == 3
    assert all(r["url"].startswith("http://") for r in people_rows)
    assert all(r["access_status"] == "verified_exact_http_only" for r in people_rows)


def test_key_primary_locators_and_corrected_paths():
    rows = build()["evidence"]
    prospectus_suppliers = [r for r in rows if r["relationship_id"] == "r-green-harmonic"]
    assert "p.142" in prospectus_suppliers[0]["evidence_locator"]

    deepseek = next(r for r in rows if r["relationship_id"] == "r-deepseek-inv")
    assert "p.3" in deepseek["evidence_locator"]
    assert deepseek["source_type"] == "primary_regulatory"

    partner = next(r for r in rows if r["relationship_id"] == "r-deepseek-partner")
    assert partner["url"] == "https://roadshow.cnstock.com/ipo/688836"
    assert "签署战略合作备忘录" in partner["evidence_locator"]


def test_investor_identity_and_direction_match_reviewed_sources():
    rel_doc = json.loads((ROOT / "data" / "relations.json").read_text())
    ent_doc = json.loads((ROOT / "data" / "entities.json").read_text())
    rels = {r["relationship_id"]: r for r in rel_doc["relations"]}
    assert rels["r-sequoia-inv"]["is_indirect"] is False
    assert "7.1149%" in rels["r-sequoia-inv"]["natural_statement"]
    assert rels["r-meituan-inv"]["is_indirect"] is True
    assert "7.6114%" in rels["r-meituan-inv"]["natural_statement"]
    assert rels["r-deepseek-inv"]["is_indirect"] is False
    assert ent_doc["entities"]["HK.03690"]["ticker"] == "03690.HK"

"""Query contract tests shared by CLI and API."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from api import entities, evidence, relations  # noqa: E402
from query import QueryValidationError, filter_relations  # noqa: E402


@pytest.fixture(scope="module")
def data():
    ents = json.loads((ROOT / "data" / "entities.json").read_text())
    rels = json.loads((ROOT / "data" / "relations.json").read_text())
    return ents, rels


def test_default_query_excludes_candidates(data):
    _, doc = data
    rows = filter_relations(doc["relations"])
    assert rows
    assert all(r["relevance_tier"] != "candidate" for r in rows)
    candidates = filter_relations(doc["relations"], tier="candidate")
    assert candidates
    assert all(r["confidence_score"] <= 40 for r in candidates)


def test_query_filters_confidence_and_rejects_bad_inputs(data):
    ents, doc = data
    rows = filter_relations(
        doc["relations"],
        relation_type="investor_or_investee",
        min_confidence=80,
        entity_ids=ents["entities"].keys(),
    )
    assert rows and all(r["confidence_score"] >= 80 for r in rows)
    with pytest.raises(QueryValidationError, match="unknown entity"):
        filter_relations(doc["relations"], entity="missing", entity_ids={"SH.688836"})
    with pytest.raises(QueryValidationError, match="min_confidence"):
        filter_relations(doc["relations"], min_confidence=101)


def test_api_defaults_and_evidence_endpoint():
    focal = next(item for item in entities() if item["id"] == "SH.688836")
    assert focal["focal"] is True
    response = relations(
        type=None, tier=None, status=None, needs_validation=None, entity=None,
        date_from=None, date_to=None, min_confidence=None,
        include_candidates=False, offset=0, limit=100,
    )
    assert response["total"] == 28
    rows = evidence(relationship_id="r-deepseek-inv", source_type=None, offset=0, limit=10)
    assert rows["total"] >= 1
    assert "p.3" in rows["items"][0]["evidence_locator"]


def test_cli_candidate_and_evidence_queries():
    cli = ROOT / "src" / "cli.py"
    candidates = subprocess.run(
        [sys.executable, str(cli), "relations", "--tier", "candidate"],
        text=True, capture_output=True, check=False,
    )
    assert candidates.returncode == 0
    assert json.loads(candidates.stdout)["total"] == 13
    ev = subprocess.run(
        [sys.executable, str(cli), "evidence", "--relationship-id", "r-tongji"],
        text=True, capture_output=True, check=False,
    )
    assert ev.returncode == 0
    assert json.loads(ev.stdout)["total"] == 1

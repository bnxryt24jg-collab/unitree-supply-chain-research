"""HTTP JSON API（FastAPI）。

题目只要求 CLI 或 API 二选一；CLI 已交付，本文件作为「同一内核的 HTTP 包装层」，
复用 data/*.json，不重复任何业务逻辑。

启动：
    python -m uvicorn src.api:app --reload --port 8000
或：
    python src/api.py        # 内部调用 uvicorn.run

端点：
    GET /health
    GET /stats
    GET /entities
    GET /relations?type=&tier=&status=&min_confidence=&include_candidates=&offset=&limit=
    GET /evidence?relationship_id=&source_type=&offset=&limit=
    GET /entity/{entity_id}
    GET /graph
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

try:  # Supports both `uvicorn src.api:app` and `python src/api.py`.
    from .query import (
        DEFAULT_LIMIT,
        MAX_LIMIT,
        QueryValidationError,
        filter_evidence,
        filter_relations,
        paginate,
    )
except ImportError:  # pragma: no cover - exercised by direct script execution
    from query import (  # type: ignore[no-redef]
        DEFAULT_LIMIT,
        MAX_LIMIT,
        QueryValidationError,
        filter_evidence,
        filter_relations,
        paginate,
    )

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

app = FastAPI(
    title="ARTi · 宇树科技供应链与合作关系 API",
    description="以宇树科技为例的供应链/合作关系知识图谱，提供实体、关系、统计与图边表的 JSON 查询。",
    version="1.0.0",
)


def _load():
    ents = json.loads((DATA / "entities.json").read_text(encoding="utf-8"))["entities"]
    rels = json.loads((DATA / "relations.json").read_text(encoding="utf-8"))["relations"]
    return ents, rels


@app.get("/health")
def health():
    ents, rels = _load()
    return {"status": "ok", "entities": len(ents), "relations": len(rels)}


@app.get("/stats")
def stats():
    ents, rels = _load()
    by_type, by_status, by_tier = {}, {}, {}
    nv = 0
    for r in rels:
        by_type[r["relation_type"]] = by_type.get(r["relation_type"], 0) + 1
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
        t = r.get("relevance_tier", "supplementary")
        by_tier[t] = by_tier.get(t, 0) + 1
        if r.get("needs_human_validation"):
            nv += 1
    return {
        "entities": len(ents),
        "relations": len(rels),
        "core": by_tier.get("core", 0),
        "supplementary": by_tier.get("supplementary", 0),
        "candidate": by_tier.get("candidate", 0),
        "needs_human_validation": nv,
        "by_type": by_type,
        "by_status": by_status,
        "by_tier": by_tier,
    }


@app.get("/entities")
def entities():
    ents, _ = _load()
    return [
        {"id": k, "name": v["name"], "type": v.get("entity_type"),
         "ticker": v.get("ticker"), "focal": v.get("role_in_graph") == "subject"}
        for k, v in ents.items()
    ]


@app.get("/relations")
def relations(
    type: Optional[str] = Query(None, description="supplier/customer/partner/investor_or_investee/peer"),
    tier: Optional[str] = Query(None, description="core / supplementary / candidate"),
    status: Optional[str] = Query(None, description="fact / inference / unknown"),
    needs_validation: Optional[bool] = Query(None),
    entity: Optional[str] = Query(None, description="按实体 ID 过滤"),
    date_from: Optional[date] = Query(None, description="关系有效期窗口起点，YYYY-MM-DD"),
    date_to: Optional[date] = Query(None, description="关系有效期窗口终点，YYYY-MM-DD"),
    min_confidence: Optional[float] = Query(None, ge=0, le=100),
    include_candidates: bool = Query(False, description="未指定 tier 时是否包含未确认候选"),
    offset: int = Query(0, ge=0, description="分页偏移量"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="每页条数"),
):
    ents, rels = _load()
    try:
        items = filter_relations(
            rels,
            relation_type=type,
            tier=tier,
            status=status,
            needs_validation=needs_validation,
            entity=entity,
            entity_ids=ents.keys(),
            date_from=date_from,
            date_to=date_to,
            min_confidence=min_confidence,
            include_candidates=include_candidates,
        )
        return paginate(items, offset=offset, limit=limit)
    except QueryValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/evidence")
def evidence(
    relationship_id: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
):
    _, rels = _load()
    if relationship_id and relationship_id not in {r["relationship_id"] for r in rels}:
        raise HTTPException(status_code=404, detail="relationship not found")
    try:
        return paginate(
            filter_evidence(rels, relationship_id=relationship_id, source_type=source_type),
            offset=offset,
            limit=limit,
        )
    except QueryValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/entity/{entity_id}")
def entity(entity_id: str):
    ents, rels = _load()
    e = ents.get(entity_id)
    if not e:
        raise HTTPException(status_code=404, detail="entity not found")
    e = dict(e)
    e["related_relations"] = [
        r["relationship_id"] for r in rels
        if entity_id in (r["subject_entity_id"], r["object_entity_id"])
    ]
    return e


@app.get("/graph")
def graph(
    tier: Optional[str] = Query(None),
    min_confidence: Optional[float] = Query(None, ge=0, le=100),
    include_candidates: bool = Query(False),
):
    ents, rels = _load()
    try:
        rels = filter_relations(
            rels,
            tier=tier,
            min_confidence=min_confidence,
            include_candidates=include_candidates,
        )
    except QueryValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    edges = [
        {"source": r["subject_entity_id"], "target": r["object_entity_id"],
         "type": r["relation_type"], "confidence_score": r["confidence_score"],
         "tier": r.get("relevance_tier"),
         "needs_validation": r.get("needs_human_validation")}
        for r in rels
    ]
    node_ids = sorted({"SH.688836", *(edge["target"] for edge in edges)})
    return {"nodes": node_ids, "edges": edges}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

"""ARTi 供应链与合作关系研究 · CLI。

用法：
  python src/cli.py entities                       # 列出全部实体
  python src/cli.py relations                       # 默认列出已支持关系，不含 candidate
  python src/cli.py relations --type supplier       # 按关系类型过滤
  python src/cli.py relations --tier core            # 仅核心业务关系
  python src/cli.py relations --tier candidate       # 显式查看未确认候选
  python src/cli.py relations --needs-validation    # 仅需人工验证的关系
  python src/cli.py relations --entity SH.688017    # 某实体参与的关系
  python src/cli.py stats                           # 统计概览（含分层与验证待办）
  python src/cli.py get SH.688836                   # 查某实体详情
  python src/cli.py graph                           # 导出 networkx 可加载的边表 JSON
  python src/cli.py evidence --relationship-id r-chinamobile
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from query import (
    DEFAULT_LIMIT,
    RELATION_TYPES,
    SOURCE_TYPES,
    STATUSES,
    TIERS,
    QueryValidationError,
    filter_evidence,
    filter_relations,
    paginate,
)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ENT_PATH = DATA / "entities.json"
REL_PATH = DATA / "relations.json"


def load():
    ents = json.loads(ENT_PATH.read_text(encoding="utf-8"))["entities"]
    rels = json.loads(REL_PATH.read_text(encoding="utf-8"))["relations"]
    return ents, rels


def _name(ents, eid):
    return ents.get(eid, {}).get("name", eid)


def cmd_entities(ents, rels, args):
    rows = [{"id": k, "name": v["name"], "type": v.get("entity_type"),
             "ticker": v.get("ticker"), "focal": v.get("role_in_graph") == "subject"}
            for k, v in ents.items()]
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


def cmd_relations(ents, rels, args):
    items = filter_relations(
        rels,
        relation_type=args.type,
        tier=args.tier,
        status=args.status,
        needs_validation=True if args.needs_validation else None,
        entity=args.entity,
        entity_ids=ents.keys(),
        date_from=args.date_from,
        date_to=args.date_to,
        min_confidence=args.min_confidence,
        include_candidates=args.include_candidates,
    )
    out = []
    for r in items:
        out.append({
            "id": r["relationship_id"],
            "type": r["relation_type"],
            "subject": _name(ents, r["subject_entity_id"]),
            "object": _name(ents, r["object_entity_id"]),
            "status": r["status"],
            "indirect": r["is_indirect"],
            "claim_support": r["claim_support"],
            "confidence_score": r["confidence_score"],
            "tier": r.get("relevance_tier"),
            "needs_validation": r.get("needs_human_validation"),
            "statement": r["natural_statement"],
        })
    print(json.dumps(
        paginate(out, offset=args.offset, limit=args.limit),
        ensure_ascii=False,
        indent=2,
    ))
    return 0


def cmd_stats(ents, rels, args):
    by_type, by_status, by_tier = {}, {}, {}
    nv = 0
    for r in rels:
        by_type[r["relation_type"]] = by_type.get(r["relation_type"], 0) + 1
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
        t = r.get("relevance_tier", "supplementary")
        by_tier[t] = by_tier.get(t, 0) + 1
        if r.get("needs_human_validation"):
            nv += 1
    print(json.dumps({
        "entities": len(ents),
        "relations": len(rels),
        "core": by_tier.get("core", 0),
        "supplementary": by_tier.get("supplementary", 0),
        "candidate": by_tier.get("candidate", 0),
        "needs_human_validation": nv,
        "by_type": by_type,
        "by_status": by_status,
        "by_tier": by_tier,
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_get(ents, rels, args):
    e = ents.get(args.entity_id)
    if not e:
        print(json.dumps({"error": "entity not found", "entity_id": args.entity_id}, ensure_ascii=False), file=sys.stderr)
        return 1
    related = [r["relationship_id"] for r in rels
               if args.entity_id in (r["subject_entity_id"], r["object_entity_id"])]
    e = dict(e)
    e["related_relations"] = related
    print(json.dumps(e, ensure_ascii=False, indent=2))
    return 0


def cmd_graph(ents, rels, args):
    rels = filter_relations(
        rels,
        tier=args.tier,
        min_confidence=args.min_confidence,
        include_candidates=args.include_candidates,
    )
    edges = [{"source": r["subject_entity_id"], "target": r["object_entity_id"],
              "type": r["relation_type"], "confidence_score": r["confidence_score"],
              "tier": r.get("relevance_tier"),
              "needs_validation": r.get("needs_human_validation")} for r in rels]
    node_ids = sorted({"SH.688836", *(e["target"] for e in edges)})
    print(json.dumps({"nodes": node_ids, "edges": edges},
                     ensure_ascii=False, indent=2))
    return 0


def cmd_evidence(ents, rels, args):
    ids = {r["relationship_id"] for r in rels}
    if args.relationship_id and args.relationship_id not in ids:
        raise QueryValidationError(f"unknown relationship_id={args.relationship_id!r}")
    rows = filter_evidence(
        rels,
        relationship_id=args.relationship_id,
        source_type=args.source_type,
    )
    print(json.dumps(
        paginate(rows, offset=args.offset, limit=args.limit),
        ensure_ascii=False,
        indent=2,
    ))
    return 0


def main():
    ap = argparse.ArgumentParser(description="ARTi 宇树科技供应链/合作关系 CLI")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("entities")
    p_rel = sub.add_parser("relations")
    p_rel.add_argument("--type", choices=RELATION_TYPES)
    p_rel.add_argument("--tier", choices=TIERS)
    p_rel.add_argument("--status", choices=STATUSES)
    p_rel.add_argument("--needs-validation", action="store_true")
    p_rel.add_argument("--entity")
    p_rel.add_argument("--date-from")
    p_rel.add_argument("--date-to")
    p_rel.add_argument("--min-confidence", type=float)
    p_rel.add_argument("--include-candidates", action="store_true")
    p_rel.add_argument("--offset", type=int, default=0)
    p_rel.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    sub.add_parser("stats")
    p_get = sub.add_parser("get")
    p_get.add_argument("entity_id")
    p_graph = sub.add_parser("graph")
    p_graph.add_argument("--tier", choices=TIERS)
    p_graph.add_argument("--min-confidence", type=float)
    p_graph.add_argument("--include-candidates", action="store_true")
    p_evidence = sub.add_parser("evidence")
    p_evidence.add_argument("--relationship-id")
    p_evidence.add_argument("--source-type", choices=SOURCE_TYPES)
    p_evidence.add_argument("--offset", type=int, default=0)
    p_evidence.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    args = ap.parse_args()
    ents, rels = load()
    try:
        return {
            "entities": cmd_entities,
            "relations": cmd_relations,
            "stats": cmd_stats,
            "get": cmd_get,
            "graph": cmd_graph,
            "evidence": cmd_evidence,
        }[args.cmd or "stats"](ents, rels, args)
    except QueryValidationError as exc:
        ap.error(str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())

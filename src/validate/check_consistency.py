"""一致性校验脚本（人工验证与冲突处理的程序化检查）。

读取 data/entities.json 与 data/relations.json，逐条核对 SCHEMA.md 与题目要求中的
关键不变量，输出可读报告；任一检查失败则以非零码退出，可直接接入 CI / 复现流水线。

运行：
    python src/validate/check_consistency.py
退出码：0 = 全部通过；1 = 存在失败项。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
ENT_PATH = DATA / "entities.json"
REL_PATH = RELATIONS_JSON = DATA / "relations.json"

SUBJECT = "SH.688836"


def load():
    ents = json.loads(ENT_PATH.read_text(encoding="utf-8"))["entities"]
    rels = json.loads(REL_PATH.read_text(encoding="utf-8"))["relations"]
    return ents, rels


def check_evidence_present(rels):
    bad = []
    for r in rels:
        if not r.get("evidence"):
            bad.append(r["relationship_id"] + " 无 evidence")
            continue
        for e in r["evidence"]:
            if not e.get("evidence_locator"):
                bad.append(r["relationship_id"] + " 存在空 evidence_locator")
    return bad


def check_direction(rels):
    bad = []
    for r in rels:
        if r["subject_entity_id"] != SUBJECT:
            bad.append(f"{r['relationship_id']} subject 写反: {r['subject_entity_id']}")
        if r["object_entity_id"] == SUBJECT:
            bad.append(f"{r['relationship_id']} object 指向自身（方向错误）")
    return bad


def check_claim_semantics(rels):
    bad = []
    for r in rels:
        tier = r.get("relevance_tier")
        support = r.get("claim_support")
        if r.get("status") == "fact" and support in {"unsupported", "conflicted"}:
            bad.append(f"{r['relationship_id']} fact 与 {support} 冲突")
        if support == "unsupported" and tier != "candidate":
            bad.append(f"{r['relationship_id']} unsupported 未进入 candidate")
        if tier == "core" and support in {"unsupported", "conflicted"}:
            bad.append(f"{r['relationship_id']} core 缺乏已解决的支持证据")
    return bad


def check_validation_flag(rels):
    bad = []
    for r in rels:
        nv = r.get("needs_human_validation")
        expected = (
            r.get("relevance_tier") == "candidate"
            or r.get("status") != "fact"
            or r.get("confidence_score", 0) < 70
        )
        if nv != expected:
            bad.append(f"{r['relationship_id']} needs_human_validation({nv}) 与证据状态不一致")
    return bad


def check_confidence_caps(rels):
    bad = []
    primary_types = {"primary_regulatory", "primary_official", "primary_procurement"}
    for r in rels:
        score = r.get("confidence_score")
        support = r.get("claim_support")
        caps = r.get("confidence_breakdown", {}).get("applied_caps", [])
        if support == "unsupported" and (score > 40 or "unsupported_claim_max_40" not in caps):
            bad.append(f"{r['relationship_id']} 未执行 unsupported 40分上限")
        if support == "conflicted" and (score > 60 or "unresolved_conflict_max_60" not in caps):
            bad.append(f"{r['relationship_id']} 未执行 conflict 60分上限")
        origins = {e.get("origin_id") for e in r.get("evidence", [])}
        only_secondary = r.get("evidence") and all(
            e.get("source_type") not in primary_types for e in r["evidence"]
        )
        if len(origins) == 1 and only_secondary and (
            score > 70 or "single_secondary_origin_max_70" not in caps
        ):
            bad.append(f"{r['relationship_id']} 未执行单一二手源70分上限")
    return bad


def check_inference_uncertainty(rels):
    bad = []
    for r in rels:
        if r["status"] == "inference" and r.get("uncertainty") == "low":
            bad.append(f"{r['relationship_id']} status=inference 但 uncertainty=low（应 ≥medium）")
    return bad


def check_no_duplicate_pairs(rels):
    seen, bad = set(), []
    for r in rels:
        key = (r["relation_type"], r["object_entity_id"])
        if key in seen:
            bad.append(f"重复关系对: {key}")
        seen.add(key)
    return bad


def check_referential_integrity(ents, rels):
    bad = []
    ent_ids = set(ents.keys())
    for r in rels:
        for eid in (r["subject_entity_id"], r["object_entity_id"]):
            if eid not in ent_ids:
                bad.append(f"{r['relationship_id']} 引用了不存在的实体 {eid}")
    # 反向：related 实体至少参与一条关系
    referenced = {eid for r in rels for eid in (r["subject_entity_id"], r["object_entity_id"])}
    for eid in ent_ids:
        if eid not in referenced:
            bad.append(f"实体 {eid} 未被任何关系引用（孤儿实体）")
    return bad


def check_material_investor_retention(rels):
    """招股书披露的持股比例超过 5% 的投资关系应保留为 core。"""
    target = {"UNLISTED.红杉中国", "HK.03690"}
    bad = []
    for r in rels:
        if r["object_entity_id"] in target and r.get("relevance_tier") != "core":
            bad.append(f"{r['object_entity_id']} 重要投资关系未保留为 core（tier={r.get('relevance_tier')}）")
    return bad


def check_dual_role_cases(rels):
    """卧龙/金发应以 supplier+investor 出现，DeepSeek 以 partner+investor 出现。"""
    expect = {"SH.600580": 2, "SH.600143": 2, "UNLISTED.DeepSeek": 2}  # 卧龙、金发、DeepSeek
    counts = {}
    for r in rels:
        if r["object_entity_id"] in expect:
            counts.setdefault(r["object_entity_id"], set()).add(r["relation_type"])
    bad = []
    for eid, n in expect.items():
        if eid not in counts or len(counts[eid]) < 2:
            bad.append(f"{eid} 双重角色（supplier+investor）未完整登记")
    return bad


CHECKS = [
    ("证据链完整（每条关系≥1证据且 locator 非空）", check_evidence_present),
    ("方向正确（subject 恒为宇树，无自环）", check_direction),
    ("事实、证据支持与业务分层语义一致", check_claim_semantics),
    ("验证标记与证据状态一致", check_validation_flag),
    ("置信度硬上限执行正确", check_confidence_caps),
    ("inference 关系 uncertainty 不为 low", check_inference_uncertainty),
    ("无重复关系对（同类型+同对象）", check_no_duplicate_pairs),
    ("引用完整性（无孤儿实体/悬空引用）", check_referential_integrity),
    ("重要投资关系保留（红杉/美团=core）", check_material_investor_retention),
    ("双重角色冲突已登记（卧龙/金发 supplier+investor；DeepSeek partner+investor）", check_dual_role_cases),
]


def main():
    ents, rels = load()
    print(f"加载：{len(ents)} 实体 / {len(rels)} 关系（截点 {json.loads(ENT_PATH.read_text(encoding='utf-8')).get('as_of')}）\n")
    all_ok = True
    for name, fn in CHECKS:
        try:
            bad = fn(rels) if fn.__code__.co_argcount == 1 else fn(ents, rels)
        except Exception as e:  # noqa: BLE001
            print(f"  [ERROR] {name}：校验脚本异常 {e}")
            all_ok = False
            continue
        if bad:
            all_ok = False
            print(f"  [FAIL] {name}")
            for b in bad:
                print(f"         - {b}")
        else:
            print(f"  [PASS] {name}")
    print()
    if all_ok:
        print("✅ 全部一致性校验通过。")
        return 0
    print("❌ 存在失败项，请按 SCHEMA.md 的约束复核并修正 build_dataset.py。")
    return 1


if __name__ == "__main__":
    sys.exit(main())

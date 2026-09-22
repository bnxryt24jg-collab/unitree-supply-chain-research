"""端到端可复现测试。

验证：重新运行 build_dataset 生成的 entities/relations 能 100% 通过
一致性校验，且无证据链缺失，保证一条命令即可复现。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "validate"))

import build_dataset  # noqa: E402
from check_consistency import CHECKS, load  # noqa: E402


def test_build_is_reproducible_and_passes_all_checks():
    # 1) 重新构建数据集（覆盖 data/entities.json, data/relations.json）
    build_dataset.main()

    # 2) 重新加载并通过全部一致性校验
    ents, rels = load()
    assert len(ents) >= 30
    assert len(rels) >= 30

    for name, fn in CHECKS:
        bad = fn(rels) if fn.__code__.co_argcount == 1 else fn(ents, rels)
        assert bad == [], f"{name} 未通过：{bad}"


def test_json_files_well_formed():
    build_dataset.main()
    ent_doc = json.loads((ROOT / "data" / "entities.json").read_text(encoding="utf-8"))
    rel_doc = json.loads((ROOT / "data" / "relations.json").read_text(encoding="utf-8"))
    assert "as_of" in ent_doc and "as_of" in rel_doc
    assert ent_doc["as_of"] == rel_doc["as_of"] == str(build_dataset.AS_OF) == "2026-09-20"

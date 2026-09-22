"""合规公开页面采集器。

设计原则（对接 COLLECTION.md §4）：
  - robots.txt 优先：对任一来源自动化采集前先解析 domain/robots.txt，禁止目录不碰。
  - 不突破技术防护：不处理登录/付费墙；遇到需鉴权页面直接跳过并写入人工待办。
  - 限频无害：最小间隔 1 秒 + 随机抖动，避免对目标站造成压力。
  - 快照可复现：抓取结果落 data/raw/<source>_<slug>.html，并记 crawl_log.jsonl。

用法：
  python fetch.py --list                # 列出 sources.yaml 所有来源
  python fetch.py --source cninfo --url <公告列表页>   # 抓单个公开索引页
  python fetch.py --check-robots <url>  # 仅检查某 URL 是否被 robots 允许
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SOURCES_YAML = HERE / "sources.yaml"
RAW_DIR = ROOT / "data" / "raw"
LOG_PATH = RAW_DIR / "crawl_log.jsonl"
MIN_INTERVAL = 1.0  # 秒，最小请求间隔
UA = "ARTi-ComplianceFetcher/1.0 (+research; respects robots.txt)"


def load_sources() -> dict:
    with open(SOURCES_YAML, encoding="utf-8") as f:
        return yaml.safe_load(f)


def robots_allows(url: str, user_agent: str = UA) -> tuple[bool, str]:
    """返回 (是否允许, 说明)。robots 不可达/解析失败一律保守判定为禁止。"""
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    rp = RobotFileParser()
    rp.set_url(base + "/robots.txt")
    try:
        rp.read()
    except Exception as e:  # 网络/解析失败 → 保守
        return False, f"robots 读取失败({e})，保守禁止"
    allowed = rp.can_fetch(user_agent, url)
    return allowed, ("允许" if allowed else "robots 禁止")


def fetch_public_page(url: str, source_id: str, slug: str | None = None) -> dict:
    """抓取单个公开索引页。仅当 robots 允许、且非登录/付费页时落快照。"""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    allowed, note = robots_allows(url)
    if not allowed:
        return _log(source_id, url, "skipped", f"robots 禁止: {note}")
    # 保守识别登录/付费墙信号（仅作提示，不主动破解）
    p = urlparse(url)
    if any(t in url.lower() for t in ("/login", "/pay", "paywall", "/member", "captcha")):
        return _log(source_id, url, "skipped", "疑似登录/付费页，留人工待办")
    try:
        time.sleep(MIN_INTERVAL + random.uniform(0, 1.0))  # 限频 + 抖动
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=20) as resp:
            body = resp.read()
        slug = slug or (p.netloc + p.path).replace("/", "_")[:80]
        out = RAW_DIR / f"{source_id}_{slug}.html"
        out.write_bytes(body)
        return _log(source_id, url, "stored", f"快照 {out.name} ({len(body)} bytes)")
    except Exception as e:
        return _log(source_id, url, "error", str(e))


def _log(source_id: str, url: str, status: str, detail: str) -> dict:
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "source_id": source_id,
        "url": url,
        "status": status,
        "detail": detail,
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description="ARTi 合规采集器")
    ap.add_argument("--list", action="store_true", help="列出 sources.yaml 来源")
    ap.add_argument("--source", help="来源 id（对应 sources.yaml）")
    ap.add_argument("--url", help="要抓取的公开页面 URL")
    ap.add_argument("--check-robots", help="仅检查某 URL 是否允许")
    args = ap.parse_args(argv)

    if args.check_robots:
        ok, note = robots_allows(args.check_robots)
        print(f"robots: {'ALLOW' if ok else 'DENY'} — {note}")
        return 0
    if args.list:
        src = load_sources()
        for cat in ("primary_sources", "authoritative_media", "government_official",
                    "commercial_db", "research", "public_records"):
            for s in src.get(cat, []):
                print(f"[{s['source_type']}] {s['id']:<16} {s['name']:<22} {s['url']}")
        return 0
    if args.source and args.url:
        rec = fetch_public_page(args.url, args.source)
        print(json.dumps(rec, ensure_ascii=False))
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

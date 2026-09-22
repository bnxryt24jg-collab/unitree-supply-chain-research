"""Evidence-locator quality rules shared by builders and validators."""
from __future__ import annotations


GENERIC_PREFIXES = ("页面正文", "网页正文", "正文；", "本地研究摘要")
SPECIFIC_MARKERS = (
    "p.",
    "pp.",
    "表",
    "检索",
    "章节",
    "公告",
    "问答",
    "文章《",
    "GitHub 仓库目录",
    "产品页",
)


def is_specific_locator(locator: str | None) -> bool:
    """Return whether a locator gives a reviewer an actionable lookup path."""
    value = (locator or "").strip()
    if not value or value.startswith(GENERIC_PREFIXES):
        return False
    return any(marker in value for marker in SPECIFIC_MARKERS)

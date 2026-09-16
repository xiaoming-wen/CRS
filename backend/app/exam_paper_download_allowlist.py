"""试卷下载用户名白名单（从同目录 .txt 读取，可随 git 部署到服务器）。"""
from __future__ import annotations

from pathlib import Path

_ALLOWLIST_FILE = Path(__file__).with_suffix(".txt")
_FALLBACK = frozenset({"hfu_stu1", "hfu_stu2", "hfu_advisor1"})


def exam_paper_download_allowlist_usernames() -> frozenset:
    names: set[str] = set()
    try:
        text = _ALLOWLIST_FILE.read_text(encoding="utf-8")
    except OSError:
        return _FALLBACK
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        names.add(s)
    return frozenset(names) if names else _FALLBACK

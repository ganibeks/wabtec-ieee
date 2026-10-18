"""Test history: every saved check is stored on disk (test_history/) with its report, separate from results/."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HIST = ROOT / "test_history"


def _safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s)[:60] or "module"


def save(record: dict, report_html: bytes, when: datetime) -> Path:
    """Store one test. Never overwrites: the file stem carries the timestamp to the millisecond."""
    HIST.mkdir(exist_ok=True)
    stem = f"{when.strftime('%Y%m%d_%H%M%S_%f')[:-3]}_{_safe(record.get('serial', ''))}"
    js, rp = HIST / f"{stem}.json", HIST / f"{stem}.html"
    assert not js.exists() and not rp.exists(), stem
    record = dict(record, id=stem, saved=when.strftime("%Y-%m-%d %H:%M:%S"), report_file=rp.name)
    rp.write_bytes(report_html)
    js.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return js


def load_all() -> list[dict]:
    if not HIST.exists():
        return []
    out = []
    for f in sorted(HIST.glob("*.json"), reverse=True):
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return out


def report_bytes(record: dict) -> bytes | None:
    f = HIST / record.get("report_file", "")
    return f.read_bytes() if f.is_file() else None

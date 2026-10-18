"""Write virtual_lab/testbench_standalone.html: one offline file containing every selectable dataset.

Usage (from the project root):  python virtual_lab/build_standalone.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from virtual_lab import payload as P  # noqa: E402


def main() -> Path:
    data = P.bundle()
    out = HERE / "testbench_standalone.html"
    out.write_text(P.render_html(data), encoding="utf-8")
    print(f"Wrote {out}  ({out.stat().st_size / 1e6:.2f} MB)")
    for d in data["datasets"]:
        m = d["meta"]
        print(f"  INCLUDED  {m['id']:<14} {m['status']:<8} {m['run_folder']}")
    for x in data["excluded"]:
        print(f"  EXCLUDED  {x['id']:<14} {x['status']:<14} {x['reason']}")
    return out


if __name__ == "__main__":
    main()

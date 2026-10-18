"""Build the tester firmware with the pip-installed zig/clang toolchain (pip install ziglang).

    python firmware/build.py

1. Host simulator      -> firmware/build/igbt_tester_sim.exe  (core + virtual board, runs on this PC)
2. Target compile check -> firmware/build/tester_cortex_m4.o  (core only, freestanding Cortex-M4F;
   proves the portable core builds for the STM32G474 CPU; it is NOT linked or run on hardware)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

FW = Path(__file__).resolve().parent
BUILD = FW / "build"
EXE = BUILD / ("igbt_tester_sim.exe" if sys.platform == "win32" else "igbt_tester_sim")
ZIG = [sys.executable, "-m", "ziglang"]
WARN = ["-Wall", "-Wextra", "-Werror"]


def run(args, label):
    print(f"[{label}] " + " ".join(str(a) for a in args[3:]))
    r = subprocess.run(args, cwd=FW, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout, r.stderr)
        raise SystemExit(f"{label}: FAILED")
    print(f"[{label}] OK")


def main() -> Path:
    BUILD.mkdir(exist_ok=True)
    run(ZIG + ["c++", "-std=c++17", "-O2", *WARN, "-Iinclude", "-Isrc/sim",
               "src/tester.cpp", "src/sim/sim_board.cpp", "src/sim/main_sim.cpp", "-o", str(EXE)], "host-sim")
    run(ZIG + ["c++", "-std=c++17", "-Os", *WARN, "-target", "thumb-freestanding-eabihf", "-mcpu=cortex_m4",
               "-ffreestanding", "-fno-exceptions", "-fno-rtti", "-Iinclude",
               "-c", "src/tester.cpp", "-o", str(BUILD / "tester_cortex_m4.o")], "cortex-m4 core")
    return EXE


if __name__ == "__main__":
    main()

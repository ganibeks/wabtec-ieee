"""Host link to the tester firmware (C++). Today: the host-simulator build with a virtual STM32G474 board
that samples a MATLAB/Simscape record. Later: the same line protocol over the board's USB-CDC port.

Provenance of every value returned: SIMULATED (simulation record -> modelled ADC -> firmware algorithms).
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

from . import datasets as D
from . import features as F

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "firmware"
EXE = FW / "build" / ("igbt_tester_sim.exe" if sys.platform == "win32" else "igbt_tester_sim")


def ensure_built() -> Path:
    if not EXE.exists():
        sys.path.insert(0, str(FW))
        import build  # firmware/build.py
        build.main()
    return EXE


def _nice_up(x: float) -> float:
    e = 10 ** math.floor(math.log10(x))
    for m in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if m * e >= x:
            return m * e
    return 10 * e


def front_end(ds: D.Dataset) -> dict:
    """ASSUMED analogue front end: voltage channels sized 1.5 x bus, current channels 1.25 x record peak."""
    x = F.load_dynamic(ds.csv)
    bus = float(ds.params["bus_V"])
    ipk = float(max(np.max(np.abs(x["Ic"])), np.max(np.abs(x["Id"]))))
    v = _nice_up(1.5 * bus)
    i = _nice_up(1.25 * ipk)
    return {"fs_VGE": 20.0, "fs_VCE": v, "fs_VCE_CLAMP": 12.0, "fs_VSW": v, "fs_VBUS": v, "fs_IC": i, "fs_ID": i}


def run_double_pulse(ds: D.Dataset, adc_rate_hz=2e6, desat_thr_V=9.0, desat_blank_us=5.0,
                     inject_fault_us: float | None = None, timeout_s=60) -> dict:
    exe = ensure_built()
    if ds.kind not in ("dynamic_rl", "dynamic_r") or not ds.selectable:
        raise ValueError(f"{ds.id}: firmware replay needs a selectable dynamic run")
    p = ds.params
    e_us = [round(e * 1e6, 6) for e in ds.edges_s]
    stop_us = round(float(ds.stop_s or p.get("dynamicStop_s")) * 1e6, 6)
    fe = front_end(ds)
    cmds = ["PING", f"LOAD {ds.csv.name} {p['bus_V']!r}", "RECPLAN " + " ".join(map(str, e_us)),
            "PLAN " + " ".join(map(str, e_us + [stop_us])),
            f"CFG bus_expected_V {p['bus_V']!r}", f"CFG gate_on_V {p['gateOn_V']!r}", f"CFG gate_off_V {p['gateOff_V']!r}",
            f"CFG desat_thr_V {desat_thr_V!r}", f"CFG desat_blank_us {desat_blank_us!r}", f"CFG adc_rate_hz {adc_rate_hz!r}"]
    cmds += [f"CFG {k} {v!r}" for k, v in fe.items()]
    if inject_fault_us is not None:
        cmds.append(f"CFG inject_fault_us {inject_fault_us!r}")
    cmds += ["RUN", "QUIT"]
    # cwd = run folder: the record is opened by a relative ASCII name (the project path is non-ASCII).
    r = subprocess.run([str(exe)], input="\n".join(cmds) + "\n", cwd=ds.folder, capture_output=True,
                       text=True, timeout=timeout_s)
    lines = [json.loads(s) for s in r.stdout.splitlines() if s.strip()]
    out = {"commands": cmds, "lines": lines, "returncode": r.returncode, "stderr": r.stderr,
           "meas": {}, "status": {}, "events": [], "errors": [], "front_end": fe,
           "config": {"adc_rate_hz": adc_rate_hz, "desat_thr_V": desat_thr_V, "desat_blank_us": desat_blank_us,
                      "inject_fault_us": inject_fault_us}}
    for m in lines:
        if m["type"] == "meas":
            out["meas"][m["key"]] = m
        elif m["type"] == "status":
            out["status"][m["key"]] = m["value"]
        elif m["type"] == "event":
            out["events"].append(m)
        elif m["type"] == "error":
            out["errors"].append(m["message"])
        elif m["type"] == "pong":
            out["firmware"] = m
        elif m["type"] == "done":
            out["ok"] = m["ok"]
    return out


def reference(ds: D.Dataset) -> dict:
    """Full-resolution values from the same record (Python, float64) for the firmware comparison table."""
    x = F.load_dynamic(ds.csv)
    t, e = x["t"], ds.edges_s
    on = (t > e[1] - 10e-6) & (t < e[1] - 2e-6)
    fw = (t > e[2] - 10e-6) & (t < e[2] - 2e-6)
    bus = float(ds.params["bus_V"])
    i0 = float(np.mean(x["Ic"][(t > e[1] - 10e-6) & (t < e[1] - 5e-6)]))
    after = t >= e[1]
    def first_cross(y, level, rising):
        m = np.nonzero(after[:-1] & ((y[:-1] < level) & (y[1:] >= level) if rising else (y[:-1] > level) & (y[1:] <= level)))[0]
        if not m.size:
            return float("nan")
        j = m[0]
        return float(t[j] + (level - y[j]) * (t[j + 1] - t[j]) / (y[j + 1] - y[j]))
    return {
        "vce_sat_V": float(np.mean(np.minimum(x["Vce"][on], 10.0))),
        "vce_sat_at_A": float(np.mean(x["Ic"][on])),
        "diode_vf_V": float(np.mean(x["Vswitch"][fw] - bus)),
        "diode_vf_at_A": float(np.mean(x["Id"][fw])),
        "peak_vce_V": float(np.max(x["Vce"])), "peak_vce_t_us": float(t[np.argmax(x["Vce"])] * 1e6),
        "peak_ic_A": float(np.max(x["Ic"])), "peak_ic_t_us": float(t[np.argmax(x["Ic"])] * 1e6),
        "off1_cmd_to_vce90_us": (first_cross(x["Vce"], 0.9 * bus, True) - e[1]) * 1e6,
        "off1_ic_fall_90_10_us": (first_cross(x["Ic"], 0.1 * i0, False) - first_cross(x["Ic"], 0.9 * i0, False)) * 1e6,
    }

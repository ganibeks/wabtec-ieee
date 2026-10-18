"""Independent Python re-computation of +testcell/analyze_dynamic.m metrics from the exported CSV.

Definitions mirror analyze_dynamic.m (windows, 10/90 crossing rules, 1 % clearance). The thresholds
recorded here are the MATLAB numerical-model checks; they are NOT hardware acceptance limits.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

trapz = getattr(np, "trapezoid", None) or np.trapz


def load_dynamic(csv) -> dict:
    d = pd.read_csv(csv)
    x = {c.rsplit("_", 1)[0]: d[c].to_numpy(float) for c in d.columns}
    x["t"] = x.pop("time")
    return x


def load_baseline(csv) -> dict:
    d = pd.read_csv(csv)
    return {"t": d["time_s"].to_numpy(float), "Vge": d["gate_emitter_V"].to_numpy(float),
            "Vce": d["collector_emitter_V"].to_numpy(float), "Ic": d["collector_A"].to_numpy(float)}


def _cumtrapz(t, y):
    return np.concatenate([[0.0], np.cumsum(np.diff(t) * (y[1:] + y[:-1]) / 2)])


def _crossing(t, v, edge, level, rising, horizon=80e-6):
    if rising:
        c = np.nonzero((v[:-1] < level) & (v[1:] >= level))[0]
    else:
        c = np.nonzero((v[:-1] > level) & (v[1:] <= level))[0]
    c = c[(t[c] >= edge - 0.1e-6) & (t[c] < edge + horizon)]
    if c.size == 0:
        return float("nan")
    j = c[0]
    return float(t[j] + (level - v[j]) * (t[j + 1] - t[j]) / (v[j + 1] - v[j]))


# Analyzer versions: "current" = +testcell/analyze_dynamic.m now; "legacy_v0" = the snapshot used by
# results/dynamic_20261017_165503_678 (all event windows 15 us, crossing horizon 15 us,
# OFF gate window 320-340 us, no 1 % clearance metric). Python mirrors the version that produced the JSON.
ANALYZERS = {"current": {"off_dur": 80e-6, "horizon": 80e-6, "clearance": True, "off_window": None},
             "legacy_v0": {"off_dur": 15e-6, "horizon": 15e-6, "clearance": False, "off_window": (320e-6, 340e-6)}}


def analyze_dynamic(x: dict, p: dict, kind: str, edges, analyzer: str = "current") -> dict:
    cfg = ANALYZERS[analyzer]
    t = x["t"]
    bus, R, Rs, Ls = p["bus_V"], p["loadR_Ohm"], p["strayR_Ohm"], p["strayL_H"]
    r: dict = {}
    r["kcl_max_A"] = float(np.max(np.abs(x["IL"] - x["Ic"] - x["Id"])))
    r["bus_kcl_max_A"] = float(np.max(np.abs(x["Ibus"] - x["IL"] + x["Id"])))
    r["bus_energy_J"] = float(trapz(bus * x["Ibus"], t))
    r["load_resistor_energy_J"] = float(trapz(R * x["IL"] ** 2, t))
    r["stray_resistor_energy_J"] = float(trapz(Rs * x["Ic"] ** 2, t))
    r["dut_collector_terminal_energy_J"] = float(trapz(x["Vce"] * x["Ic"], t))
    r["dut_gate_terminal_energy_J"] = float(trapz(x["Vge"] * x["Ig"], t))
    r["diode_terminal_energy_J"] = float(trapz((x["Vswitch"] - bus) * x["Id"], t))
    r["stray_stored_energy_change_J"] = float(0.5 * Ls * (x["Ic"][-1] ** 2 - x["Ic"][0] ** 2))
    if kind == "dynamic_rl":
        L = p["loadL_H"]
        r["load_stored_energy_change_J"] = float(0.5 * L * (x["IL"][-1] ** 2 - x["IL"][0] ** 2))
        flux = L * (x["IL"] - x["IL"][0])
        vint = _cumtrapz(t, bus - R * x["IL"] - x["Vswitch"])
        r["inductor_flux_relative_error"] = float(np.max(np.abs(flux - vint)) / max(np.max(np.abs(flux)), 1e-9))
        fw = (t > edges[2] - 10e-6) & (t < edges[2] - 2e-6)
        r["freewheel_min_current_A"] = float(np.min(x["Id"][fw]))
        r["freewheel_Ic_to_IL_ratio"] = float(np.max(np.abs(x["Ic"][fw])) / np.mean(x["IL"][fw]))
    else:
        r["load_stored_energy_change_J"] = 0.0
        r["resistive_kvl_max_V"] = float(np.max(np.abs(bus - R * x["IL"] - x["Vswitch"])))
    sumE = sum(r[k] for k in ("load_resistor_energy_J", "stray_resistor_energy_J", "dut_collector_terminal_energy_J",
                              "diode_terminal_energy_J", "stray_stored_energy_change_J", "load_stored_energy_change_J"))
    r["energy_balance_error_J"] = r["bus_energy_J"] - sumE
    r["energy_balance_relative_error"] = abs(r["energy_balance_error_J"]) / max(abs(r["bus_energy_J"]), 1e-6)
    plateau = (t > 100e-6) & (t < 200e-6)
    if cfg["off_window"]:
        off = (t > cfg["off_window"][0]) & (t < cfg["off_window"][1])
    else:
        off = (t > edges[2] - 10e-6) & (t < edges[2] - 2e-6)
    r["on_gate_max_error_V"] = float(np.max(np.abs(x["Vge"][plateau] - p["gateOn_V"])))
    r["off_gate_max_error_V"] = float(np.max(np.abs(x["Vge"][off] - p["gateOff_V"])))
    r["peak_Vce_V"] = float(np.max(x["Vce"]))
    r["peak_Ic_A"] = float(np.max(x["Ic"]))
    r["peak_Ig_A"] = float(np.max(np.abs(x["Ig"])))
    r["peak_Vce_time_s"] = float(t[np.argmax(x["Vce"])])
    events = []
    for k, e in enumerate(edges, start=1):
        on = k % 2 == 1
        dur = 15e-6 if on else cfg["off_dur"]
        H = cfg["horizon"]
        idx = (t >= e - 2e-6) & (t <= e + dur)
        z = {"command_time_s": e, "window_s": [e - 2e-6, e + dur], "on_event": on,
             "gross_collector_terminal_energy_J": float(trapz(x["Vce"][idx] * x["Ic"][idx], t[idx])),
             "gate_charge_C": float(trapz(x["Ig"][idx], t[idx])),
             "gate_terminal_energy_J": float(trapz(x["Vge"][idx] * x["Ig"][idx], t[idx]))}
        if on:
            low = float(np.median(x["Vce"][(t > e + 5e-6) & (t < e + 10e-6)]))
            a = _crossing(t, x["Vce"], e, low + 0.9 * (bus - low), False, H)
            b = _crossing(t, x["Vce"], e, low + 0.1 * (bus - low), False, H)
        else:
            low = float(np.median(x["Vce"][(t > e - 10e-6) & (t < e - 5e-6)]))
            a = _crossing(t, x["Vce"], e, low + 0.1 * (bus - low), True, H)
            b = _crossing(t, x["Vce"], e, low + 0.9 * (bus - low), True, H)
        z["Vce_transition_10_90_s"] = b - a
        z["command_to_Vce_transition_s"] = a - e
        ref = float("nan")
        if k == 3 or not on:
            if on:
                ref = float(np.median(x["IL"][(t > e + 5e-6) & (t < e + 10e-6)]))
                a = _crossing(t, x["Ic"], e, 0.1 * ref, True, H)
                b = _crossing(t, x["Ic"], e, 0.9 * ref, True, H)
            else:
                ref = float(np.median(x["Ic"][(t > e - 10e-6) & (t < e - 5e-6)]))
                a = _crossing(t, x["Ic"], e, 0.9 * ref, False, H)
                b = _crossing(t, x["Ic"], e, 0.1 * ref, False, H)
            z["Ic_transition_10_90_s"] = b - a
        else:
            z["Ic_transition_10_90_s"] = float("nan")
        if not on and cfg["clearance"]:
            m = np.nonzero((t > e) & (t < e + 80e-6) & (x["Ic"] < 0.01 * ref) & (x["Vce"] > 0.99 * bus))[0]
            z["current_clearance_1percent_s"] = float(t[m[0]] - e) if m.size else float("nan")
        else:
            z["current_clearance_1percent_s"] = float("nan")
        events.append(z)
    r["events"] = events
    return r


def switching_times(x: dict, p: dict, edges) -> dict:
    """Inductive-load switching times by the usual datasheet definitions (Mitsubishi HVIGBT convention):
      td(on) : Vge 10 % rise  -> Ic 10 % ;  tr : Ic 10 % -> 90 %      (hard turn-on ON-2, edge 3)
      td(off): Vge 90 % fall  -> Ic 90 % ;  tf : Ic 90 % -> 10 %      (OFF-1, edge 2)
    Percentages of the gate swing (Voff..Von) and of the load current. di/dt = 0.8 I / (10-90 % time),
    the average slope over the 10-90 % interval. Values are SIMULATED at the record's device temperature."""
    t, vge, ic = x["t"], x["Vge"], x["Ic"]
    von, voff = p["gateOn_V"], p["gateOff_V"]
    out = {}
    e = edges[2]
    i_on = float(np.median(x["IL"][(t > e + 5e-6) & (t < e + 10e-6)]))
    g10 = _crossing(t, vge, e, voff + 0.1 * (von - voff), True)
    i10 = _crossing(t, ic, e, 0.1 * i_on, True)
    i90 = _crossing(t, ic, e, 0.9 * i_on, True)
    out.update(on_current_A=i_on, td_on_s=i10 - g10, tr_s=i90 - i10, didt_on_A_per_s=0.8 * i_on / (i90 - i10))
    e = edges[1]
    i_off = float(np.median(ic[(t > e - 10e-6) & (t < e - 5e-6)]))
    g90 = _crossing(t, vge, e, voff + 0.9 * (von - voff), False)
    j90 = _crossing(t, ic, e, 0.9 * i_off, False)
    j10 = _crossing(t, ic, e, 0.1 * i_off, False)
    out.update(off_current_A=i_off, td_off_s=j90 - g90, tf_s=j10 - j90, didt_off_A_per_s=0.8 * i_off / (j10 - j90))
    out["didt_max_A_per_s"] = max(abs(out["didt_on_A_per_s"]), abs(out["didt_off_A_per_s"]))
    # gate charge and driver energy per switching cycle (ON-2 window) for the slide-5 driver-power check
    w = (t >= edges[2] - 2e-6) & (t <= edges[2] + 15e-6)
    qg = float(trapz(x["Ig"][w], t[w]))
    out.update(gate_charge_C=qg, driver_energy_per_cycle_J=abs(qg) * (von - voff))
    return out


def dynamic_checks(r: dict, kind: str, analyzer: str = "current") -> list[dict]:
    """The assertions of analyze_dynamic.m, evaluated on the Python numbers (same limits, not loosened)."""
    rows = [
        ("Current continuity |IL-Ic-Id|, |Ibus-IL+Id|", "< 1e-5 A", max(r["kcl_max_A"], r["bus_kcl_max_A"]), lambda v: v < 1e-5, "kcl_max_A"),
        ("Terminal energy balance (relative)", "< 0.005", r["energy_balance_relative_error"], lambda v: v < 0.005, "energy_balance_relative_error"),
        ("ON gate plateau |Vge-Von| (100-200 us)", "< 0.02 V", r["on_gate_max_error_V"], lambda v: v < 0.02, "on_gate_max_error_V"),
        ("OFF gate plateau |Vge-Voff| (before 2nd ON)", "< 0.02 V", r["off_gate_max_error_V"], lambda v: v < 0.02, "off_gate_max_error_V"),
    ]
    if kind == "dynamic_rl":
        rows += [
            ("Integrated inductor law (relative flux error)", "< 0.005", r["inductor_flux_relative_error"], lambda v: v < 0.005, "inductor_flux_relative_error"),
            ("Freewheel min diode current", "> 0.1 A", r["freewheel_min_current_A"], lambda v: v > 0.1, "freewheel_min_current_A"),
            ("Freewheel |Ic|/IL", "< 0.01", r["freewheel_Ic_to_IL_ratio"], lambda v: v < 0.01, "freewheel_Ic_to_IL_ratio"),
        ]
    else:
        rows.append(("Resistive-load KVL", "< 1e-3 V", r["resistive_kvl_max_V"], lambda v: v < 1e-3, "resistive_kvl_max_V"))
    ev_ok = all(np.isfinite(e["Vce_transition_10_90_s"]) for e in r["events"]) and \
        all(np.isfinite(e["Ic_transition_10_90_s"]) for e in r["events"][1:])
    out = [{"criterion": c, "limit": lim, "key": key, "python": float(v), "pass": bool(f(v))} for c, lim, v, f, key in rows]
    if analyzer == "current":  # legacy_v0 did not assert transition resolution
        out.append({"criterion": "All Vce / Ic transitions resolved in event windows", "limit": "finite", "key": None,
                    "python": None, "pass": bool(ev_ok)})
    return out


def analyze_baseline(x: dict) -> dict:
    """Mirror of validate_baseline.m on its 2 us CSV grid (same grid the MATLAB checks used)."""
    t, vge, vce, ic = x["t"], x["Vge"], x["Vce"], x["Ic"]
    ph = np.mod(t, 0.002)
    on = (ph > 0.0012) & (ph < 0.0018)
    off = (ph > 0.0002) & (ph < 0.0008)
    eI = (12 - 0.8) / 100.1
    eV = 12 - 100 * eI
    c = {"on_gate_error_V": float(np.max(np.abs(vge[on] - 15))),
         "off_gate_error_V": float(np.max(np.abs(vge[off] + 15))),
         "on_current_error_A": float(np.max(np.abs(ic[on] - eI))),
         "on_vce_error_V": float(np.max(np.abs(vce[on] - eV))),
         "off_current_max_A": float(np.max(np.abs(ic[off]))),
         "off_vce_error_V": float(np.max(np.abs(vce[off] - 12))),
         "kvl_error_V": float(np.max(np.abs(vce + 100 * ic - 12))),
         "source_energy_J": float(trapz(12 * ic, t)),
         "peak_source_power_W": float(np.max(12 * ic)),
         "rising_edges": int(np.sum(np.diff((vge > 6).astype(int)) == 1)),
         "falling_edges": int(np.sum(np.diff((vge > 6).astype(int)) == -1))}
    return c


def baseline_checks(c: dict) -> list[dict]:
    rows = [("ON gate level error", "< 0.01 V", "on_gate_error_V", lambda v: v < 0.01),
            ("OFF gate level error", "< 0.01 V", "off_gate_error_V", lambda v: v < 0.01),
            ("ON current vs circuit law", "< 1e-4 A", "on_current_error_A", lambda v: v < 1e-4),
            ("ON Vce vs circuit law", "< 0.01 V", "on_vce_error_V", lambda v: v < 0.01),
            ("OFF current", "< 1e-6 A", "off_current_max_A", lambda v: v < 1e-6),
            ("OFF Vce vs supply", "< 0.01 V", "off_vce_error_V", lambda v: v < 0.01),
            ("KVL Vce + R*Ic = 12 V", "< 0.01 V", "kvl_error_V", lambda v: v < 0.01)]
    out = [{"criterion": n, "limit": lim, "key": k, "python": c[k], "pass": bool(f(c[k]))} for n, lim, k, f in rows]
    out.append({"criterion": "Gate edges (3 rising, >=2 falling)", "limit": "3 / >=2", "key": None,
                "python": f'{c["rising_edges"]} / {c["falling_edges"]}',
                "pass": c["rising_edges"] == 3 and c["falling_edges"] >= 2})
    return out


def rel_diff(a, b) -> float:
    a = float("nan") if a is None else float(a)
    b = float("nan") if b is None else float(b)
    if not (np.isfinite(a) and np.isfinite(b)):
        return 0.0 if (np.isnan(a) and np.isnan(b)) else float("nan")
    if a == b:
        return 0.0
    return abs(a - b) / max(abs(a), abs(b), 1e-300)

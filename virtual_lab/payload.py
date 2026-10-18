"""Build the JSON payload consumed by virtual_lab/web/testbench.html.

Every number in the payload comes from a results/ folder (CSV / validation JSON / parameters.json)
or is recomputed from that CSV by features.py. Nothing is synthesised for display.
Arrays: time as float64 little-endian base64 (sub-ns solver steps need double precision);
channel samples as float32 little-endian base64 at FULL solver resolution (no decimation).
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import datasets as D
from . import features as F

WEB = Path(__file__).resolve().parent / "web"
PLACEHOLDER = "/*__LAB_PAYLOAD__*/"

CHANNELS = {
    #  key      csv-key  label                  unit color      description
    "Vge":     ("Vge",   "Vge",                 "V", "#a88400", "Gate-emitter voltage at the IGBT terminals (VgeSensor)"),
    "Ig":      ("Ig",    "Ig",                  "A", "#d2601a", "Gate current through Rg (IgSensor)"),
    "Vce":     ("Vce",   "Vce",                 "V", "#0a7ea4", "Collector-emitter voltage (VceSensor, collector to ground)"),
    "Vswitch": ("Vswitch", "Vswitch",           "V", "#2f5fd0", "Switch-node voltage SW to ground (VswitchSensor)"),
    "Ic":      ("Ic",    "Ic",                  "A", "#1f8a4c", "Collector current, positive into collector (IcSensor)"),
    "IL":      ("IL",    "IL",                  "A", "#a335c4", "Load-branch current P to LoadR (ILSensor)"),
    "Id":      ("Id",    "Id",                  "A", "#d0021b", "Freewheel branch current SW to diode anode (IdSensor, includes DiodeC displacement)"),
    "Ibus":    ("Ibus",  "Ibus",                "A", "#555555", "Bus source current (IbusSensor)"),
}

EVENT_DESC = {
    "dynamic_rl": ["First turn-on with IL ~ 0: charges the load inductor",
                   "Turn-off: inductive current commutates into the freewheel diode",
                   "Second (hard) turn-on while the diode carries the load current",
                   "Second turn-off at the higher end-of-pulse current"],
    "dynamic_r": ["First turn-on into the resistive load", "First turn-off (resistive)",
                  "Second turn-on (resistive)", "Second turn-off (resistive)"],
}


# Residual-type metrics are differences of nearly equal numbers; the 15-significant-digit CSV
# cannot reproduce them to 1e-6 relative. They are flagged, not hidden or counted as matches.
RESIDUAL_KEYS = {"energy_balance_relative_error", "inductor_flux_relative_error", "kcl_max_A", "resistive_kvl_max_V",
                 "on_gate_max_error_V", "off_gate_max_error_V", "on_gate_error_V", "off_gate_error_V",
                 "on_current_error_A", "on_vce_error_V", "off_vce_error_V", "kvl_error_V", "off_current_max_A"}


def _mvp_row(metric, event, mv, pv):
    rd = F.rel_diff(mv, pv)
    both_na = mv is None and (pv is None or not np.isfinite(pv))
    return {"metric": metric, "event": event, "matlab": mv, "python": pv, "rel_diff": rd,
            "both_na": bool(both_na), "residual": metric in RESIDUAL_KEYS,
            "abs_diff": abs(float(mv) - float(pv)) if (mv is not None and pv is not None and np.isfinite(pv)) else None,
            "match": bool(rd < 1e-6) if np.isfinite(rd) and not both_na else False}


def _b64(arr, dtype) -> str:
    return base64.b64encode(np.ascontiguousarray(arr, dtype=np.dtype(dtype).newbyteorder("<")).tobytes()).decode()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def _timestamp(folder: Path) -> str:
    m = re.search(r"(\d{8})_(\d{6})", folder.name)
    if not m:
        return ""
    return datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")


def _clean(v):
    """JSON-safe: NaN/inf -> None, numpy -> python."""
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    if isinstance(v, (np.floating, float)):
        return float(v) if np.isfinite(v) else None
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, Path):
        return str(v)
    return v


def _channel(x, key, csv_key):
    _, label, unit, color, desc = CHANNELS[key][0], CHANNELS[key][1], CHANNELS[key][2], CHANNELS[key][3], CHANNELS[key][4]
    a = x[csv_key]
    return {"b64": _b64(a, "f4"), "label": label, "unit": unit, "color": color, "desc": desc,
            "min": float(np.min(a)), "max": float(np.max(a))}


def _meta(ds: D.Dataset, root: Path) -> dict:
    p = ds.params
    schema = p.get("schema", "")
    traction = schema == "testcell.traction_device.v1"
    notes = ["Hardware decision: INCONCLUSIVE (no approved device-specific acceptance limits).",
             "Numerical checks are simulation-consistency checks, not hardware acceptance limits."]
    if traction:
        notes += ["Device parameters from Mitsubishi CM1500HC-66XB datasheet HVM-1147-B (typical values; "
                  "representative traction module, NOT a confirmed Wabtec part). Load/fixture values ASSUMED.",
                  "Freewheel diode has NO reverse recovery (datasheet Qrr 880 uC, Erec 1.05 J at 25 C not modelled): "
                  "turn-on overshoot and Eon are underestimated.",
                  "transit_s (tail current) is ASSUMED: modelled Ic fall (~22 us) is far slower than datasheet tf <= 0.70 us."]
    elif ds.kind in ("dynamic_rl", "dynamic_r", "static"):
        notes += ["Assumed/illustrative device parameters (testcell.parameters); not a locomotive module datasheet.",
                  "Freewheel diode: piecewise-linear conduction + capacitance, no reverse recovery."]
    else:
        notes += ["Ideal switching IGBT, illustrative 12 V / 100 ohm values; no gate capacitance, so no switching dynamics."]
    return {
        "id": ds.id, "kind": ds.kind, "label": ds.label, "status": ds.status,
        "provenance": "SIMULATED", "hardware_decision": "INCONCLUSIVE",
        "run_folder": str(ds.folder.relative_to(root)) if ds.folder.is_relative_to(root) else str(ds.folder),
        "timestamp": _timestamp(ds.folder),
        "csv": ds.csv.name if ds.csv else None,
        "csv_sha256": _sha256(ds.csv) if ds.csv and ds.csv.exists() else None,
        "model_file": ds.model_file.name if ds.model_file else None,
        "engine": "MATLAB R2026b + Simscape Electrical (generated by +testcell / build_baseline.m)",
        "parameter_schema": schema or p.get("schema", ""),
        "parameter_provenance": p.get("provenance", ""),
        "edges_source": ds.edges_source,
        "analyzer": getattr(ds, "analyzer", "current"),
        "parameters_note": "Illustrative/assumed parameters" if not traction else
                           "Datasheet typical values + ASSUMED fixture/load (see parameters.json tags)",
        "notes": notes,
        "energy_caveat": "Event integrals of Vce*Ic include conduction and reactive energy transfer; "
                         "they are NOT calibrated Eon/Eoff dissipation.",
    }


def _edges(ds: D.Dataset) -> list[dict]:
    out = []
    n_on = n_off = 0
    descs = EVENT_DESC.get(ds.kind, [])
    for k, e in enumerate(ds.edges_s):
        on = k % 2 == 0
        if on:
            n_on += 1
            name = f"ON-{n_on}"
        else:
            n_off += 1
            name = f"OFF-{n_off}"
        out.append({"t": float(e), "on": on, "name": name,
                    "desc": descs[k] if k < len(descs) else ("Gate command ON" if on else "Gate command OFF")})
    return out


def _dynamic_payload(ds: D.Dataset, root: Path) -> dict:
    x = F.load_dynamic(ds.csv)
    p = ds.params
    m = json.loads(ds.validation.read_text(encoding="utf-8-sig"))
    py = F.analyze_dynamic(x, p, ds.kind, ds.edges_s, ds.analyzer)
    checks = F.dynamic_checks(py, ds.kind, ds.analyzer)
    peak_ic = float(np.max(np.abs(x["Ic"])))
    thresholds = {
        "Vth_V": p["Vth_V"], "bus_V": p["bus_V"], "conduct_A": 0.01 * peak_ic, "vce_sat_frac": 0.10,
        "rules": {
            "conduct_A": f"1 % of record peak |Ic| = {0.01 * peak_ic:.6g} A (display threshold, not an acceptance limit)",
            "gate": f"ON-BIAS: Vge >= Vth ({p['Vth_V']} V); CHARGING: 0 < Vge < Vth; OFF-BIAS: Vge <= 0",
            "igbt": "NEGATIVE Ic: Ic < -thr; BLOCKING: |Ic| <= thr; CONDUCTING-SAT: Ic > thr and Vce < 10 % bus; "
                    "TAIL CURRENT: Ic > thr, Vce >= 10 % bus, Vge < Vth; SWITCHING: Ic > thr, Vce >= 10 % bus, Vge >= Vth",
            "diode": "FREEWHEELING: Id > thr; NEGATIVE Id: Id < -thr (transient/displacement); BLOCKING otherwise",
        },
    }
    # MATLAB vs Python
    mvp = []
    scalar_keys = ["peak_Vce_V", "peak_Ic_A", "peak_Ig_A", "energy_balance_relative_error", "bus_energy_J",
                   "dut_collector_terminal_energy_J", "diode_terminal_energy_J", "load_resistor_energy_J",
                   "inductor_flux_relative_error", "freewheel_min_current_A", "freewheel_Ic_to_IL_ratio",
                   "on_gate_max_error_V", "off_gate_max_error_V", "kcl_max_A", "resistive_kvl_max_V"]
    for k in scalar_keys:
        if k in m and k in py:
            mvp.append(_mvp_row(k, None, m[k], py[k]))
    ev_keys = ["Vce_transition_10_90_s", "Ic_transition_10_90_s", "command_to_Vce_transition_s",
               "current_clearance_1percent_s", "gross_collector_terminal_energy_J", "gate_charge_C"]
    events = []
    for i, (me, pe) in enumerate(zip(m.get("events", []), py["events"])):
        row = {"name": _edges(ds)[i]["name"], "t": pe["command_time_s"], "metrics": {}}
        for k in ev_keys:
            mv = me.get(k, None) if k in me else None
            r = _mvp_row(k, row["name"], mv, pe.get(k))
            r["in_matlab"] = k in me
            row["metrics"][k] = r
            if k in me:
                mvp.append(r)
        events.append(row)
    vrows = []
    for c in checks:
        mv = m.get(c["key"]) if c["key"] else None
        if c["key"] == "kcl_max_A":
            mv = max(m.get("kcl_max_A", 0), m.get("bus_kcl_max_A", 0))
        vrows.append({"criterion": c["criterion"], "limit": c["limit"], "matlab": mv, "python": c["python"],
                      "pass_python": c["pass"], "matlab_status": m.get("status")})
    vrows.append({"criterion": "Half-step (MaxStep/2) event energy convergence", "limit": "< 0.03",
                  "matlab": max(m.get("half_step_event_energy_relative_errors", [float("nan")])),
                  "python": None, "pass_python": None, "matlab_status": m.get("status")})
    channels = {k: _channel(x, k, v[0]) for k, v in CHANNELS.items()}
    # DERIVED in float64 before float32 packing: Vswitch - Vbus cancels ~48 V to uV, which float32 cannot resolve.
    vak = x["Vswitch"] - p["bus_V"]
    derived = {"VAK": {"b64": _b64(vak, "f4"), "label": "V_AK", "unit": "V",
                       "desc": "Diode anode-cathode voltage = Vswitch - Vbus (computed in float64 from simulated channels)"}}
    return {
        "derived": derived,
        "meta": _meta(ds, root), "params": p, "thresholds": thresholds, "edges": _edges(ds),
        "t_b64": _b64(x["t"], "f8"), "n": int(len(x["t"])), "channels": channels, "events": events,
        "validation_rows": vrows, "matlab_vs_python": mvp,
        "checks_python": {"all_pass": all(c["pass"] for c in checks), "rows": checks},
        "matlab_summary": {k: m.get(k) for k in ("status", "peak_Vce_V", "peak_Ic_A", "peak_Ig_A",
                                                  "energy_balance_relative_error", "scope", "energy_interpretation")},
        "python_summary": {k: py.get(k) for k in ("peak_Vce_V", "peak_Vce_time_s", "peak_Ic_A", "peak_Ig_A",
                                                   "energy_balance_relative_error")},
    }


def _baseline_payload(ds: D.Dataset, root: Path) -> dict:
    x = F.load_baseline(ds.csv)
    m = json.loads(ds.validation.read_text(encoding="utf-8-sig"))
    c = F.analyze_baseline(x)
    checks = F.baseline_checks(c)
    p = ds.params
    peak_ic = float(np.max(np.abs(x["Ic"])))
    chans = {"Vge": _channel(x, "Vge", "Vge"), "Vce": _channel(x, "Vce", "Vce"), "Ic": _channel(x, "Ic", "Ic")}
    chans["Vge"]["desc"] = "Gate-emitter voltage (Vge_Sensor); driver connected directly to gate"
    chans["Ic"]["desc"] = "Series loop current: source -> 100 ohm -> Collector_Current sensor -> IGBT"
    mvp = [_mvp_row(k, None, m.get(k), c[k])
           for k in ("on_gate_error_V", "off_gate_error_V", "on_current_error_A", "on_vce_error_V", "off_current_max_A",
                     "off_vce_error_V", "kvl_error_V", "source_energy_J", "peak_source_power_W") if k in m]
    vrows = [{"criterion": r["criterion"], "limit": r["limit"], "matlab": m.get(r["key"]) if r["key"] else None,
              "python": r["python"], "pass_python": r["pass"], "matlab_status": m.get("status")} for r in checks]
    return {
        "meta": _meta(ds, root), "params": p,
        "thresholds": {"Vth_V": 6.0, "bus_V": 12.0, "conduct_A": 0.01 * peak_ic, "vce_sat_frac": 0.10,
                       "rules": {"conduct_A": f"1 % of record peak |Ic| = {0.01 * peak_ic:.6g} A",
                                 "gate": "ON-BIAS: Vge >= 6 V; CHARGING: 0 < Vge < 6 V; OFF-BIAS: Vge <= 0",
                                 "igbt": "BLOCKING: |Ic| <= thr; CONDUCTING-SAT: Ic > thr and Vce < 10 % bus; otherwise SWITCHING",
                                 "diode": "No diode in this topology"}},
        "edges": _edges(ds), "t_b64": _b64(x["t"], "f8"), "n": int(len(x["t"])), "channels": chans, "events": [],
        "validation_rows": vrows, "matlab_vs_python": mvp,
        "checks_python": {"all_pass": all(r["pass"] for r in checks), "rows": checks},
        "matlab_summary": {"status": m.get("status")}, "python_summary": {},
    }


def _static_payload(ds: D.Dataset, root: Path) -> dict:
    s = pd.read_csv(ds.csv)
    sat = pd.read_csv(ds.folder / "saturation.csv")
    v = json.loads(ds.validation.read_text(encoding="utf-8-sig"))
    out_curves, leak_curves = [], []
    for name, g in s.groupby("experiment", sort=False):
        rec = {"experiment": name, "T_C": float(g.temperature_C.iloc[0]), "gate_V": float(g.gate_command_V.iloc[0]),
               "force_V": g.force_command.tolist(), "Vce_V": g.Vce_V.tolist(), "Ic_A": g.Ic_A.tolist(),
               "Vge_V": g.Vge_V.tolist(), "settling_A": g.settling_range_A.tolist()}
        (leak_curves if name.startswith("leak") else out_curves).append(rec)
    sat_rows = sat.to_dict(orient="records")
    meta = _meta(ds, root)
    meta["notes"].append("Static status PARTIAL: 25 C output/leakage + current-clamp points complete; "
                         "75 C voltage fixture blocked (solver stall); 125 C has one 20 A calibration point only.")
    return {"meta": meta, "params": ds.params, "static": {"output": out_curves, "leakage": leak_curves,
                                                           "saturation": sat_rows},
            "validation_rows": [{"criterion": k, "limit": "", "matlab": val, "python": None, "pass_python": None,
                                 "matlab_status": v.get("status")} for k, val in v.items()],
            "matlab_vs_python": [], "checks_python": {"all_pass": None, "rows": []}, "edges": [], "events": []}


def build_dataset(ds: D.Dataset, root: Path | None = None) -> dict:
    root = Path(root) if root else D.ROOT
    if not ds.selectable:
        raise ValueError(f"{ds.id} is not selectable: {ds.status} - {ds.reason}")
    if ds.kind in ("dynamic_rl", "dynamic_r"):
        return _clean(_dynamic_payload(ds, root))
    if ds.kind == "baseline":
        return _clean(_baseline_payload(ds, root))
    if ds.kind == "static":
        return _clean(_static_payload(ds, root))
    raise ValueError(ds.kind)


def bundle(dataset_ids=None, root=None) -> dict:
    root = Path(root) if root else D.ROOT
    all_ds = D.discover(root)
    chosen = [d for d in all_ds if d.selectable and (dataset_ids is None or d.id in dataset_ids)]
    if dataset_ids is not None:
        missing = set(dataset_ids) - {d.id for d in chosen}
        if missing:
            raise KeyError(f"Not selectable or unknown: {sorted(missing)}")
    return {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "generator": "virtual_lab.payload.bundle",
        "datasets": [build_dataset(d, root) for d in chosen],
        "excluded": [{"id": d.id, "label": d.label, "status": d.status, "reason": d.reason,
                      "folder": d.folder.name} for d in all_ds if not d.selectable],
    }


def render_html(payload: dict, template: Path | None = None) -> str:
    html = (template or WEB / "testbench.html").read_text(encoding="utf-8")
    assert PLACEHOLDER in html, "payload placeholder missing in template"
    js = json.dumps(payload, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    return html.replace(PLACEHOLDER, "window.__LAB_PAYLOAD__ = " + js + ";", 1)

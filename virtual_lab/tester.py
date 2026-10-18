"""Tester-level view: map data sources onto the depot tester tiles and one PASS / NO-PASS verdict.

Verdict rule (conservative): PASS only if every required tile was tested AND is inside an approved limit.
Anything else is NO-PASS, with the reason kept separate:
  FAILED        - at least one value outside its limit
  NOT VERIFIED  - a tile not tested / not modelled, or limits not approved (then the hardware decision is INCONCLUSIVE)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import datasets as D
from . import features as F

TILES = [  # key, label, unit
    ("I_GES", "Gate leakage", "mA"),
    ("V_GE_th", "Gate threshold", "V"),
    ("V_CE_sat", "Vce(sat)", "V"),
    ("V_f", "Diode Vf", "V"),
    ("t_trip", "Desat trip", "µs"),
    ("R_NTC", "NTC sensor", "Ω"),
    ("Z_th", "Thermal Zth", "K/W"),
    ("f_res", "Acoustic", "Hz"),
]


@dataclass
class Tile:
    key: str
    label: str
    unit: str
    value: float | None
    state: str            # IN_LIMIT | OUT_OF_LIMIT | NO_LIMIT | NOT_TESTED
    limit: str
    note: str
    provenance: str       # PRESET-DEMO | SIMULATED | ASSUMED | MEASURED


def verdict(tiles: list[Tile], limits: str) -> dict:
    """Evaluate the full required test set, including checks without evidence.

    SLIDE comparisons and DEMO limits never establish a hardware decision.
    The SLIDE key check also prevents a caller from passing only successful tiles.
    """
    failed = [t.label for t in tiles if t.state == "OUT_OF_LIMIT"]
    unverified = [t.label for t in tiles if t.state not in ("IN_LIMIT", "OUT_OF_LIMIT")
                  or t.value is None or not np.isfinite(t.value)]
    if limits == "SLIDE":
        present = {t.key for t in tiles}
        unverified += [label for key, label, _ in SLIDE_TILES if key not in present]
    ok = bool(tiles) and not failed and not unverified
    if not tiles:
        reason, detail = "NOT VERIFIED", "No simulated check available for this run"
    elif ok and limits == "SLIDE":
        reason, detail = "PASS", f"All {len(tiles)} simulated checks inside the Wabtec slide 5/8 values"
    elif ok:
        reason, detail = "PASS", "All tests inside " + ("approved" if limits == "APPROVED" else "DEMO") + " limits"
    elif failed:
        reason, detail = "FAILED", "Failed: " + ", ".join(failed)
    else:
        reason, detail = "NOT VERIFIED", "Not verified: " + ", ".join(unverified)
    return {"verdict": "PASS" if ok else "NO-PASS", "reason": reason, "detail": detail, "limits": limits,
            "failed": failed, "unverified": unverified,
            "hardware_decision": ("PASS" if ok else "FAIL" if failed else "INCONCLUSIVE") if limits == "APPROVED" else "INCONCLUSIVE"}


def tiles_from_preset(res) -> list[Tile]:
    """Teammate engine (igbt_simulation_engine.CABTEResult). Values and limits are PRESET-DEMO."""
    out = []
    for key, label, unit in TILES:
        p = res.parameters.get(key)
        if p is None:
            out.append(Tile(key, label, unit, None, "NOT_TESTED", "—", "not in preset", "PRESET-DEMO"))
            continue
        out.append(Tile(key, label, p.unit, float(p.measured_value), "IN_LIMIT" if p.passed else "OUT_OF_LIMIT",
                        f"{p.pass_min} – {p.pass_max} {p.unit} (DEMO)", p.description, "PRESET-DEMO"))
    return out


def sim_packet(ds: D.Dataset) -> dict:
    """Values a simulation run can actually supply, read from its CSV. Others are null with a reason."""
    x = F.load_dynamic(ds.csv)
    t, e = x["t"], ds.edges_s
    bus = float(ds.params["bus_V"])
    fw = (t > e[2] - 10e-6) & (t < e[2] - 2e-6)          # freewheel window (same as analyze_dynamic.m)
    on = (t > e[1] - 10e-6) & (t < e[1] - 2e-6)          # end of first ON pulse
    vf = float(np.median(x["Vswitch"][fw] - bus)) if fw.any() else None
    vf_i = float(np.median(x["Id"][fw])) if fw.any() else None
    vce = float(np.median(x["Vce"][on])) if on.any() else None
    vce_i = float(np.median(x["Ic"][on])) if on.any() else None
    return {
        "I_GES": {"value": None, "unit": "mA", "reason": "not modelled: gate is purely capacitive (no oxide leakage path)"},
        "V_f": {"value": vf, "unit": "V", "at_A": vf_i,
                "reason": "diode V_AK = Vswitch - Vbus during freewheel (median, last 10-2 us before ON-2); not Vce(sat)"},
        "t_trip": {"value": None, "unit": "µs", "reason": "not modelled: no desaturation detector / protection logic"},
        "R_NTC": {"value": None, "unit": "Ω", "reason": "not modelled: no NTC thermistor in the model"},
        "V_CE_sat": {"value": vce, "unit": "V", "at_A": vce_i,
                     "reason": "Vce median over last 10-2 us of pulse 1 (Vge = +15 V)"},
        "V_GE_th": {"value": float(ds.params.get("Vth_V")), "unit": "V",
                    "reason": "model INPUT parameter (ASSUMED / datasheet), not a measured result"},
    }


def slide_tiles_from_firmware(res: dict, ds: D.Dataset) -> list[Tile]:
    """Firmware double-pulse results mapped onto the slide 5/8 list. Only what the MCU sequence measures."""
    m, ev = res["meas"], res["events"]
    out: dict[str, Tile] = {}
    von, voff = m.get("vge_on_V", {}).get("value"), m.get("vge_off_V", {}).get("value")
    if von is not None and voff is not None:
        err = max(abs(von - 15.0), abs(voff + 15.0))
        out["gate"] = Tile("gate", "Gate drive ±15 V", "V", von, "IN_LIMIT" if err < 0.02 else "OUT_OF_LIMIT",
                           "+15 / −15 V (SLIDE 5/8); tolerance 0.02 V = model check in analyze_dynamic.m",
                           f"firmware ADC: VGE ON {von:.4f} V, OFF {voff:.4f} V (LSB ≈ 9.8 mV)", "SIMULATED")
    else:
        out["gate"] = Tile("gate", "Gate drive ±15 V", "V", None, "NOT_TESTED", SLIDE["gate"], "sequence aborted before the gate windows", "—")
    out["vth"] = Tile("vth", "Turn-on threshold", "V", None, "NOT_TESTED", "+4 … +7 V (SLIDE 8)",
                      "firmware sequence has no static threshold step (MATLAB static checks do)", "—")
    out["didt"] = Tile("didt", "Max di/dt", "A/µs", None, "NOT_TESTED", "≤ 5000 A/µs (SLIDE 5)",
                       f"a {res['config']['adc_rate_hz'] / 1e6:g} MS/s MCU ADC cannot resolve sub-µs current edges; needs a fast digitiser", "—")
    out["diode_fwd"] = Tile("diode_fwd", "Diode forward", "V", None, "NOT_TESTED", "0.2 … 0.8 V (SLIDE 5)",
                            "low-current diode (DMM-mode) step not in the firmware double-pulse sequence", "—")
    out["diode_rev"] = Tile("diode_rev", "Diode reverse", "µA", None, "NOT_TESTED", "open (SLIDE 5)",
                            "reverse diode step not in the firmware double-pulse sequence", "—")
    trip = [x for x in ev if x["name"] == "DESAT_TRIP_FIRMWARE"]
    flt = [x for x in ev if x["name"] == "DRIVER_FAULT_INPUT"]
    if trip:
        tt = trip[0]["t_us"]
        last_on = max(e * 1e6 for e in ds.edges_s[0::2] if e * 1e6 <= tt)
        out["protection"] = Tile("protection", "Desat turn-off", "µs", tt - last_on, "OUT_OF_LIMIT", "≤ 10 µs (SLIDE 5/8)",
                                 f"SPURIOUS DESAT trip {tt - last_on:.3g} µs after the ON command at {last_on:.4g} µs on a HEALTHY record: "
                                 "blanking shorter than the modelled Vce fall", "SIMULATED")
    elif flt:
        out["protection"] = Tile("protection", "Desat turn-off", "µs", m.get("fault_to_offcmd_us", {}).get("value"), "NO_LIMIT",
                                 "≤ 10 µs (SLIDE 5/8)", "injected FAULT-input logic test: firmware off-command latency only, "
                                 "not the device turn-off", "SIMULATED")
    else:
        out["protection"] = Tile("protection", "Desat turn-off", "µs", None, "NOT_TESTED", "≤ 10 µs (SLIDE 5/8)",
                                 "not exercised: no saturation fault in the record (no spurious trip either)", "—")
    out["driver"] = Tile("driver", "Driver power", "W", None, "NOT_TESTED", "≤ 20 W (SLIDE 5)",
                         "gate current not sampled by the firmware front end", "—")
    for k, lab, unit in SLIDE_TILES:     # keys the firmware sequence does not measure
        out.setdefault(k, Tile(k, lab, unit, None, "NOT_TESTED", SLIDE.get(k, "—"), "not measured by the firmware sequence", "—"))
    return [out[k] for k, _, _ in SLIDE_TILES]


def tiles_from_firmware(res: dict, ds: D.Dataset) -> list[Tile]:
    """Firmware (C++ core on the virtual STM32G474 board) results. Values are SIMULATED via the modelled ADC."""
    m, ev = res["meas"], res["events"]
    peak_i = abs(m.get("peak_ic_A", {}).get("value") or 0.0)
    out = []
    for key, label, unit in TILES:
        if key == "V_CE_sat" and m.get("vce_sat_V", {}).get("value") is not None:
            out.append(Tile(key, label, "V", m["vce_sat_V"]["value"], "NO_LIMIT", "no approved limit",
                            f"firmware VCE_CLAMP mean at {m['vce_sat_at_A']['value']:.4g} A", "SIMULATED"))
        elif key == "V_f" and m.get("diode_vf_V", {}).get("value") is not None:
            i_d = m["diode_vf_at_A"]["value"] or 0.0
            if i_d <= max(0.01 * peak_i, 1e-3):
                out.append(Tile(key, label, "V", None, "NOT_TESTED", "—",
                                f"not applicable: diode not conducting in this run (Id = {i_d:.3g} A)", "—"))
            else:
                out.append(Tile(key, label, "V", m["diode_vf_V"]["value"], "NO_LIMIT", "no approved limit",
                                f"firmware VSW-VBUS mean at {i_d:.4g} A (kV-range channels: coarse)", "SIMULATED"))
        elif key == "t_trip":
            trip = [e for e in ev if e["name"] == "DESAT_TRIP_FIRMWARE"]
            flt = [e for e in ev if e["name"] == "DRIVER_FAULT_INPUT"]
            if trip:
                t = trip[0]["t_us"]
                last_on = max(e * 1e6 for e in ds.edges_s[0::2] if e * 1e6 <= t)
                out.append(Tile(key, label, "µs", t - last_on, "OUT_OF_LIMIT", "no DESAT expected on a healthy record",
                                f"FALSE DESAT trip {t - last_on:.3g} µs after ON command at {last_on:.4g} µs: "
                                "blanking shorter than modelled Vce fall", "SIMULATED"))
            elif flt:
                lat = m.get("fault_to_offcmd_us", {}).get("value")
                out.append(Tile(key, label, "µs", lat, "NO_LIMIT", "logic test only",
                                "injected FAULT-input test signal: firmware off-command latency (polling), not device protection",
                                "SIMULATED"))
            else:
                out.append(Tile(key, label, "µs", None, "NOT_TESTED", "—",
                                "not exercised: no short-circuit applied; real 10 µs path is driver DESAT + HRTIM fault (hardware)", "—"))
        else:
            out.append(Tile(key, label, unit, None, "NOT_TESTED", "—",
                            "not part of the firmware double-pulse sequence", "—"))
    return out


def _static_tiles(ds: D.Dataset, out: list[Tile]) -> tuple[list[Tile], dict | None]:
    """Overlay datasheet-condition static checks (testcell.run_static_checks) when they exist for this device."""
    sc = D.latest_static_checks(ds.params.get("schema", ""))
    if not sc:
        return out, None
    folder, v = sc
    L = ds.params.get("datasheetLimits") or {}
    by = {t.key: t for t in out}
    src = f"static_checks run {folder.name} ({v.get('status')})"
    if v.get("VGEth_V") is not None and L:
        x = v["VGEth_V"]
        ok = L["VGEth_min_V"] <= x <= L["VGEth_max_V"]
        by["V_GE_th"] = Tile("V_GE_th", "Gate threshold", "V", x, "IN_LIMIT" if ok else "OUT_OF_LIMIT",
                             f"{L['VGEth_min_V']} – {L['VGEth_max_V']} V (DATASHEET, representative device)",
                             f"VGE at Ic = {v['VGEth_at_Ic_A']:.4g} A, Vce = {v['VGEth_at_Vce_V']:.4g} V, 25 °C; "
                             f"model input Vth = {v.get('VGEth_model_input_V')} V; {src}", "SIMULATED")
    sat25 = next((e for e in (v.get("VCEsat") or []) if e.get("T_C") == 25), None)
    sat150 = next((e for e in (v.get("VCEsat") or []) if e.get("T_C") == 150), None)
    independent150 = sat150 is not None and sat150.get("calibration_target_V") is None
    if independent150 and L.get("VCEsat_max150_V"):
        x = sat150["Vce_V"]
        ok = x <= L["VCEsat_max150_V"]
        by["V_CE_sat"] = Tile("V_CE_sat", "Vce(sat) @150 °C", "V", x, "IN_LIMIT" if ok else "OUT_OF_LIMIT",
                              f"≤ {L['VCEsat_max150_V']} V at {L['VCEsat_IC_A']} A, 150 °C (DATASHEET, representative device)",
                              f"model PREDICTION (calibrated at 25/125 °C), current clamp {sat150['Ic_A']:.5g} A, VGE 15 V"
                              + (f"; 25 °C: {sat25['Vce_V']:.4g} V" if sat25 else "") + f"; {src}", "SIMULATED")
    elif sat25:
        by["V_CE_sat"] = Tile("V_CE_sat", "Vce(sat)", "V", sat25["Vce_V"], "NO_LIMIT",
                              "datasheet gives only typ 2.60 V at 25 °C (max only at 150 °C)",
                              f"current clamp {sat25['Ic_A']:.5g} A, VGE 15 V, 25 °C; {src}", "SIMULATED")
    tiles = [by[t.key] for t in out]
    ices25 = next((e for e in (v.get("ICES") or []) if e.get("T_C") == 25), None)
    if ices25 and L:
        x = ices25["Ic_A"] * 1e3
        ok = ices25["Ic_A"] <= L["ICES_max_A"]
        tiles.append(Tile("I_CES", "Collector leakage ICES", "mA", x, "IN_LIMIT" if ok else "OUT_OF_LIMIT",
                          f"≤ {L['ICES_max_A'] * 1e3:g} mA at {L['ICES_VCE_V']} V (DATASHEET, representative device)",
                          f"VGE = 0, Vce = {ices25['Vce_V']:.5g} V, 25 °C (model calibrated at 125/150 °C, extrapolated); {src}",
                          "SIMULATED"))
    return tiles, {"folder": folder, "validation": v}


# Wabtec hackathon brief (references/NU IEEE 2026 IGBT test cell_AK_Final), slides 5 and 8: the primary source.
SLIDE = {
    "gate": "Slide 5/8: gate drive +15 V on, -15 V off",
    "vth": "Slide 8: fully on above roughly +4 to +7 V",
    "didt": "Slide 5: max di/dt 0 - 5000 A/µs",
    "diode_fwd": "Slide 5: free-wheeling diode 0.2 V to 0.8 V",
    "diode_rev": "Slide 5: free-wheeling diode reverse direction - open",
    "protection": "Slide 5/8: switch turns off 10 µs after a saturation fault",
    "insulation": "Slide 5: busbar insulation leakage current up to 2 mA",
    "driver": "Slide 5: driver power up to 20 W",
}
# Busbar insulation (slide 5) is a hipot measurement on hardware; by team decision (2026-10-17) it is not part
# of the simulated tester's required set.
SLIDE_TILES = [("gate", "Gate drive ±15 V", "V"), ("vth", "Turn-on threshold", "V"), ("didt", "Max di/dt", "A/µs"),
               ("diode_fwd", "Diode forward", "V"), ("diode_rev", "Diode reverse", "µA"),
               ("driver", "Driver power", "W"),
               ("desat_trip", "DESAT detection", "µs"), ("desat_gateoff", "DESAT gate turn-off", "µs")]
# Slide items that ARE simulated but excluded from the verdict, by team decision (2026-10-18), because a known model
# limitation decides the result rather than the device. Shown with value, limit and reason; the limit is unchanged.
EXCLUDED_TILES = {
    "protection": "Excluded from verdict, known model limitation: the IGBT turn-off tail is not calibrated (model "
                  "current fall ≈ 22 µs vs datasheet tf ≤ 0.70 µs), and that tail sets the current-clearing time. "
                  "The driver's gate turn-off after detection is a separate tile (DESAT gate turn-off), which is in the verdict.",
}
# ASSUMED switching frequency for the driver-power check: the slides give none. 3.3 kV traction IGBTs typically
# switch at a few hundred Hz to ~1 kHz; 1 kHz is the conservative end.
ASSUMED_FSW_HZ = 1000.0


def slide_tiles_from_sim(ds: D.Dataset) -> list[Tile]:
    """Tester tiles that follow the Wabtec slide 5/8 parameter list, filled from simulation runs only."""
    out = _slide_out_from_sim(ds)
    tiles = [out[k] for k, _, _ in SLIDE_TILES]
    return tiles


def excluded_tiles_from_sim(ds: D.Dataset) -> list[Tile]:
    """Simulated slide items kept out of the verdict (EXCLUDED_TILES), with the reason in the note."""
    out = _slide_out_from_sim(ds)
    tiles = []
    for k, reason in EXCLUDED_TILES.items():
        if k == "protection" and out.get("_no_trip"):          # nothing was interrupted; desat_trip carries the FAIL
            continue
        if out[k].state == "NOT_TESTED":      # nothing was run, so there is no result to set aside
            continue
        t = out[k]
        tiles.append(Tile(t.key, t.label, t.unit, t.value, t.state, t.limit, reason + " " + t.note, t.provenance))
    return tiles


def _slide_out_from_sim(ds: D.Dataset) -> dict:
    schema = ds.params.get("schema", "")
    x = F.load_dynamic(ds.csv)
    p, e = ds.params, ds.edges_s
    t = x["t"]
    sw = F.switching_times(x, p, e)
    out: dict[str, Tile] = {}
    # gate drive: actual terminal plateaus vs slide nominal; tolerance = the existing model check (analyze_dynamic.m)
    on = (t > e[1] - 10e-6) & (t < e[1] - 2e-6)
    off = (t > e[2] - 10e-6) & (t < e[2] - 2e-6)
    von, voff = float(np.mean(x["Vge"][on])), float(np.mean(x["Vge"][off]))
    err = max(abs(von - 15.0), abs(voff + 15.0))
    out["gate"] = Tile("gate", "Gate drive ±15 V", "V", von if err < 0.02 or abs(von - 15.0) >= abs(voff + 15.0) else voff, "IN_LIMIT" if err < 0.02 else "OUT_OF_LIMIT",
                       "+15 / −15 V (SLIDE 5/8); tolerance 0.02 V = model check in analyze_dynamic.m",
                       f"terminal Vge ON {von:.4f} V, OFF {voff:.4f} V (dynamic run {ds.folder.name})", "SIMULATED")
    # threshold (static checks, if available for this device)
    sc = D.latest_static_checks(schema)
    if sc and sc[1].get("VGEth_V") is not None:
        v = sc[1]["VGEth_V"]
        ok = 4.0 <= v <= 7.0
        out["vth"] = Tile("vth", "Turn-on threshold", "V", v, "IN_LIMIT" if ok else "OUT_OF_LIMIT",
                          "+4 … +7 V (SLIDE 8)",
                          f"VGE at Ic = {sc[1]['VGEth_at_Ic_A']:.4g} A, Vce = {sc[1]['VGEth_at_Vce_V']:.4g} V, 25 °C "
                          f"(datasheet 5.8–6.8 V); {sc[0].name}", "SIMULATED")
    else:
        out["vth"] = Tile("vth", "Turn-on threshold", "V", float(p.get("Vth_V", float("nan"))), "NO_LIMIT", "+4 … +7 V (SLIDE 8)",
                          "no static threshold run for this device: value shown is the model INPUT, not a measurement", "ASSUMED")
    # di/dt (10-90 % slopes of the hard turn-on and OFF-1)
    d = sw["didt_max_A_per_s"] / 1e6
    out["didt"] = Tile("didt", "Max di/dt", "A/µs", d, "IN_LIMIT" if d <= 5000 else "OUT_OF_LIMIT", "≤ 5000 A/µs (SLIDE 5)",
                       f"0.8·I/t(10–90 %): turn-on {sw['didt_on_A_per_s'] / 1e6:.4g} A/µs at {sw['on_current_A']:.4g} A, "
                       f"turn-off {sw['didt_off_A_per_s'] / 1e6:.4g} A/µs; Ic fall tf = {sw['tf_s'] * 1e6:.3g} µs", "SIMULATED")
    # diode (DMM emulation)
    dt = D.latest_diode_test(schema)
    if dt:
        v = dt[1]
        okf = 0.2 <= v["forward_V"] <= 0.8
        out["diode_fwd"] = Tile("diode_fwd", "Diode forward", "V", v["forward_V"], "IN_LIMIT" if okf else "OUT_OF_LIMIT",
                                "0.2 … 0.8 V (SLIDE 5)",
                                f"at {v['forward_at_A'] * 1e3:.3g} mA (ASSUMED DMM test current); {v.get('model_note', '')} {dt[0].name}",
                                "SIMULATED")
        out["diode_rev"] = Tile("diode_rev", "Diode reverse", "µA", abs(v["reverse_A"]) * 1e6,
                                "IN_LIMIT" if v["reverse_open"] else "OUT_OF_LIMIT", "open (SLIDE 5)",
                                f"{abs(v['reverse_A']) * 1e6:.3g} µA at {v['reverse_V']:.3g} V: cannot carry the 1 mA DMM test current → open",
                                "SIMULATED")
    else:
        for k, lab in (("diode_fwd", "Diode forward"), ("diode_rev", "Diode reverse")):
            out[k] = Tile(k, lab, "", None, "NOT_TESTED", SLIDE[k], "no diode test run for this device", "—")
    # protection: closed-loop DESAT short-circuit run (testcell.run_desat_test)
    dz = D.latest_run("desat_test_*", schema)
    LIM10 = "≤ 10 µs after detection (SLIDE 5/8 + slide 8 notes)"
    if dz and dz[1].get("tripped") is False:
        # Protection never acted: a detection failure, independent of the modelled current tail.
        v = dz[1]
        out["desat_trip"] = Tile("desat_trip", "DESAT detection", "µs", None, "OUT_OF_LIMIT", "trips during the short circuit",
                                 f"DESAT NEVER TRIPPED: the short lasted the full {v.get('short_duration_without_protection_s', float('nan')) * 1e6:.3g} µs "
                                 f"command pulse; peak Ic {v['peak_Ic_A']:.4g} A, short-circuit energy {v['sc_energy_J']:.4g} J. {dz[0].name}",
                                 "SIMULATED")
        out["desat_gateoff"] = Tile("desat_gateoff", "DESAT gate turn-off", "µs", None, "NOT_TESTED", LIM10,
                                    "no DESAT trip, so the driver never turned the gate off", "—")
        out["protection"] = Tile("protection", "Desat current interruption", "µs", None, "NOT_TESTED", LIM10, "no DESAT trip", "—")
        out["_no_trip"] = True
    elif dz:
        v = dz[1]
        cfg = v["config"]
        out["desat_trip"] = Tile("desat_trip", "DESAT detection", "µs", v["trip_after_on_s"] * 1e6, "IN_LIMIT", "trips during the short circuit",
                                 f"fault latched {v['trip_after_on_s'] * 1e6:.3g} µs after gate-on into a short at {v.get('bus_at_turn_on_V', p['bus_V']):.4g} V "
                                 f"(threshold {cfg['threshold_V']:g} V, blanking {cfg['blanking_s'] * 1e6:g} µs, both ASSUMED). {dz[0].name}",
                                 "SIMULATED")
        # Driver response: detection -> VGE below the threshold, read from the run's raw waveform export.
        wf = dz[0] / "desat_waveforms.csv"
        if wf.exists():
            w = np.genfromtxt(wf, delimiter=",", names=True)
            tt, vge = w["time_s"], w["Vge_V"]
            after = np.nonzero((tt > v["trip_time_s"]) & (vge < float(p["Vth_V"])))[0]
            goff = (tt[after[0]] - v["trip_time_s"]) * 1e6 if after.size else None
            out["desat_gateoff"] = Tile("desat_gateoff", "DESAT gate turn-off", "µs", goff,
                                        "NOT_TESTED" if goff is None else ("IN_LIMIT" if goff <= 10 else "OUT_OF_LIMIT"), LIM10,
                                        f"detection → VGE below Vth ({float(p['Vth_V']):g} V): the driver has switched the IGBT channel off "
                                        f"(R_off {p['RdriverOff_Ohm']:g} Ω). Gate turn-off only; current interruption is shown separately. {wf.parent.name}",
                                        "SIMULATED")
        else:
            out["desat_gateoff"] = Tile("desat_gateoff", "DESAT gate turn-off", "µs", None, "NOT_TESTED", LIM10,
                                        "DESAT run has no waveform export (desat_waveforms.csv)", "—")
        # Slide 8 speaker notes: "turns the healthy IGBT off 10 microseconds after the companion failure is detected"
        # -> current interruption measured from the DESAT detection (latch) to Ic < 10 % of peak.
        toff = (v["desat_turnoff_s"] - v["trip_after_on_s"]) * 1e6
        out["protection"] = Tile("protection", "Desat current interruption", "µs", toff, "IN_LIMIT" if toff <= 10 else "OUT_OF_LIMIT", LIM10,
                                 f"detection → Ic < 10 % of peak; peak Ic {v['peak_Ic_A']:.4g} A (short-circuit level not validated). "
                                 f"Slow current fall = modelled tail (tf 22 µs vs datasheet ≤ 0.7 µs). {dz[0].name}",
                                 "SIMULATED")
    else:
        for k, lab in (("desat_trip", "DESAT detection"), ("desat_gateoff", "DESAT gate turn-off"), ("protection", "Desat current interruption")):
            out[k] = Tile(k, lab, "µs", None, "NOT_TESTED", LIM10, "no DESAT short-circuit run (testcell.run_desat_test) for this device", "—")
    pw = sw["driver_energy_per_cycle_J"] * ASSUMED_FSW_HZ
    out["driver"] = Tile("driver", "Driver power", "W", pw, "IN_LIMIT" if pw <= 20 else "OUT_OF_LIMIT", "≤ 20 W (SLIDE 5)",
                         f"Qg·ΔV = {abs(sw['gate_charge_C']) * 1e6:.4g} µC × {p['gateOn_V'] - p['gateOff_V']:g} V per cycle "
                         f"× f_sw {ASSUMED_FSW_HZ / 1e3:g} kHz (ASSUMED; slides give none). Gate-charge power only, driver "
                         f"quiescent losses not modelled. 20 W reached at f_sw ≈ {20 / sw['driver_energy_per_cycle_J'] / 1e3:.4g} kHz",
                         "SIMULATED + ASSUMED f_sw")
    return out


def split_simulated(tiles: list[Tile]) -> tuple[list[Tile], list[Tile]]:
    """Group checked/pending tiles for display; always pass the FULL set to verdict."""
    checked = [t for t in tiles if t.state in ("IN_LIMIT", "OUT_OF_LIMIT")]
    return checked, [t for t in tiles if t not in checked]


def tiles_from_sim(ds: D.Dataset) -> list[Tile]:
    return slide_tiles_from_sim(ds)


def datasheet_tiles_from_sim(ds: D.Dataset) -> list[Tile]:
    """Secondary view: datasheet min/max checks of the representative device (details tab)."""
    return _static_tiles(ds, _tiles_from_dynamic(ds))[0]


def static_checks_for(ds: D.Dataset):
    return D.latest_static_checks(ds.params.get("schema", ""))


def _tiles_from_dynamic(ds: D.Dataset) -> list[Tile]:
    pk = sim_packet(ds)
    out = []
    for key, label, unit in TILES:
        if key in pk and pk[key]["value"] is not None:
            v = pk[key]["value"]
            prov = "ASSUMED" if key == "V_GE_th" else "SIMULATED"
            at = f" at {pk[key]['at_A']:.4g} A" if pk[key].get("at_A") is not None else ""
            out.append(Tile(key, label, pk[key]["unit"], v, "NO_LIMIT", "no approved limit", pk[key]["reason"] + at, prov))
        else:
            reason = pk[key]["reason"] if key in pk else "not modelled (outside electrical simulation scope)"
            out.append(Tile(key, label, unit, None, "NOT_TESTED", "—", reason, "—"))
    return out

"""IGBT bench tester front end.

    streamlit run app_virtual_lab.py

Top: one tester verdict (PASS / NO-PASS) and per-test tiles. Below: details.
NO-PASS = not cleared: either a test FAILED or something is NOT VERIFIED (not tested / no approved limit).
Data sources are labelled everywhere: SIMULATED / PRESET-DEMO / ASSUMED / MEASURED.
The hardware decision stays INCONCLUSIVE: no Wabtec-approved acceptance limits exist.
"""
from __future__ import annotations

import time

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from igbt_simulation_engine import IGBTSimulationEngine  # teammate engine, used unchanged
from virtual_lab import datasets as D
from virtual_lab import tester as TT
from virtual_lab.component import render_virtual_lab

st.set_page_config(page_title="IGBT Bench Tester", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.block-container{padding-top:1.4rem}
.vbox{border-radius:10px;padding:18px 24px;margin:4px 0 10px;display:flex;align-items:center;gap:28px;flex-wrap:wrap}
.vbox.pass{background:#0f3d24;border:2px solid #2bd97c}
.vbox.nopass{background:#43121a;border:2px solid #ff4d5e}
.vbox.unverified{background:#4a3407;border:2px solid #ffb000}
.vbig{font:800 46px/1 'Segoe UI',system-ui,sans-serif;letter-spacing:.06em;color:#fff}
.vsub{font:600 16px 'Segoe UI',system-ui,sans-serif;color:#f1f1f1}
.vsmall{font:13px 'Segoe UI',system-ui,sans-serif;color:#e0e0e0;opacity:.9;margin-top:4px}
.chip{display:inline-block;font:600 11.5px Consolas,monospace;padding:4px 8px;border-radius:4px;margin:2px 4px 2px 0;border:1px solid}
.c-demo{color:#b07800;border-color:#b07800;background:#fff7e0}
.c-sim{color:#126b3d;border-color:#1f8f55;background:#e6f7ee}
.c-inc{color:#9a5b00;border-color:#d48a00;background:#fff3dc}
.c-src{color:#2b4a6f;border-color:#6d8fb5;background:#eef4fb}
.tiles{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:10px;margin:6px 0 4px}
.tile{border-radius:8px;padding:10px 12px;border:1px solid #d8dde3;background:#f7f8fa;min-height:96px}
.tile .tl{font:600 12px 'Segoe UI',sans-serif;letter-spacing:.05em;text-transform:uppercase;color:#4a5562;display:flex;justify-content:space-between}
.tile .tv{font:700 22px Consolas,monospace;margin:4px 0 2px;color:#111}
.tile .tn{font:11.5px 'Segoe UI',sans-serif;color:#5b6672}
.tile.IN_LIMIT{background:#e8f8ef;border-color:#2bd97c}
.tile.OUT_OF_LIMIT{background:#fde9ec;border-color:#ff4d5e}
.tile.NO_LIMIT{background:#eef2f7;border-color:#9fb0c4}
.tile.NOT_TESTED{background:#f3f3f3;border-color:#d0d0d0;border-style:dashed}
.tile.NOT_TESTED .tv{color:#9a9a9a;font-size:16px}
.st-dot{width:11px;height:11px;border-radius:50%;display:inline-block}
@media (max-width:900px){.tiles{grid-template-columns:repeat(2,1fr)}.vbig{font-size:34px}}
</style>
""", unsafe_allow_html=True)

STATE_TXT = {"IN_LIMIT": ("in limit", "#2bd97c"), "OUT_OF_LIMIT": ("OUT OF LIMIT", "#ff4d5e"),
             "NO_LIMIT": ("no approved limit", "#7d93ad"), "NOT_TESTED": ("not tested / not modelled", "#b0b0b0")}
PRESETS = ["Healthy Module (Pass)", "Bond Wire Lift-Off (Fail)", "Gate Oxide Breakdown (Fail)", "Solder Layer Delamination (Fail)"]


# ---------------------------------------------------------------- sidebar
st.sidebar.header("Bench control")
SRC_SIM, SRC_FW, SRC_PRE = "MATLAB simulation results", "MCU firmware (simulated STM32G474)", "Diagnostic presets (teammate)"
source = st.sidebar.radio("Data source", [SRC_SIM, SRC_FW, SRC_PRE],
                          help="Physical DAQ is not implemented. The firmware source runs the C++ tester core on a "
                               "virtual board that samples a MATLAB record through a modelled 12-bit ADC.")
st.sidebar.button("Physical DAQ — NOT IMPLEMENTED", disabled=True, width="stretch",
                  help="No acquisition hardware interface exists yet. Nothing in this app is MEASURED data.")
module_id = st.sidebar.text_input("Module serial / barcode", value="WB-2026-IGBT-088")

if source == SRC_FW:
    all_ds = D.discover()
    # Tester lists only the locomotive-class device: the slide 5/8 checks do not apply to the 48 V assumed device.
    dyn = [d for d in all_ds if d.selectable and d.kind in ("dynamic_rl", "dynamic_r") and D.is_traction(d)]
    labels = {d.id: f"{d.label}  [{d.status}]" for d in dyn}
    ds_id = st.sidebar.selectbox("Simulated device record", [d.id for d in dyn], format_func=lambda i: labels[i])
    adc_rate = st.sidebar.select_slider("ADC rate per channel", options=[0.5e6, 1e6, 2e6, 4e6], value=2e6,
                                        format_func=lambda v: f"{v / 1e6:g} MS/s")
    blank_us = st.sidebar.number_input("DESAT blanking (µs) — ASSUMED", 0.5, 20.0, 5.0, 0.5,
                                       help="Time after each turn-on command during which the DESAT comparator is ignored.")
    thr_V = st.sidebar.number_input("DESAT threshold (V) — ASSUMED", 1.0, 50.0, 9.0, 0.5)
    inj = st.sidebar.checkbox("Inject driver FAULT input (logic test)",
                              help="Asserts the FAULT input at a chosen time to test the firmware abort path. "
                                   "This is a test signal, not a simulated device fault.")
    inj_us = st.sidebar.number_input("FAULT input time (µs)", 0.0, 1500.0, 200.0, 10.0) if inj else None
    run = st.sidebar.button("▶ RUN FIRMWARE SEQUENCE", type="primary", width="stretch")
    st.sidebar.caption("C++ firmware core (firmware/src/tester.cpp) on a virtual board. The core also compiles for "
                       "Cortex-M4F; it has not run on a real STM32G474.")
elif source.startswith("Diagnostic"):
    preset = st.sidebar.selectbox("Condition preset", PRESETS,
                                  help="Teammate engine: synthetic values generated around preset means (PRESET-DEMO).")
    run = st.sidebar.button("▶ RUN TEST SEQUENCE", type="primary", width="stretch")
    st.sidebar.caption("PRESET-DEMO data: synthetic values from igbt_simulation_engine.py, judged against DEMO limits "
                       "(not Wabtec-approved).")
else:
    all_ds = D.discover()
    # Tester lists only the locomotive-class device: the slide 5/8 checks do not apply to the 48 V assumed device.
    dyn = [d for d in all_ds if d.selectable and d.kind in ("dynamic_rl", "dynamic_r") and D.is_traction(d)]
    labels = {d.id: f"{d.label}  [{d.status}]" for d in dyn}
    ids = [d.id for d in dyn]
    ds_id = st.sidebar.selectbox("Simulation run", ids, format_func=lambda i: labels[i],
                                 index=ids.index("traction_rl") if "traction_rl" in ids else 0)
    with st.sidebar.expander("Excluded runs (never shown as valid)"):
        for d in all_ds:
            if not d.selectable and D.is_traction(d):
                st.markdown(f"- `{d.id}` — **{d.status}**: {d.reason}")
    st.sidebar.caption("SIMULATED data from MATLAB/Simscape results folders, judged against the Wabtec slide 5/8 values. "
                       "Required checks without evidence remain visible; the hardware decision stays INCONCLUSIVE.")

st.sidebar.markdown("---")
st.sidebar.markdown("**Reference conditions** (Wabtec slides 5/8)\n\n- Gate drive +15 V / −15 V\n- Protection reference ≈ 10 µs\n\n"
                    "These are test conditions, not acceptance limits.")


# ---------------------------------------------------------------- data -> tiles
def _stable_hash(s) -> int:
    """Process-independent replacement for builtins.hash (which is salted per interpreter start)."""
    import hashlib
    return int.from_bytes(hashlib.sha256(str(s).encode("utf-8")).digest()[:8], "big")


# The teammate engine seeds numpy with hash(module_id). Shadowing `hash` in that module's namespace makes the
# same serial give the same PRESET-DEMO values after every restart, without editing igbt_simulation_engine.py.
import igbt_simulation_engine as _engine  # noqa: E402
_engine.hash = _stable_hash


def run_preset(mid, pre):
    return IGBTSimulationEngine.run_full_diagnostic(module_id=mid, condition_preset=pre)


if source == SRC_FW:
    from virtual_lab import mcu_link as ML
    ds = D.get(ds_id)
    fw_cfg = (ds_id, adc_rate, blank_us, thr_V, inj_us)
    if run:
        with st.spinner("Firmware running on virtual STM32G474 board…"):
            st.session_state["fw_result"] = (fw_cfg, ML.run_double_pulse(ds, adc_rate, thr_V, blank_us, inj_us))
    stored = st.session_state.get("fw_result")
    if stored is None:
        st.title("IGBT Bench Tester")
        st.info("Choose a simulated device record and press **RUN FIRMWARE SEQUENCE**.")
        st.stop()
    r_cfg, fw = stored
    if r_cfg[0] != ds_id:
        ds = D.get(r_cfg[0])
    tiles = TT.slide_tiles_from_firmware(fw, ds)
    _, pending = TT.split_simulated(tiles)
    v = TT.verdict(tiles, "SLIDE")
    src_chips = ('<span class="chip c-sim">DATA: SIMULATED record → modelled ADC → C++ firmware</span>'
                 f'<span class="chip c-src">{fw.get("firmware", {}).get("target", "firmware")} · sequence '
                 f'{fw["status"].get("sequence", "?")}</span><span class="chip c-demo">LIMITS: Wabtec brief slides 5/8</span>')
    subject = f"Module {module_id} · simulated device: {ds.label}"
    stale = r_cfg != fw_cfg
elif source.startswith("Diagnostic"):
    if run:
        box = st.empty()
        for i, name in enumerate(["Static sweep", "Double pulse", "Gate driver / desat", "Thermal & acoustic"], 1):
            box.info(f"DEMO sequence {i}/4: {name} … (no hardware or simulation is executed)")
            time.sleep(0.25)
        box.empty()
        st.session_state["preset_result"] = (module_id, preset, run_preset(module_id, preset))
    stored = st.session_state.get("preset_result")
    if stored is None:
        st.title("IGBT Bench Tester")
        st.info("Choose a preset in the sidebar and press **RUN TEST SEQUENCE**.")
        st.stop()
    r_mid, r_pre, res = stored
    tiles, pending = TT.tiles_from_preset(res), []
    v = TT.verdict(tiles, "DEMO")
    src_chips = '<span class="chip c-demo">DATA: PRESET-DEMO (synthetic)</span><span class="chip c-demo">LIMITS: DEMO — not Wabtec-approved</span>'
    subject = f"Module {r_mid} · preset “{r_pre}”"
    stale = (r_mid, r_pre) != (module_id, preset)
else:
    ds = D.get(ds_id)
    tiles = TT.tiles_from_sim(ds)
    _, pending = TT.split_simulated(tiles)
    v = TT.verdict(tiles, "SLIDE")
    sc = TT.static_checks_for(ds)
    src_chips = ('<span class="chip c-sim">DATA: SIMULATED (MATLAB/Simscape)</span>'
                 f'<span class="chip c-src">RUN {ds.folder.name} · model checks {ds.status}</span>'
                 + (f'<span class="chip c-src">STATIC CHECKS {sc[0].name} · {sc[1].get("status")}</span>' if sc else "")
                 + '<span class="chip c-demo">LIMITS: Wabtec brief slides 5/8 (test list and values)</span>')
    subject = f"Module {module_id} · simulated device: {ds.label}"
    stale = False

# ---------------------------------------------------------------- TOP: verdict + tiles
st.title("IGBT Bench Tester")
if stale:
    st.warning("Sidebar inputs changed since the last run. The verdict below is still for the previous run — press RUN again.")
cls = "pass" if v["verdict"] == "PASS" else ("nopass" if v["reason"] == "FAILED" else "unverified")
st.markdown(f"""
<div class="vbox {cls}">
  <div class="vbig">{v['verdict']}</div>
  <div>
    <div class="vsub">{v['detail']}</div>
    <div class="vsmall">{subject}</div>
    <div class="vsmall">{'Tester rule: all required electrical checks must have results and applicable limits. Missing checks keep the result NOT VERIFIED; slide comparisons do not certify hardware.' if v['limits'] == 'SLIDE' else 'Tester rule: PASS only when every test ran and is inside its limit; anything else is NO-PASS (not cleared).'}
    Hardware decision: <b>{v['hardware_decision']}</b>{' — DEMO limits are not Wabtec-approved' if v['limits'] == 'DEMO' else ' — simulation of a representative device, not a measured module'}.</div>
  </div>
</div>
{src_chips}<span class="chip c-inc">HARDWARE: {v['hardware_decision']}</span>
""", unsafe_allow_html=True)


def fmt(t: TT.Tile) -> str:
    if t.value is None:
        return "—"
    # out-of-limit values can sit just past a boundary (e.g. 0.80001 V vs 0.8 V): show enough digits to see it
    return f"{t.value:.6g} {t.unit}" if t.state == "OUT_OF_LIMIT" else f"{t.value:.4g} {t.unit}"


html = '<div class="tiles">'
for t in tiles:
    txt, col = STATE_TXT[t.state]
    html += (f'<div class="tile {t.state}" title="{t.note} | limit: {t.limit} | provenance: {t.provenance}">'
             f'<div class="tl"><span>{t.label}</span><span class="st-dot" style="background:{col}"></span></div>'
             f'<div class="tv">{fmt(t)}</div><div class="tn">{txt} · {t.provenance}</div></div>')
st.markdown(html + "</div>", unsafe_allow_html=True)
if pending:
    st.caption("Required checks awaiting evidence or applicable limits: " + ", ".join(t.label for t in pending) + ". These checks prevent an overall PASS.")
st.caption("Green = inside limit · Red = outside limit · Blue-grey = value available but no approved limit · "
           "Grey dashed = not tested / not modelled. Hover a tile for its definition and provenance.")

# ---------------------------------------------------------------- DETAILS
st.markdown("### Details")
if source.startswith("Diagnostic"):
    t1, t2, t3 = st.tabs(["Parameter table", "Waveforms (PRESET-DEMO)", "Report (DEMO)"])
    with t1:
        st.dataframe(pd.DataFrame([{"Parameter": p.name, "Symbol": p.symbol, "Value": f"{p.measured_value} {p.unit}",
                                    "DEMO limit": f"{p.pass_min} – {p.pass_max} {p.unit}",
                                    "Result vs DEMO limit": "in limit" if p.passed else "OUT OF LIMIT",
                                    "Purpose": p.description, "Provenance": "PRESET-DEMO"} for p in res.parameters.values()]),
                     hide_index=True, width="stretch")
        st.caption("Values are random draws around preset means in igbt_simulation_engine.py. Limits are the teammate's "
                   "demo limits. Note: the 2 mA figure on slide 5 is busbar insulation leakage, not an IGBT I_GES rating.")
    with t2:
        wf = res.waveforms
        c1, c2 = st.columns(2)
        with c1:
            tt, vv = wf["desat_protection"]
            f, a = plt.subplots(figsize=(6, 3)); a.plot(tt, vv, lw=2); a.axvline(10, ls="--", c="gray", label="10 µs reference (slides 5/8)")
            a.set_xlabel("Time (µs)"); a.set_ylabel("Vge (V)"); a.set_title("Desat trip — PRESET-DEMO (synthetic)"); a.grid(alpha=.4); a.legend(fontsize=8)
            st.pyplot(f); plt.close(f)
            fz, z = wf["thermal_impedance"]
            f, a = plt.subplots(figsize=(6, 3)); a.semilogx(fz, z, lw=2, c="#ff7f0e"); a.axhline(0.05, ls="--", c="r", label="DEMO limit 0.050 K/W")
            a.set_xlabel("Time (ms)"); a.set_ylabel("Zth (K/W)"); a.set_title("Thermal impedance — PRESET-DEMO (synthetic)"); a.grid(alpha=.4, which="both"); a.legend(fontsize=8)
            st.pyplot(f); plt.close(f)
        with c2:
            vd, idd = wf["diode_iv_curve"]
            f, a = plt.subplots(figsize=(6, 3)); a.plot(vd, idd, lw=2, c="#2ca02c"); a.axvspan(0.2, 0.8, color="g", alpha=.12, label="DEMO window 0.2–0.8 V")
            a.set_xlabel("Vf (V)"); a.set_ylabel("If (A)"); a.set_ylim(0, 45); a.set_title("Diode I-V — PRESET-DEMO (synthetic)"); a.grid(alpha=.4); a.legend(fontsize=8)
            st.pyplot(f); plt.close(f)
            fr, am = wf["acoustic_spectrum"]
            f, a = plt.subplots(figsize=(6, 3)); a.plot(fr, am, c="#9467bd"); a.axvspan(1320, 1370, color="g", alpha=.1, label="DEMO band")
            a.set_xlabel("Frequency (Hz)"); a.set_ylabel("Amplitude (dB)"); a.set_title("Acoustic — PRESET-DEMO (synthetic)"); a.grid(alpha=.4); a.legend(fontsize=8)
            st.pyplot(f); plt.close(f)
    with t3:
        lines = ["=" * 78, "DEMONSTRATION REPORT — NOT A VALID INSPECTION CERTIFICATE", "=" * 78,
                 f"Generated : {time.strftime('%Y-%m-%d %H:%M:%S')}", f"Module    : {r_mid}", f"Preset    : {r_pre}",
                 "Data      : PRESET-DEMO (synthetic values, igbt_simulation_engine.py)",
                 "Limits    : DEMO limits, not Wabtec-approved", "-" * 78,
                 f"Tester verdict (vs DEMO limits): {v['verdict']} — {v['detail']}",
                 "Hardware decision             : INCONCLUSIVE", "-" * 78]
        for i, p in enumerate(res.parameters.values(), 1):
            lines.append(f"{i}. {p.name:<30} {p.measured_value:>9} {p.unit:<4} DEMO [{p.pass_min} – {p.pass_max}] "
                         f"-> {'in limit' if p.passed else 'OUT OF LIMIT'}")
        lines += ["-" * 78, "Operator action: none. Demonstration output only — not for installation decisions.", "=" * 78]
        txt = "\n".join(lines)
        st.text_area("Report preview", txt, height=300)
        st.download_button("Download DEMO report (.txt)", txt, file_name=f"DEMO_report_{r_mid}.txt", mime="text/plain")
elif source == SRC_FW:
    t1, t2, t3, t4 = st.tabs(["Firmware vs full resolution", "Protocol transcript", "Virtual test bench", "Firmware & hardware notes"])
    with t1:
        ref = ML.reference(ds)
        names = {"vce_sat_V": "Vce(sat), end of pulse 1", "vce_sat_at_A": "  … at Ic", "diode_vf_V": "Diode V_AK, freewheel",
                 "diode_vf_at_A": "  … at Id", "peak_vce_V": "Peak Vce", "peak_ic_A": "Peak Ic",
                 "off1_cmd_to_vce90_us": "OFF-1 command → Vce 90 %", "off1_ic_fall_90_10_us": "OFF-1 Ic fall 90→10 %"}
        rows = []
        for k, n in names.items():
            fv = fw["meas"].get(k, {}).get("value")
            rv = ref[k]
            rows.append({"Quantity": n, "Firmware (ADC)": fv, "Full-resolution record": rv,
                         "Unit": fw["meas"].get(k, {}).get("unit") or ("A" if k.endswith("_A") else "V" if k.endswith("_V") else "µs"),
                         "Difference": None if fv is None else fv - rv})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        fe = fw["front_end"]
        st.caption(f"ADC {fw['config']['adc_rate_hz'] / 1e6:g} MS/s, 12-bit bipolar. ASSUMED front-end full scale: "
                   f"VCE/VSW/VBUS ±{fe['fs_VCE']:g} V (LSB {fe['fs_VCE'] / 2048:.3g} V), VCE_CLAMP ±12 V "
                   f"(LSB {12 / 2048 * 1000:.3g} mV), IC/ID ±{fe['fs_IC']:g} A. Differences are the measurement chain: "
                   "sampling misses ns-scale spikes (peak Vce) and kV-range channels quantise small differences (diode V_AK). "
                   "Full-resolution column: Python on the same CSV.")
        if fw["errors"]:
            st.error("Firmware errors: " + "; ".join(fw["errors"]))
        if any(e["name"] == "DESAT_TRIP_FIRMWARE" for e in fw["events"]):
            st.warning("The firmware DESAT supervision tripped on a HEALTHY simulated record: the modelled Vce falls more "
                       "slowly than the blanking time after turn-on. Longer blanking eats into the device's short-circuit "
                       "withstand time (CM1500HC-66XB datasheet tpSC = 10 µs). For the traction record the slow fall comes "
                       "from the ASSUMED transit time; the datasheet allows td(on)+tr ≤ 1.9 µs. Not hidden by changing defaults.")
    with t2:
        st.code("\n".join(fw["commands"]), language="text")
        st.code("\n".join(__import__("json").dumps(m) for m in fw["lines"]), language="json")
    with t3:
        render_virtual_lab([ds.id], height=1250)
    with t4:
        st.markdown("""
**Architecture (production intent)**
- **Gate-driver board** (isolated, DESAT detection): hard 10 µs short-circuit protection in hardware.
- **STM32G474** (C++): HRTIM double-pulse generation, HRTIM fault input wired to the driver FAULT pin (hardware turn-off),
  ADC1–5 simultaneous sampling with DMA, test sequencing, USB-CDC line protocol.
- **PC (Python)**: operator screen, verdict, reports. Same protocol for the real board and this simulator.

**What has actually been executed**
- `firmware/src/tester.cpp` compiled with clang 21 (`-Wall -Wextra -Werror`) for the host simulator **and** freestanding
  Cortex-M4F (`thumb-freestanding-eabihf`), proving the core builds for the MCU. It has **not** been linked, flashed or run
  on a board.
- `firmware/src/stm32/board_stm32g474.cpp` is a peripheral-mapping **skeleton** (not compiled; needs STM32CubeG4).

**Known measurement-chain lessons from the simulation**
- 2 MS/s cannot capture switching transients; dynamic switching metrics need an oscilloscope/fast digitiser.
- Vce(sat) and diode Vf need dedicated clamp / differential channels; kV-range channels are too coarse.
- DESAT blanking must exceed the real device's Vce fall time but stay well below tpSC.
""")
else:
    t1, t0, t2, t3 = st.tabs(["Virtual test bench", "Slide & datasheet checks", "Diagnostic packet", "Model validation"])
    with t0:
        from virtual_lab import features as FF
        st.markdown("**Slide 5/8 checks** (top tiles) — limits quoted from the Wabtec brief:")
        st.dataframe(pd.DataFrame([{"Check": t.label, "Value": None if t.value is None else round(t.value, 6), "Unit": t.unit,
                                    "Limit (source)": t.limit, "Result": STATE_TXT[t.state][0], "How obtained": t.note,
                                    "Provenance": t.provenance} for t in tiles]), hide_index=True, width="stretch")
        sw = FF.switching_times(FF.load_dynamic(ds.csv), ds.params, ds.edges_s)
        dsmax = {"td_on_s": 1.40, "tr_s": 0.50, "td_off_s": 6.40, "tf_s": 0.70} if ds.params.get("schema") == "testcell.traction_device.v1" else {}
        st.markdown("**Switching times** (datasheet definitions; hard turn-on ON-2, turn-off OFF-1):")
        st.dataframe(pd.DataFrame([{"Quantity": k.replace("_s", ""), "Simulated (µs)": round(sw[k] * 1e6, 4),
                                    "Datasheet max (µs, 150 °C)": dsmax.get(k)} for k in ("td_on_s", "tr_s", "td_off_s", "tf_s")]),
                     hide_index=True, width="stretch")
        dtl = TT.datasheet_tiles_from_sim(ds)
        extra = [t for t in dtl if "DATASHEET" in t.limit]
        if extra:
            st.markdown("**Datasheet min/max checks** (representative CM1500HC-66XB, not Wabtec acceptance):")
            st.dataframe(pd.DataFrame([{"Check": t.label, "Value": round(t.value, 6), "Unit": t.unit, "Limit": t.limit,
                                        "Result": STATE_TXT[t.state][0], "Note": t.note} for t in extra]), hide_index=True, width="stretch")
    with t1:
        st.caption("Animated replay of the SIMULATED record at full solver resolution. Use the bench's own dataset selector to switch runs.")
        render_virtual_lab([ds.id], height=1250)
    with t2:
        pk = TT.sim_packet(ds)
        rows = []
        for k in ("I_GES", "V_f", "t_trip", "R_NTC"):
            e = pk[k]
            rows.append({"Field": k, "Value": None if e["value"] is None else round(e["value"], 6), "Unit": e["unit"],
                         "Provenance": "SIMULATED" if e["value"] is not None else "—",
                         "Definition / reason": e["reason"] + (f" (Id ≈ {e['at_A']:.4g} A)" if e.get("at_A") else "")})
        st.markdown("Simulation results mapped onto the teammate tester fields. `null` means the quantity is not modelled.")
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.json({k: (None if pk[k]["value"] is None else pk[k]["value"]) for k in ("I_GES", "V_f", "t_trip", "R_NTC")})
    with t3:
        import json
        val = json.loads(ds.validation.read_text(encoding="utf-8-sig"))
        keys = ["status", "peak_Vce_V", "peak_Ic_A", "peak_Ig_A", "energy_balance_relative_error",
                "inductor_flux_relative_error", "freewheel_min_current_A", "freewheel_Ic_to_IL_ratio", "kcl_max_A"]
        st.dataframe(pd.DataFrame([{"Quantity": k, "Value (validation JSON)": str(val.get(k))} for k in keys if k in val]),
                     hide_index=True, width="stretch")
        st.caption(f"{val.get('scope', '')}. {val.get('energy_interpretation', '')} "
                   f"Source: {ds.validation.relative_to(D.ROOT)}.")
        if ds.params.get("schema") == "testcell.traction_device.v1":
            st.warning("Traction run: CM1500HC-66XB datasheet typical values (representative, NOT a confirmed Wabtec part). "
                       "Freewheel diode has NO reverse recovery (Qrr 880 µC not modelled) — turn-on overshoot and Eon "
                       "underestimated. transit_s (tail current) is ASSUMED; modelled Ic fall ≈ 22 µs vs datasheet tf ≤ 0.70 µs.")

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
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@600;700;800&family=Source+Sans+3:wght@400;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
/* white + red identity, same as the project page */
.stApp, .stApp p, .stApp li, .stApp label, .stApp input{font-family:'Source Sans 3','Segoe UI',Roboto,Arial,sans-serif}
.stApp h1, .stApp h2, .stApp h3{font-family:Barlow,'Arial Narrow',Arial,sans-serif;letter-spacing:-.005em}
.stAppDeployButton, [data-testid="stAppDeployButton"], [data-testid="stToolbarActions"]{display:none!important}
[data-testid="stHeader"]{background:#ffffff;border-top:5px solid #d0021b}
[data-testid="stSidebar"]{background:#ffffff;border-right:1px solid #e8e1e1;min-width:340px!important;max-width:340px!important}
[data-testid="stSidebar"] h2{font:700 13px Barlow,'Arial Narrow',sans-serif;letter-spacing:.14em;text-transform:uppercase;color:#d0021b}
.brand{display:flex;flex-direction:column;gap:6px;margin:0 0 14px;padding-bottom:12px;border-bottom:1px solid #e8e1e1}
.brand .eb{display:flex;align-items:center;gap:8px;font:600 12px Barlow,sans-serif;letter-spacing:.14em;text-transform:uppercase;color:#d0021b}
.brand .eb i{width:11px;height:11px;background:#d0021b;display:inline-block}
.brand .tt{font:800 44px/1 Barlow,'Arial Narrow',sans-serif;color:#1a1414}
.brand .tt em{font-style:normal;color:#d0021b}
.block-container{padding-top:2.6rem}
.vbox{border-radius:2px;padding:18px 24px;margin:4px 0 10px;display:flex;align-items:center;gap:28px;flex-wrap:wrap;border:1px solid #e8e1e1}
.vbox.pass{background:#ffffff;border-left:8px solid #1f7a45}
.vbox.nopass{background:#d0021b;border-color:#d0021b}
.vbox.unverified{background:#ffffff;border-left:8px solid #b06a00}
.vbig{font:800 50px/1 Barlow,'Arial Narrow',sans-serif;letter-spacing:.04em;color:#1a1414}
.vbox.pass .vbig{color:#1f7a45}.vbox.unverified .vbig{color:#b06a00}
.vbox.nopass .vbig,.vbox.nopass .vsub,.vbox.nopass .vsmall,.vbox.nopass b{color:#ffffff}
.vsub{font:600 16px 'Segoe UI',system-ui,sans-serif;color:#1a1414}
.vsmall{font:13px 'Segoe UI',system-ui,sans-serif;color:#6b5f5f;margin-top:4px}
.chip{display:inline-block;font:500 11px 'IBM Plex Mono',Consolas,monospace;padding:5px 8px;border-radius:0;margin:2px 4px 2px 0;border:1px solid #e8e1e1;background:#ffffff;color:#1a1414}
.c-demo{border-left:3px solid #d0021b}
.c-sim{border-left:3px solid #1f7a45}
.c-inc{border-left:3px solid #b06a00}
.c-src{border-left:3px solid #8a7e7e}
.tiles{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:10px;margin:6px 0 4px}
.tile{border-radius:2px;padding:10px 12px;border:1px solid #e8e1e1;border-top:3px solid #d9cfcf;background:#ffffff;min-height:96px}
.tile .tl{font:600 12.5px Barlow,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:#6b5f5f;display:flex;justify-content:space-between}
.tile .tv{font:600 22px 'IBM Plex Mono',Consolas,monospace;margin:4px 0 2px;color:#1a1414}
.tile .tn{font:11.5px 'Segoe UI',sans-serif;color:#5b6672}
.tile.IN_LIMIT{border-top-color:#1f7a45}
.tile.OUT_OF_LIMIT{background:#fdecee;border-top-color:#d0021b}
.tile.NO_LIMIT{border-top-color:#b06a00}
.tile.NOT_TESTED{background:#faf7f7;border-style:dashed}
.tile.NOT_TESTED .tv{color:#9a9a9a;font-size:16px}
.st-dot{width:11px;height:11px;border-radius:50%;display:inline-block}
@media (max-width:900px){.tiles{grid-template-columns:repeat(2,1fr)}.vbig{font-size:34px}}
</style>
""", unsafe_allow_html=True)

STATE_TXT = {"IN_LIMIT": ("in limit", "#1f7a45"), "OUT_OF_LIMIT": ("OUT OF LIMIT", "#d0021b"),
             "NO_LIMIT": ("no approved limit", "#b06a00"), "NOT_TESTED": ("not tested / not modelled", "#b0b0b0")}
PRESETS = ["Healthy Module (Pass)", "Bond Wire Lift-Off (Fail)", "Gate Oxide Breakdown (Fail)", "Solder Layer Delamination (Fail)"]


# ---------------------------------------------------------------- sidebar
BRAND = ('<div class="brand"><span class="eb"><i></i>NU × Wabtec Hackathon 2026 · pre-installation test cell</span>'
         '<span class="tt">IGBT Bench <em>Tester</em></span></div>')
page = st.sidebar.radio("View", ["Tester", "Test history"], horizontal=True, label_visibility="collapsed")

if page == "Test history":
    from virtual_lab import history as H
    st.markdown(BRAND.replace("IGBT Bench <em>Tester</em>", "Test <em>history</em>"), unsafe_allow_html=True)
    hist = H.load_all()
    if not hist:
        st.info("No saved tests yet. In **Tester**, confirm the safety interlocks and press **Save to history**.")
        st.stop()
    n_pass = sum(r["verdict"] == "PASS" for r in hist)
    c1, c2, c3 = st.columns(3)
    c1.metric("Saved tests", len(hist)); c2.metric("PASS", n_pass); c3.metric("NO-PASS", len(hist) - n_pass)
    f1, f2 = st.columns([1, 2])
    vf = f1.selectbox("Verdict", ["All", "PASS", "NO-PASS"])
    q = f2.text_input("Search serial or module", "")
    rows = [r for r in hist if (vf == "All" or r["verdict"] == vf)
            and (q.strip().lower() in (r["serial"] + " " + r["module"]).lower())]
    st.dataframe(pd.DataFrame([{"Saved": r["saved"], "Serial": r["serial"], "Module": r["module"], "Verdict": r["verdict"],
                                "Detail": r["detail"]} for r in rows]), hide_index=True, width="stretch")
    if rows:
        pick = st.selectbox("Open test", range(len(rows)),
                            format_func=lambda i: f'{rows[i]["saved"]} · {rows[i]["serial"]} · {rows[i]["verdict"]} · {rows[i]["module"][:70]}')
        r = rows[pick]
        st.markdown(f"**{r['serial']}** · {r['module']} · **{r['verdict']}** — {r['detail']}  \n"
                    f"Saved {r['saved']} · run `{r['run']}` · {r.get('data_source', '')} · hardware decision {r.get('hardware_decision', '')}")
        st.dataframe(pd.DataFrame([{"Check": c["check"], "Value": c["value"], "Unit": c["unit"], "Result": c["state"],
                                    "Limit": c["limit"]} for c in r.get("checks", [])]), hide_index=True, width="stretch")
        saf = r.get("safety_confirmed")
        if saf:
            st.caption("Safety interlocks at save time: " + " · ".join(f"{k}: {'✔' if v else '✘'}" for k, v in saf.items()))
        rb = H.report_bytes(r)
        if rb:
            st.download_button("⬇ Download stored report (HTML → PDF)", rb, file_name=r["report_file"], mime="text/html")
    st.stop()

st.sidebar.header("Bench control")
SRC_SIM, SRC_FW, SRC_PRE = "MATLAB simulation results", "MCU firmware (simulated STM32G474)", "Diagnostic presets (teammate)"
# MCU firmware and diagnostic-preset sources removed from the UI (team decision 2026-10-18); their code paths
# below are kept but unreachable. The tester shows MATLAB simulation results only.
source = SRC_SIM
st.sidebar.button("Physical DAQ — NOT IMPLEMENTED", disabled=True, width="stretch",
                  help="No acquisition hardware interface exists yet. Nothing in this app is MEASURED data.")
module_id = st.sidebar.text_input("Module serial / barcode", value="WB-2026-IGBT-088")
# Safety interlocks: operator confirmations (the simulation cannot measure them). A test can only be saved when all hold.
SAFETY = [("door", "Test-cell door closed, interlock OK"),
          ("estop", "E-stop released and tested"),
          ("discharged", "DC link discharged < 50 V (panel reading)"),
          ("ppe", "PPE worn: insulating gloves, face shield"),
          ("fixture", "Module locked in fixture, terminals torqued")]
st.sidebar.markdown("**Safety interlocks** — operator confirmation")
safety = [(lab, st.sidebar.checkbox(lab, key="safety_" + k)) for k, lab in SAFETY]
safety_ok = all(ok for _, ok in safety)
st.sidebar.caption("All interlocks confirmed — test may be saved." if safety_ok else
                   "Saving is blocked until every interlock is confirmed. These are operator confirmations, "
                   "not measurements; the hard-wired interlocks act independently of this software.")

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
    # Short, numbered labels; the full description of the selected module is shown under the list.
    SHORT = {"traction_rl": "Healthy module",
             "fault:igbt_gate_leak": "F1 · IGBT · gate-oxide leakage",
             "fault:igbt_vth_shift": "F2 · IGBT · threshold drift",
             "fault:igbt_diode_degraded": "F3 · IGBT · diode degraded",
             "fault:driver_weak_supply": "F4 · Driver · supply sag (+12 V)",
             "fault:driver_desat_dead": "F5 · Driver · DESAT protection dead",
             "fault:driver_slow_off": "F6 · Driver · slow turn-off"}
    full = {d.id: f"{d.label}  [{d.status}]" for d in dyn}
    ids = sorted((d.id for d in dyn), key=lambda i: (list(SHORT).index(i) if i in SHORT else len(SHORT), i))
    ds_id = st.sidebar.radio("Module under test", ids, format_func=lambda i: SHORT.get(i, full[i]),
                             index=ids.index("traction_rl") if "traction_rl" in ids else 0)
    st.sidebar.caption(full[ds_id])



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
    src_chips = ""
    subject = f"Module {module_id} · simulated device: {ds.label}"
    stale = False

# ---------------------------------------------------------------- TOP: verdict + tiles
st.markdown(BRAND, unsafe_allow_html=True)
if stale:
    st.warning("Sidebar inputs changed since the last run. The verdict below is still for the previous run — press RUN again.")
cls = "pass" if v["verdict"] == "PASS" else ("nopass" if v["reason"] == "FAILED" else "unverified")
st.markdown(f"""
<div class="vbox {cls}">
  <div class="vbig">{v['verdict']}</div>
  <div>
    <div class="vsub">{v['detail']}</div>
    <div class="vsmall">{subject} · simulation only, not a hardware decision</div>
  </div>
</div>
{src_chips}
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
st.caption("Green = inside limit · Red = outside limit · Amber = value available but no approved limit · "
           "Grey dashed = not tested / not modelled. Hover a tile for its definition and provenance.")

# ---------------------------------------------------------------- report download + test history
if source == SRC_SIM:
    from datetime import datetime as _dt
    from virtual_lab import history as H
    from virtual_lab import report as RP
    _now = _dt.now()
    _excl = globals().get("excluded", [])
    _html = RP.to_html(module_id, ds, v, tiles, _excl, _now, safety)
    _stem = f"IGBT_report_{module_id}_{_now.strftime('%Y%m%d_%H%M%S')}"
    b1, b2, b3, b4 = st.columns(4)
    b1.download_button("⬇ Report (HTML → PDF)", _html, file_name=_stem + ".html", mime="text/html", width="stretch",
                       help="Open in a browser and press Ctrl+P → Save as PDF.")
    b2.download_button("⬇ Results (Excel)", RP.to_xlsx(module_id, ds, v, tiles, _excl, _now), file_name=_stem + ".xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
    b3.download_button("⬇ Results (CSV)", RP.to_csv(module_id, ds, v, tiles, _excl, _now), file_name=_stem + ".csv",
                       mime="text/csv", width="stretch")
    if b4.button("💾 Save to history", type="primary", width="stretch", disabled=not safety_ok,
                 help=None if safety_ok else "Confirm all safety interlocks in the sidebar first."):
        H.save({"serial": module_id, "module": ds.label, "module_id": ds.id, "run": ds.folder.name,
                "verdict": v["verdict"], "reason": v["reason"], "detail": v["detail"],
                "hardware_decision": v["hardware_decision"], "data_source": "SIMULATED",
                "safety_confirmed": {lab: ok for lab, ok in safety},
                "checks": [{"check": t.label, "value": t.value, "unit": t.unit, "state": t.state, "limit": t.limit}
                           for t in tiles]}, _html, _now)
        st.toast(f"Saved to test history: {module_id} · {v['verdict']}")

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
        render_virtual_lab([ds.id], height=2150)
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
        render_virtual_lab([ds.id], height=2150)
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

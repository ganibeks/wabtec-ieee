import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import time
from igbt_simulation_engine import IGBTSimulationEngine, CABTEResult

# --- Page Setup & Styling ---
st.set_page_config(
    page_title="Wabtec CABTE Diagnostic Platform",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for polished industrial dashboard appearance
st.markdown("""
<style>
    .main-header { font-size:2.2rem; font-weight:700; color:#0e1117; margin-bottom:0rem; }
    .sub-header { font-size:1.1rem; color:#555; margin-bottom:1.5rem; }
    .metric-card { background-color:#f8f9fa; border-radius:8px; padding:12px; border:1px solid #e9ecef; }
    .badge-pass { background-color:#d4edda; color:#155724; padding:4px 8px; border-radius:4px; font-weight:bold; }
    .badge-fail { background-color:#f8d7da; color:#721c24; padding:4px 8px; border-radius:4px; font-weight:bold; }
</style>
""", unsafe_allow_html=True)

# --- Header Section ---
st.markdown('<p class="main-header">🚆 Wabtec CABTE: Automated IGBT Bench Test Cell</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Consolidated Pre-Installation Diagnostic Platform for 25 kg Heavy-Haul Locomotive Phase Modules</p>', unsafe_allow_html=True)

# --- Sidebar Control Panel ---
st.sidebar.header("⚙️ Bench Control & Module Config")

module_id = st.sidebar.text_input("IGBT Serial Number / Barcode:", value="WB-2026-IGBT-088")

condition_preset = st.sidebar.selectbox(
    "Select Test Condition Preset:",
    options=[
        "Healthy Module (Pass)",
        "Bond Wire Lift-Off (Fail)",
        "Gate Oxide Breakdown (Fail)",
        "Solder Layer Delamination (Fail)"
    ],
    help="Simulates specific physical degradation modes observed in railway traction converters."
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📋 Test Specifications")
st.sidebar.markdown("- **Gate Drive Voltage:** $+15\\text{ V}$ ON / $-15\\text{ V}$ OFF")
st.sidebar.markdown("- **Max Desat Protection Delay:** $10.0\\ \\mu\\text{s}$")
st.sidebar.markdown("- **Auxiliary Driver Supply:** $100\\text{ VAC}$")
st.sidebar.markdown("- **Max Gate Leakage ($I_{GES}$):** $2.0\\text{ mA}$")

run_test_btn = st.sidebar.button("▶ RUN DIAGNOSTIC SEQUENCE", type="primary", use_container_width=True)

# --- Main Dashboard Logic ---

# Initialize session state for test results
if "result" not in st.session_state:
    st.session_state["result"] = None

if run_test_btn:
    st.markdown("### 🔄 Executing Consolidated Diagnostic Sequence")
    progress_bar = st.progress(0)
    status_text = st.empty()

    # Simulate the 4 CABTE test phases with visual progress
    phases = [
        "Phase 1/4: DC Static Curve Sweep (Breakdown Voltage & Gate Leakage Current)...",
        "Phase 2/4: Pulsed Double-Pulse Dynamic Switching Test (E_on, E_off, Diode V_f)...",
        "Phase 3/4: Gate Driver Exerciser & 10 µs Desaturation Protection Test...",
        "Phase 4/4: Transient Thermal Impedance & Acoustic Resonance Analysis..."
    ]

    for idx, phase_name in enumerate(phases):
        status_text.info(f"**{phase_name}**")
        time.sleep(0.5)
        progress_bar.progress(int((idx + 1) * 25))

    status_text.success("✅ **Diagnostic Sequence Completed Successfully!**")

    # Store result using Member 1's engine
    st.session_state["result"] = IGBTSimulationEngine.run_full_diagnostic(
        module_id=module_id,
        condition_preset=condition_preset
    )

res: CABTEResult = st.session_state["result"]

if res is not None:
    st.markdown("---")

    # --- Top Banner: Overall Verdict ---
    if res.overall_passed:
        st.success(f"### 🎉 OVERALL VERDICT: {res.summary_verdict}")
    else:
        st.error(f"### 🛑 OVERALL VERDICT: {res.summary_verdict}")

    # --- Section 1: Parameter Metrics Table & Status Cards ---
    col_left, col_right = st.columns([1.2, 1])

    with col_left:
        st.subheader("📊 Diagnostic Parameter Summary")

        # Build DataFrame for clean table display
        table_data = []
        for key, p in res.parameters.items():
            status_str = "✅ PASS" if p.passed else "❌ FAIL"
            table_data.append({
                "Parameter": p.name,
                "Symbol": p.symbol,
                "Measured Value": f"{p.measured_value} {p.unit}",
                "Target Range": f"{p.pass_min} - {p.pass_max} {p.unit}",
                "Status": status_str,
                "Diagnostic Purpose": p.description
            })

        df_params = pd.DataFrame(table_data)
        st.dataframe(df_params, use_container_width=True, hide_index=True)

    with col_right:
        st.subheader("📌 Key Fault Indicators")

        p_desat = res.parameters["t_trip"]
        p_leakage = res.parameters["I_GES"]
        p_diode = res.parameters["V_f"]
        p_thermal = res.parameters["Z_th"]

        m_col1, m_col2 = st.columns(2)
        with m_col1:
            st.metric(
                label="Desat Trip Speed",
                value=f"{p_desat.measured_value} µs",
                delta="Within 10 µs limit" if p_desat.passed else "EXCEEDS 10 µs LIMIT",
                delta_color="normal" if p_desat.passed else "inverse"
            )
            st.metric(
                label="Diode Drop (V_f)",
                value=f"{p_diode.measured_value} V",
                delta="Normal (0.2-0.8V)" if p_diode.passed else "Diode Fault",
                delta_color="normal" if p_diode.passed else "inverse"
            )
        with m_col2:
            st.metric(
                label="Gate Leakage Current",
                value=f"{p_leakage.measured_value} mA",
                delta="Normal (< 2 mA)" if p_leakage.passed else "Dielectric Puncture",
                delta_color="normal" if p_leakage.passed else "inverse"
            )
            st.metric(
                label="Thermal Impedance",
                value=f"{p_thermal.measured_value} K/W",
                delta="Normal Heat Path" if p_thermal.passed else "Solder Voiding",
                delta_color="normal" if p_thermal.passed else "inverse"
            )

    st.markdown("---")

    # --- Section 2: Waveform Visualizations ---
    st.subheader("📈 Diagnostic Waveform & Spectral Analysis")

    tab1, tab2, tab3, tab4 = st.tabs([
        "⚡ Desaturation Protection (t_trip)",
        "🔄 Diode I-V Curve (V_f)",
        "🌡️ Thermal Response (Z_th)",
        "🔊 Acoustic Resonance (f_res)"
    ])

    # Tab 1: Desaturation Waveform
    with tab1:
        t_desat, v_desat = res.waveforms["desat_protection"]
        fig1, ax1 = plt.subplots(figsize=(8, 3.5))
        ax1.plot(t_desat, v_desat, color="#1f77b4" if p_desat.passed else "#d62728", linewidth=2.5, label="Measured Gate Voltage V_ge")
        ax1.axvline(10.0, color="gray", linestyle="--", linewidth=1.5, label="10 µs Protection Threshold")
        ax1.axhline(15.0, color="green", linestyle=":", alpha=0.5, label="+15V Turn-ON")
        ax1.axhline(-15.0, color="red", linestyle=":", alpha=0.5, label="-15V Turn-OFF")
        ax1.set_xlabel("Time (µs)", fontsize=10)
        ax1.set_ylabel("Gate-Emitter Voltage V_ge (V)", fontsize=10)
        ax1.set_title("Gate Driver Desaturation Fault Trip Response", fontsize=11, fontweight="bold")
        ax1.set_ylim(-20, 20)
        ax1.grid(True, linestyle="--", alpha=0.6)
        ax1.legend(loc="upper right", fontsize=9)
        st.pyplot(fig1)
        st.caption("Verifies that the local gate driver shuts off gate voltage (+15V to -15V) within 10 µs during a short-circuit condition.")

    # Tab 2: Diode I-V Curve
    with tab2:
        v_d, i_d = res.waveforms["diode_iv_curve"]
        fig2, ax2 = plt.subplots(figsize=(8, 3.5))
        ax2.plot(v_d, i_d, color="#2ca02c" if p_diode.passed else "#d62728", linewidth=2.5, label="Freewheeling Diode Forward Sweep")
        ax2.axvspan(0.2, 0.8, color="green", alpha=0.15, label="Pass Window (0.2V - 0.8V)")
        ax2.axvline(p_diode.measured_value, color="black", linestyle="--", label=f"Measured V_f @ 10A ({p_diode.measured_value} V)")
        ax2.set_xlabel("Forward Voltage Drop V_f (V)", fontsize=10)
        ax2.set_ylabel("Forward Current I_f (A)", fontsize=10)
        ax2.set_title("Free-Wheeling Diode Forward Voltage Characteristic", fontsize=11, fontweight="bold")
        ax2.set_ylim(0, 45)
        ax2.grid(True, linestyle="--", alpha=0.6)
        ax2.legend(loc="upper left", fontsize=9)
        st.pyplot(fig2)
        st.caption("Checks for open circuit or short circuit damage in anti-parallel freewheeling diode dies.")

    # Tab 3: Thermal Impedance Curve
    with tab3:
        t_ms, z_th = res.waveforms["thermal_impedance"]
        fig3, ax3 = plt.subplots(figsize=(8, 3.5))
        ax3.semilogx(t_ms, z_th, color="#ff7f0e" if p_thermal.passed else "#d62728", linewidth=2.5, label="Transient Thermal Impedance Z_th(t)")
        ax3.axhline(0.050, color="red", linestyle="--", label="Max Allowable Thermal Resistance (0.050 K/W)")
        ax3.set_xlabel("Time Post-Pulse (ms, log scale)", fontsize=10)
        ax3.set_ylabel("Thermal Impedance Z_th (K/W)", fontsize=10)
        ax3.set_title("Transient Thermal Response (Solder Stack Delamination Check)", fontsize=11, fontweight="bold")
        ax3.grid(True, which="both", linestyle="--", alpha=0.6)
        ax3.legend(loc="upper left", fontsize=9)
        st.pyplot(fig3)
        st.caption("Measures heat transfer efficiency through the ceramic substrate and baseplate to detect solder voids.")

    # Tab 4: Acoustic Resonance Spectrum
    with tab4:
        freqs, amp = res.waveforms["acoustic_spectrum"]
        p_res = res.parameters["f_res"]
        fig4, ax4 = plt.subplots(figsize=(8, 3.5))
        ax4.plot(freqs, amp, color="#9467bd" if p_res.passed else "#d62728", linewidth=2, label="Acoustic Spectral Response")
        ax4.axvline(1345.0, color="green", linestyle="--", label="Nominal Structural Resonance (1345 Hz)")
        ax4.axvspan(1320.0, 1370.0, color="green", alpha=0.1, label="Pass Frequency Band")
        ax4.set_xlabel("Frequency (Hz)", fontsize=10)
        ax4.set_ylabel("Spectral Amplitude (dB)", fontsize=10)
        ax4.set_title("Piezoelectric Acoustic Emission Structural Resonance", fontsize=11, fontweight="bold")
        ax4.grid(True, linestyle="--", alpha=0.6)
        ax4.legend(loc="upper right", fontsize=9)
        st.pyplot(fig4)
        st.caption("Detects structural bond wire foot cracking and ceramic substrate fractures via acoustic frequency shifts.")

    st.markdown("---")

    # --- Section 3: Certificate Export Generator ---
    st.subheader("📄 Generate Depot Inspection Certificate")

    cert_text = f"""================================================================================
WABTEC LOCOMOTIVE TRACTION CONVERTER SERVICE DEPOT
CABTE AUTOMATED INSPECTION CERTIFICATE
================================================================================
Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}
Module Serial Number: {res.module_id}
Module Mass Rating: 25 kg (55 lb)
Tested Platform: Consolidated Automated Bench Test Equipment (CABTE)
Condition Preset Tested: {res.condition_preset}

OVERALL VERDICT: {res.summary_verdict}
--------------------------------------------------------------------------------
MEASURED PARAMETER BREAKDOWN:
--------------------------------------------------------------------------------
1. Gate Leakage Current (I_GES):          {res.parameters['I_GES'].measured_value} mA  [Target: < 2.0 mA] -> {'PASS' if res.parameters['I_GES'].passed else 'FAIL'}
2. Gate Threshold Voltage (V_GE_th):      {res.parameters['V_GE_th'].measured_value} V   [Target: 5.0 - 7.5 V] -> {'PASS' if res.parameters['V_GE_th'].passed else 'FAIL'}
3. Diode Forward Voltage Drop (V_f):      {res.parameters['V_f'].measured_value} V   [Target: 0.2 - 0.8 V] -> {'PASS' if res.parameters['V_f'].passed else 'FAIL'}
4. Collector Saturation Voltage (V_CE_sat):{res.parameters['V_CE_sat'].measured_value} V   [Target: 1.7 - 2.3 V] -> {'PASS' if res.parameters['V_CE_sat'].passed else 'FAIL'}
5. Desaturation Protection Speed (t_trip):{res.parameters['t_trip'].measured_value} us  [Target: <= 10.0 us] -> {'PASS' if res.parameters['t_trip'].passed else 'FAIL'}
6. NTC Thermistor Resistance (R_NTC):     {res.parameters['R_NTC'].measured_value} Ohm [Target: 4500 - 5500 Ohm] -> {'PASS' if res.parameters['R_NTC'].passed else 'FAIL'}
7. Transient Thermal Impedance (Z_th):    {res.parameters['Z_th'].measured_value} K/W [Target: <= 0.050 K/W] -> {'PASS' if res.parameters['Z_th'].passed else 'FAIL'}
8. Acoustic Structural Resonance (f_res): {res.parameters['f_res'].measured_value} Hz  [Target: 1320 - 1370 Hz] -> {'PASS' if res.parameters['f_res'].passed else 'FAIL'}

--------------------------------------------------------------------------------
OPERATOR ACTION / RECOMMENDATION:
{'[APPROVED] Module cleared for immediate installation on locomotive chassis.' if res.overall_passed else '[REJECTED] Send module for component-level rebuild or silicon die scrap.'}
================================================================================
"""

    st.text_area("Inspection Certificate Preview:", value=cert_text, height=220)

    st.download_button(
        label="📥 DOWNLOAD INSPECTION CERTIFICATE (.TXT)",
        data=cert_text,
        file_name=f"CABTE_Inspection_{res.module_id}.txt",
        mime="text/plain",
        use_container_width=True
    )
else:
    st.info("👈 Select a module condition preset in the sidebar and click **'▶ RUN DIAGNOSTIC SEQUENCE'** to initiate testing.")

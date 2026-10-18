import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, Tuple, Any

@dataclass
class DiagnosticParameter:
    name: str
    symbol: str
    measured_value: float
    unit: str
    pass_min: float
    pass_max: float
    passed: bool
    description: str

@dataclass
class CABTEResult:
    module_id: str
    condition_preset: str
    overall_passed: bool
    summary_verdict: str
    parameters: Dict[str, DiagnosticParameter]
    waveforms: Dict[str, Tuple[np.ndarray, np.ndarray]]

class IGBTSimulationEngine:
    """
    Consolidated Automated Bench Test Equipment (CABTE) Simulation Engine
    Models static DC characteristics, dynamic pulse switching, desaturation fault
    protection, and thermal/acoustic packaging health for 25 kg locomotive IGBT modules.
    """

    @staticmethod
    def run_full_diagnostic(module_id: str, condition_preset: str = "Healthy Module (Pass)") -> CABTEResult:
        """
        Executes a complete 4-phase CABTE diagnostic sequence.
        Presets:
          - "Healthy Module (Pass)"
          - "Bond Wire Lift-Off (Fail)"
          - "Gate Oxide Breakdown (Fail)"
          - "Solder Layer Delamination (Fail)"
        """
        # Seed random generator deterministically based on module_id string
        seed_val = int(abs(hash(module_id))) % (2**31 - 1)
        np.random.seed(seed_val)

        # Default Baseline Values (Healthy State)
        gate_leakage_mA = float(np.random.normal(0.04, 0.005))   # Threshold < 2.0 mA
        v_ge_th_V = float(np.random.normal(6.1, 0.1))            # Healthy 5.0 - 7.5 V
        diode_vf_V = float(np.random.normal(0.54, 0.02))         # Healthy 0.2 - 0.8 V
        v_ce_sat_V = float(np.random.normal(1.95, 0.03))         # Healthy 1.7 - 2.3 V
        desat_trip_us = float(np.random.normal(6.2, 0.2))        # Threshold <= 10.0 us
        ntc_ohm = float(np.random.normal(4980, 45.0))            # Healthy 4500 - 5500 Ohm
        z_th_k_w = float(np.random.normal(0.035, 0.002))         # Healthy <= 0.050 K/W
        acoustic_peak_hz = float(np.random.normal(1345, 3.0))    # Resonant frequency ~1345 Hz

        # Inject Specific Fault Mechanisms based on Preset
        if condition_preset == "Bond Wire Lift-Off (Fail)":
            # Bond wire fatigue increases path resistance & causes open diode / V_CE shift
            diode_vf_V = float(np.random.normal(1.45, 0.05))     # FAIL: > 0.8 V
            v_ce_sat_V = float(np.random.normal(3.10, 0.10))     # FAIL: Elevated saturation voltage
            acoustic_peak_hz = float(np.random.normal(1210, 15.0)) # FAIL: Resonant shift away from 1345 Hz

        elif condition_preset == "Gate Oxide Breakdown (Fail)":
            # Gate dielectric puncture increases leakage & delays protection response
            gate_leakage_mA = float(np.random.normal(3.85, 0.25)) # FAIL: > 2.0 mA
            v_ge_th_V = float(np.random.normal(3.2, 0.15))       # FAIL: Dropped threshold
            desat_trip_us = float(np.random.normal(18.5, 0.8))   # FAIL: > 10.0 us protection limit

        elif condition_preset == "Solder Layer Delamination (Fail)":
            # Solder voiding increases thermal impedance & distorts thermistor readings
            ntc_ohm = float(np.random.normal(9200, 150.0))       # FAIL: Thermal sensor out of spec
            z_th_k_w = float(np.random.normal(0.092, 0.005))     # FAIL: Elevated thermal resistance (> 0.05 K/W)

        # Evaluate Pass/Fail Criteria for each Parameter
        p1 = DiagnosticParameter("Gate Leakage Current", "I_GES", round(gate_leakage_mA, 3), "mA", 0.0, 2.0, gate_leakage_mA < 2.0, "Checks gate dielectric integrity")
        p2 = DiagnosticParameter("Gate Threshold Voltage", "V_GE(th)", round(v_ge_th_V, 2), "V", 5.0, 7.5, 5.0 <= v_ge_th_V <= 7.5, "Verifies turn-on threshold voltage")
        p3 = DiagnosticParameter("Diode Forward Drop", "V_f", round(diode_vf_V, 3), "V", 0.2, 0.8, 0.2 <= diode_vf_V <= 0.8, "Measures anti-parallel diode drop")
        p4 = DiagnosticParameter("Collector Saturation Voltage", "V_CE(sat)", round(v_ce_sat_V, 2), "V", 1.7, 2.3, 1.7 <= v_ce_sat_V <= 2.3, "Detects bond wire lift-off resistance")
        p5 = DiagnosticParameter("Desaturation Trip Time", "t_trip", round(desat_trip_us, 2), "us", 0.0, 10.0, desat_trip_us <= 10.0, "Gate driver short-circuit protection speed")
        p6 = DiagnosticParameter("NTC Thermistor Resistance", "R_NTC", round(ntc_ohm, 1), "Ohm", 4500.0, 5500.0, 4500.0 <= ntc_ohm <= 5500.0, "Internal thermal node sensor check")
        p7 = DiagnosticParameter("Thermal Impedance", "Z_th", round(z_th_k_w, 4), "K/W", 0.0, 0.050, z_th_k_w <= 0.050, "Solder stack heat dissipation health")
        p8 = DiagnosticParameter("Acoustic Resonance", "f_res", round(acoustic_peak_hz, 1), "Hz", 1320.0, 1370.0, 1320.0 <= acoustic_peak_hz <= 1370.0, "Structural bond wire foot integrity")

        params = {
            "I_GES": p1, "V_GE_th": p2, "V_f": p3, "V_CE_sat": p4,
            "t_trip": p5, "R_NTC": p6, "Z_th": p7, "f_res": p8
        }

        overall_passed = all(p.passed for p in params.values())

        if overall_passed:
            summary_verdict = "PASS - MODULE SAFE FOR LOCOMOTIVE INSTALLATION"
        else:
            failed_names = [p.name for p in params.values() if not p.passed]
            summary_verdict = f"REJECT - FAULT DETECTED: {', '.join(failed_names)}"

        # Generate Time-Series Waveforms for Plots
        waveforms = {
            "desat_protection": IGBTSimulationEngine._gen_desat_waveform(desat_trip_us),
            "diode_iv_curve": IGBTSimulationEngine._gen_diode_iv_curve(diode_vf_V),
            "thermal_impedance": IGBTSimulationEngine._gen_thermal_response(z_th_k_w),
            "acoustic_spectrum": IGBTSimulationEngine._gen_acoustic_spectrum(acoustic_peak_hz)
        }

        return CABTEResult(
            module_id=module_id,
            condition_preset=condition_preset,
            overall_passed=overall_passed,
            summary_verdict=summary_verdict,
            parameters=params,
            waveforms=waveforms
        )

    # --- Private Waveform Generators ---

    @staticmethod
    def _gen_desat_waveform(trip_time_us: float) -> Tuple[np.ndarray, np.ndarray]:
        """Generates Gate Voltage (V_ge) vs Time during simulated desaturation fault."""
        t = np.linspace(0, 25, 300) # Time in microseconds
        # Gate starts ON at +15V, drops to -15V upon trip detection
        v_ge = np.where(t < trip_time_us, 15.0, -15.0)
        # Add realistic RC transient smoothing
        tau = 0.4
        for i in range(1, len(v_ge)):
            v_ge[i] = v_ge[i-1] + (v_ge[i] - v_ge[i-1]) * (1 - np.exp(-(t[i]-t[i-1])/tau))
        return t, v_ge

    @staticmethod
    def _gen_diode_iv_curve(v_f_target: float) -> Tuple[np.ndarray, np.ndarray]:
        """Generates Diode Forward Current (I_f) vs Voltage (V_f) curve using Shockley model."""
        v_d = np.linspace(0.0, 1.2, 200)
        # Scale diode current so that at V_f = v_f_target, I_d = 10A (sensing current)
        n_vt = 0.045
        i_s = 10.0 / (np.exp(v_f_target / n_vt) - 1.0)
        i_d = i_s * (np.exp(v_d / n_vt) - 1.0)
        i_d = np.clip(i_d, 0, 50) # Cap display current at 50A
        return v_d, i_d

    @staticmethod
    def _gen_thermal_response(z_th_max: float) -> Tuple[np.ndarray, np.ndarray]:
        """Generates Transient Thermal Impedance Z_th(t) curve following a heating pulse."""
        t_ms = np.logspace(0, 3, 200) # 1ms to 1000ms
        # Multi-exponential thermal foster network model
        z_th = z_th_max * (1 - 0.4 * np.exp(-t_ms / 10.0) - 0.6 * np.exp(-t_ms / 150.0))
        return t_ms, z_th

    @staticmethod
    def _gen_acoustic_spectrum(peak_hz: float) -> Tuple[np.ndarray, np.ndarray]:
        """Generates Acoustic Emission Spectral Response showing resonant frequency peaks near 1345 Hz."""
        freqs = np.linspace(1000, 1600, 300)
        # Gaussian resonance peak centered around peak_hz
        amplitude = 10.0 * np.exp(-0.5 * ((freqs - peak_hz) / 12.0)**2) + np.random.normal(0.5, 0.05, len(freqs))
        amplitude = np.clip(amplitude, 0, 15)
        return freqs, amplitude

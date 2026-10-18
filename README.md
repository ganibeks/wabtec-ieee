# IGBT Bench Tester — NU × Wabtec Hackathon 2026

Pre-installation test cell for traction IGBT modules: catch a bad IGBT on the bench, not on the locomotive.

The project simulates a representative 3.3 kV / 1500 A traction IGBT (Mitsubishi CM1500HC-66XB, **not a confirmed Wabtec part**)
and its gate driver in MATLAB R2026b / Simscape Electrical, and checks every module against the Wabtec brief (slides 5 and 8)
in a laptop tester that returns PASS / NO-PASS and a downloadable report.

## What is inside

| Folder / file | Content |
|---|---|
| `app_virtual_lab.py` | Tester (Streamlit): PASS / NO-PASS, slide 5/8 checks, safety interlocks, report download, test history |
| `virtual_lab/` | Tester logic, report and history, animated virtual test bench (`testbench_standalone.html`) |
| `+testcell/` | MATLAB package: device parameters, double-pulse rig, static checks, diode test, DESAT short-circuit test, injected faults |
| `results/` | Simulation results (CSV waveforms, validation JSON, plots, Simulink models) |
| `deliverables/` | Technical report (PDF/HTML), project page, block diagrams |
| `firmware/` | C++ tester core for an STM32G474 (portable core + simulated board) |
| `tests/` | Regression tests for the verdict logic and the dashboard |

## Run the tester

```
pip install -r requirements.txt
streamlit run app_virtual_lab.py
```

No installation needed for a quick look: open `virtual_lab/testbench_standalone.html` in a browser
(animated bench with the healthy module and six injected faults).

## Re-run the simulations (MATLAB R2026b + Simscape Electrical)

```matlab
p = testcell.parameters_traction;
testcell.run_dynamic(p, {'dynamic_rl'});   % double pulse, 1800 V
testcell.run_static_checks(p);             % VGE(th), ICES, VCE(sat)
testcell.run_diode_test(p, 'traction');    % multimeter-style diode test
testcell.run_desat_test(p, 'traction');    % DESAT short circuit at 1800 V
testcell.run_dynamic(testcell.parameters_traction_fault('driver_slow_off'), {'dynamic_rl'});   % one of 6 faults
```

Each run writes a new folder in `results/`.

## Results (simulation)

- Healthy module: **PASS 8/8** (gate ±15 V, threshold 6.35 V, di/dt 1852 A/µs, diode 0.5 V / open, driver 0.22 W, DESAT detection 7.6 µs, gate off 1.94 µs after detection)
- **6 of 6 injected faults caught**, each by its own check: gate-oxide leakage, threshold drift, diode degradation, driver supply sag, dead DESAT, slow driver turn-off
- Model checks: energy balance error 6·10⁻⁷, half-step rerun within 3 %

## Limitations

Simulation of a representative device only; the hardware decision stays **INCONCLUSIVE** until real Wabtec modules are tested.
The model's turn-off current tail is not calibrated (≈ 22 µs vs datasheet ≤ 0.7 µs), so the DESAT current-interruption time is
reported but not used in the verdict. Fault severities are assumed. Busbar insulation needs a hardware hipot test.
The Wabtec brief is not included in this repository.

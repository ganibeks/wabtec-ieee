# Project status — 2026-10-17

## Preserved validated baseline
- results/20261017_163035_757/igbt_baseline.slx; independent rerun in results/verify_20261017_163312_457.
- 12 V / 100 ohm ideal switching baseline PASS; original files archived before the earlier resume.
- Baseline SLX SHA256: 8DCE5F7DB3C347E7C97366482343E57CF9639390B9EEFCF47E87F6264921CB9E.

## Detailed electrical laboratory
- Reusable +testcell factory creates DUT, GateDrive, Supply, LoadBank and Measurements subsystems using the installed full nonlinear N-Channel IGBT, capacitances and stored charge.
- Four fixture compilation/initialization tests PASS (targeted_detailed_03.log).
- 62 completed static points and partial report: results/static25_20261017_165838_504. Includes 54 output/leakage points at 25 C, seven current-clamp points at 25 C, one 20 A current-clamp check at 125 C. Vce at 20 A: 2.000065 V (25 C), 2.400083 V (125 C). Assumed calibration recovery, not measured hardware validation.
- Resistive switching PASS: results/dynamic_20261017_165503_678/dynamic_r_validation.json. No solver warnings; terminal energy balance relative error 1.09e-8; half-step event-energy discrepancy below 0.43 percent. This folder also retains the superseded 50 us-gap RL diagnostic, which failed its commutation check.
- RL double-pulse PASS: results/dynamic_20261017_165933_696, dynamic_rl_04.log. 48 V, 2 ohm, 1 mH, 100 nH assumed commutation inductance. KCL passes; inductor integral error 8.58e-8; energy balance error 1.51e-8; event-energy step convergence below 0.12 percent. Peak Vce 51.143 V, peak Ic 10.395 A.
- Model charge storage gives approximately 48.35 us normal turn-off clearance to 1 percent current. This is distinct from driver delay and does not establish a 10 us protection response. The double-pulse freewheel interval was extended to 100 us based on the observed tail, without shortening the assumed device transit time.
- Raw MAT, CSV, parameter JSON, source snapshots, SLX models, plots and HTML reports retained in unique output folders. Numerical tolerances are not module acceptance limits.

## Current task
User scope is now ELECTRICAL ONLY. Analyze existing static and R/RL results and define the electrical testing and diagnostic solution in docs/ELECTRICAL_SOLUTION.md. No non-electrical work is active. Existing other-domain artifacts remain preserved as historical work; the coupled run remains NOT_VALIDATED per its validation_review.json.

## Blocked / known limitations
- Intermediate-temperature static voltage fixture stalls in the nonlinear BJT model. Three approaches attempted: stepped sweep, finite-bandwidth sweep, independent DC operating points. Batch stopped during the third approach after repeated solver warnings. Full 25/75/125 C matrix is NOT validated. Do not retry automatically without a new agreed investigation.
- Thermal interface resolved using nesl_utility/Simscape Component with simscape.setBlockComponent. The library variant block itself cannot be changed by setting ComponentPath. Thermal network topology must be explicitly external when attaching the separate RC network.
- Freewheel diode has piecewise-linear conduction plus explicit capacitance; reverse-recovery charge is not modeled.
- All device I-V calibration, capacitance, transit time, fixture and thermal RC parameters are illustrative. No device identity, manufacturer ratings, SOA, geometry, measured fit or hardware acceptance limits supplied.
- Hardware decision remains INCONCLUSIVE. No simulated device is certified operational.
- Fault injection, desaturation/protection, dead-time for a future half bridge, noise/tolerances/Monte Carlo, electrothermal degradation and automated hardware health classification remain unfinished.
- Python WindowsApps alias failed previously; ANSYS has not been used. Geometry/material/contact/cooling data are needed before any module-specific ANSYS thermal claims.

## Requirements provenance
references/NU IEEE 2026 IGBT test cell_AK_Final.pptx (slides 5/8: +15/-15 V, approximately 10 us protection; slide 8: roughly +4 to +7 V turn-on region; slide 11: parameters, justified duration, instructions, report and cost). The 3.5-minute figure remains user-supplied, absent from extracted slide text. Slide 5 busbar insulation leakage must not become a transistor leakage limit.

## Next steps — electrical scope
1. Review docs/ELECTRICAL_SOLUTION.md and the executed electrical-assessment metrics.
2. Validate isolated open-path and C-E short/bypass electrical fault scenarios against the preserved healthy R/RL fixtures.
3. Implement gate-drive fault checks and desaturation logic with separate detection, trip-command and current-clearance timing.
4. Define device-specific limits and measurement uncertainty before any hardware PASS/FAIL verdict. Hardware remains INCONCLUSIVE meanwhile.

Policy: one defined task at a time; targeted checks before full experiments; at most three automatic debugging attempts per issue; preserve existing results; report limitations honestly.



Electrical-only assessment COMPLETE: results/electrical_assessment_20261017_171813_439 (electrical_assessment.json, gate_comparison.csv and conduction_characteristic.csv). Script testcell.analyze_electrical executed successfully; it analyzes existing data and does not run new physical simulations. Findings: Vce approximately 2 V at 20 A, leakage 8.29 microampere at 48 V, strong gate-drive dependence, 48.35 us assumed-device current clearance. Solution and outstanding electrical tests documented in docs/ELECTRICAL_SOLUTION.md.


## Electrical code review — findings pending correction
- Confirmed by saved-data regression: truncating the RL record at 534.940 us still returns PASS with second turn-off current clearance NaN. Full record also returns PASS. No physical simulations rerun.
- parameters_traction.allowedKinds is not enforced by the runner/factory; default run_dynamic chooses the prohibited resistive fixture first.
- Per-case PASS JSON is written before the fine-step simulation/convergence check, so a later failure can leave a misleading PASS artifact.
- gateOn_V controls both driver output and device Vge_sat calibration, preventing independent under-drive experiments through that parameter.
- run_static accepts parameters but hardcodes calibration voltages, currents and operating conditions to the illustrative reference device.
Review made no implementation changes. Existing validated artifacts remain intact; MATLAB regression output is in review_electrical_*.log.

Part-identification research: original Elixir link is GE1255 / 17FM796A1-A3; separate Elixir exact match for 17FM774A1 found at /products/complete-igbt-module-ve, paired with 17FM775A1. Exact equivalence and internal semiconductor remain unconfirmed; IndiaMART content could not be retrieved. Findings: docs\PART_IDENTIFICATION_20261017_190659.md. No model parameters changed.


---

## Update 2026-10-17 evening — virtual lab, traction run, tester front end, C++ firmware

### Honest assessment
A useful simulation laboratory with a tester workflow, **not yet a reliable automatic IGBT health tester**. Fault classification and protection are not implemented, device-specific acceptance limits are missing, and validation bugs found in review must stay fixed before any automated PASS is trusted. Hardware decision: INCONCLUSIVE everywhere.

### Built
- `+testcell/parameters_traction.m` — Mitsubishi CM1500HC-66XB (3.3 kV / 1500 A), datasheet HVM-1147-B Dec 2025 typical values (`references/cm1500hc-66xb_e.pdf`, SHA256 19E5A4E0…6E44). Representative traction module, NOT a confirmed Wabtec part. Load/fixture values ASSUMED. Only `dynamic_rl` allowed.
- `virtual_lab/` (Python): `datasets.py` (discovery and exclusion rules), `features.py` (independent re-computation of `analyze_dynamic.m`, including the legacy analyzer used by the `dynamic_r` run), `payload.py`, `web/testbench.html` (offline animated test bench), `build_standalone.py`, `verify_testbench.py` (Playwright), `component.py`, `tester.py` (tiles and verdict), `mcu_link.py` (firmware link).
- `app_virtual_lab.py` (Streamlit tester). Top: PASS / NO-PASS (NO-PASS = failed OR not verified), 8 test tiles. Below: details. Sources: MATLAB simulation results / MCU firmware (simulated STM32G474) / Diagnostic presets (teammate, PRESET-DEMO, DEMO limits) / Physical DAQ (NOT IMPLEMENTED).
- Teammate files `app.py` and `igbt_simulation_engine.py` kept unchanged. The wrapper makes preset values repeatable across restarts (stable hash), marks their values PRESET-DEMO and replaces the installation certificate with a DEMO report.
- `firmware/` (C++17): portable tester core (`src/tester.cpp`: double-pulse sequencing, windowed Vce(sat) / diode Vf, OFF-1 timing, DESAT supervision, FAULT-input abort), virtual STM32G474 board (`src/sim`: 12-bit ADC model, clamp channel, quantisation; samples the MATLAB record), STM32G474 peripheral skeleton (`src/stm32`, NOT compiled). `build.py` uses pip `ziglang` (clang 21).

### Verified (actual outputs)
- Traction `dynamic_rl` run `results/dynamic_20261017_182654_290` (traction_rl_02.log): all `analyze_dynamic.m` assertions PASS, unmodified. Peak Vce 1822.39 V, peak Ic 2233.43 A, peak Ig 12.0 A, energy balance error 6.83e-8, half-step convergence ≤ 2.21e-5. Vce(on) 2.80 V at 1479 A (datasheet 2.60 V at 1500 A, 25 C; model calibrated at 125/150 C typical values and extrapolated). Peak Ic at 2nd turn-on 1670.6 A. Attempt 1 (`traction_rl_01.log`, folder `dynamic_20261017_182435_834`) failed compile: negative energy gap from mixing the 25 C ICES max with the 125 C typ; kept as evidence.
- Python vs MATLAB: all non-residual metrics agree with rel diff < 1e-6 on dynamic_rl, dynamic_r, baseline, traction_rl. Roundoff residuals (energy error ~1e-8 etc.) flagged, not counted as matches.
- `python virtual_lab/verify_testbench.py`: **37/37 PASS** (meters vs numpy.interp of CSV at 40, 200, 300.2, 310, 350, 400.06, 505, 1400 us; expected states; peak Vce 51.1427 V at 400.06196 us; 4 scope cursors same pixel; all datasets load without JS errors).
- Firmware: host build and freestanding Cortex-M4F compile of the core both clean with `-Wall -Wextra -Werror`. On the 48 V RL record the firmware gives Vce(sat) 1.143 V (full res 1.143 V), OFF-1 Ic fall 21.98 us (21.98 us). Peak Vce 48.9 V vs 51.14 V: a 2 MS/s ADC misses the spike. Wrong pulse plan refused. Injected FAULT input aborts the sequence.
- Streamlit app driven by Playwright with no exceptions: preset Healthy → PASS (DEMO limits); Gate Oxide Breakdown → NO-PASS (Failed: Gate leakage, Gate threshold, Desat trip); 48 V simulation → NO-PASS (not verified); firmware on traction → NO-PASS (Failed: Desat trip).

### Findings
- Firmware DESAT with ASSUMED 5 us blanking **false-trips on the healthy traction record** (Vce takes 9.18 us to fall below 9 V at ON-2). 10 us blanking completes but would consume the datasheet tpSC = 10 us. The cause is the ASSUMED transit time (datasheet td(on)+tr ≤ 1.9 us). Default not changed to hide it.
- Model Ic fall ~22 us vs datasheet tf ≤ 0.70 us (ASSUMED transit_s). Turn-off overshoot and Eon are not representative. Diode reverse recovery is not modelled (Qrr 880 uC, Erec 1.05 J).
- Measurement chain: Vce(sat) and diode Vf need dedicated clamp/differential channels; kV-range channels quantise to ~1.5 V.
- Teammate 2 mA I_GES limit comes from slide 5 busbar insulation leakage, not an IGBT rating.

### Bugs fixed
- `run_dynamic.m` wrote `*_validation.json` with status PASS before the half-step convergence assertion, so a convergence failure could leave a PASS file. It now writes only after all checks. `datasets.py` refuses PASS without a passed convergence record (status UNCONFIRMED). Existing PASS runs all contain the record.
- Bench V_AK meter lost precision (float32 cancellation of Vswitch − 48 V); now packed as a float64-derived channel.

### NOT done
Fault injection on the device model (open path, C-E short, gate faults), fault classification, desaturation protection validated against the device, diode reverse recovery, multi-temperature static matrix (75 C blocked), electrothermal (NOT_VALIDATED), real DAQ / real STM32 hardware, device-specific acceptance limits, the "Run new simulation" dashboard form (`+testcell/run_dashboard.m` not written).

### How to run (Anaconda Python; the `python` alias on PATH is broken)
```
C:\Users\ganib\anaconda3\python.exe virtual_lab/build_standalone.py      # -> virtual_lab/testbench_standalone.html (offline)
C:\Users\ganib\anaconda3\python.exe virtual_lab/verify_testbench.py      # Playwright check, expects 37/37 PASS
C:\Users\ganib\anaconda3\python.exe firmware/build.py                    # C++ host simulator + Cortex-M4F core compile
C:\Users\ganib\anaconda3\python.exe -m streamlit run app_virtual_lab.py  # tester front end
```

## Update 2026-10-17 ~19:50 — static checks at datasheet conditions; traction parameter fix

- New `+testcell/run_static_checks.m` (reuses the static_v / static_i fixtures unchanged): VGE(th) at VCE 10 V / IC 150 mA by bisection, ICES at 3300 V / VGE 0, VCEsat at 1500 A; 25 / 125 / 150 C.
- **It found a parameterization error in traction attempt 2:** the block measures all main-tab values (incl. Vth) at Tmeas, which was 125 C, so the 25 C datasheet Vth was applied at 125 C. Result: VGE(th) = 7.795 V at 25 C, outside the datasheet 5.80–6.80 V (`static_checks_traction_01.log`, `results/static_checks_20261017_193416_029`). That run and `dynamic_20261017_182654_290` are now SUPERSEDED (kept as evidence; `virtual_lab/datasets.py` SUPERSEDED list).
- Attempt 3 parameters: Tmeas 25 C (Vth 6.3 V, VCEsat 2.60 V typ), Tmeas2 125 C (3.20 V, ICES 4.0 mA typ). ICES at 25 C is DERIVED: back-extrapolated from the 125/150 C typ with EG = 0.981 eV → 0.115 uA.
- Static checks rerun (`static_checks_traction_02.log`, `results/static_checks_20261017_193726_230`), status **PARTIAL**:
  - VGE(th) 6.3504 V (datasheet 5.80–6.80 V) — inside.
  - VCEsat 2.6003 V (25 C), 3.1997 V (125 C) — calibration recovered. **150 C prediction 3.348 V** (datasheet typ 3.30, max 3.70) — inside, independent of the calibration.
  - ICES 150 C prediction 26.0 mA (typ 26 mA). ICES 125 C recovered within 0.07 %.
  - **ICES 25 C recovery FAILED:** the model gives 3.0055 uA at 3300 V in both attempts, independent of the Ices parameter (≈1.1 GΩ off-state floor), vs the 0.115 uA derived target. Check not loosened; no ICES value shown in the tester.
- Traction dynamic attempt 3 (`traction_rl_03.log`) failed the no-solver-warning rule: ode23t min-step difficulty at 50.57 us. Diagnostic (`diag_traction_01.log`): AbsTol 1e-10 did not help; ode15s has no warnings and matches ode23t to 0.2 % at 65 us. `build_rig.m` now accepts an optional `p.dynamicSolver` (default unchanged ode23t for the 48 V runs); `parameters_traction.m` sets ode15s.
- **Traction attempt 4 PASS** (`traction_rl_04.log`, `results/dynamic_20261017_194219_720`): all analyze_dynamic assertions unmodified. Peak Vce 1822.45 V, peak Ic 2240.26 A, peak Ig 12.0 A, energy balance 8.72e-7, half-step ≤ 4.63e-5. Vce(on) 2.645 V at 1479 A (datasheet typ 2.60 V at 1500 A). Peak Ic at 2nd turn-on 1676.0 A. ON-2 Vce < 9 V after 6.99 us.
- Firmware DESAT: 5 us blanking still false-trips at 405 us on this healthy record; 7.5 us completes (firmware Vce(sat) 2.601 V). Datasheet tpSC = 10 us.
- Tester (MATLAB source, traction): Gate threshold 6.35 V **IN LIMIT** and Vce(sat) at 150 C 3.348 V **IN LIMIT** against DATASHEET min/max of the representative device (not Wabtec acceptance). Verdict NO-PASS (amber, not verified: gate leakage, diode Vf limit, desat, NTC, thermal, acoustic). Hardware INCONCLUSIVE.
- App: NO-PASS is red when a test failed and amber when it is only not verified. `verify_testbench.py` 37/37 PASS after rebuild.

## Cleanup 2026-10-17 ~20:00
Root tidied. All batch logs (`*.log` referenced above, e.g. traction_rl_0x.log, static_checks_traction_0x.log, diag_traction_01.log) moved to `archive/cleanup_20261017/logs/`. Dev scripts (probe_blocks.m, inspect_detailed.m, run_development.m) moved to `archive/cleanup_20261017/dev_scripts/`, and their text outputs to `dev_outputs/`. Regenerable caches deleted (slprj, *.slxc, __pycache__, firmware/build, virtual_lab/verify_out). `results/` untouched.

## Recommendation review 2026-10-17 — electrical scope

Read-only code/result review; no simulations executed or implementation changed. Priorities:
1. Require complete dynamic records and finite turn-off clearance; enforce permitted dynamic fixtures; separate device calibration gate voltage from driver stimulus. Premature PASS-file writing is already fixed.
2. Keep required pending/NO_LIMIT tests in the overall verdict. Current split_simulated excludes them before verdict, allowing a subset to headline PASS; hardware_decision remains INCONCLUSIVE.
3. Bind static, diode and dynamic evidence by explicit experiment/parameter identity, not schema alone; retain numerical validation, specification comparison and hardware decision as separate fields.
4. Calibrate electrical switching dynamics at matching reference conditions, including capacitance versus voltage, gate resistance and tail behavior; investigate leakage recovery and add diode reverse recovery with sourced parameters. The 0.5 V diode-knee test is calibration recovery, not independent validation.
5. Finish and validate the existing closed-loop run_desat_test implementation. The two inspected desat_test result folders have no validation.json. Recorded-waveform firmware replay establishes logic behavior, not physical fault clearing; distinguish fault onset, detection, trip command and current clearance.
6. Add isolated electrical fault cases and diagnostic checks after the healthy model is trustworthy. Refresh README/status and provide one reproducible electrical experiment manifest with preserved artifacts.

Newer diode results and dynamic_20261017_195453_347 exist; datasets.py marks dynamic_20261017_194219_720 superseded after the assumed diode-knee change. Earlier status entries describe historical states. No Wabtec device identity or acceptance limits have been established.

## Validation guards completed 2026-10-17 22:00

- `analyze_dynamic.m` now checks every raw channel covers the configured interval without sampling gaps larger than the configured solver maximum step. It rejects an insufficient final event window and unresolved OFF-event current clearance using the existing 1 percent current / 99 percent bus-voltage criterion.
- `virtual_lab/tester.py` now includes missing required slide keys, unknown states and missing/nonfinite values in the unverified decision. The dashboard passes the full required tile set to the verdict and shows pending tiles, instead of discarding them. Existing numerical limits were not relaxed.
- Executed MATLAB batch saved-data regression: **11/11 PASS**. Coarse/fine records from the 48 V RL and traction RL runs remain accepted; coarse peak voltage/current, bus energy and energy residual match their saved metrics. Seven incomplete/corrupted-record cases are rejected with the expected errors. No new physical simulation was run.
- Executed Python/Streamlit regression: **9/9 PASS**, including the rendered dashboard with deliberately withheld DESAT evidence. Initial Python attempt assumed no new traction DESAT data existed; newer files invalidated that test precondition. The regression now explicitly withholds evidence in memory and leaves the newer implementation/results intact.
- Evidence: `results/validation_guard_regression_20261017_215823_664/` (`matlab_regression.json`, `matlab_regression.log`, `python_regression_02.log`). Reproduction instructions: `tests/README.md`. Pre-edit source copies: `archive/before_validation_guards_20261017_210518_077/`.
- No existing SLX, device parameter file or saved simulation result was overwritten. These checks establish software behavior, not module acceptance; simulated hardware decision stays INCONCLUSIVE.
- Next: enforce permitted dynamic fixtures and decouple driver voltage from device calibration, then bind combined experiment evidence to exact parameter versions. Switching-model calibration and protection-current realism remain separate unfinished work. Newer DESAT/dashboard work appeared during this task and was preserved; earlier notes about missing DESAT output are historical.

## Presentation circuit assets 2026-10-17

- Created `results/presentation_20261017_220620_549/slide/igbt_test_cell_slide.{png,svg,pdf}`: a 16:9 electrical schematic, PNG 3840 x 2160 and vector SVG/PDF. Labels show the saved source/fixture parameters, gate command, freewheel path, DUT and acquisition functions. Engineering simplifications are documented alongside the drawing. The drawing was visually inspected and checked against build_rig wiring; it is not a new physical simulation.
- Added reusable `docs/render_circuit_slide.py` and `+testcell/export_presentation.m`.
- Separate cosmetically formatted SLX and real Simulink screenshots are in `results/presentation_20261017_220620_549/simulink_final/`. MATLAB batch compilation/export completed with exit code 0. Auto-layout warnings are retained. The first export encountered a locked library subsystem; the exporter now arranges only the five project-created subsystems. Intermediate outputs were preserved.
- Original source model SHA256 remained `70E1CDA3BBB450DFBDE08E77DB6D020F774D040819F5D63DCD8B53A96F98E5A0`. Device parameters and original models were not modified. No new electrical simulation or protection validation was performed.

## Detailed native Simulink circuits completed 2026-10-17

- User requested maximum visible electrical detail in native Simulink, with the supplied hardware schematic as a layout reference. Added `+testcell/build_detailed_models.m`; expanded the five project subsystems from the preserved RL model into actual top-level connected components. Library device internals remain the selected Simscape models, not invented transistor-level hardware.
- Final deliverables: `results/detailed_simulink_20261017_221616_239/build02/final/wabtec_igbt_test_cell.slx` and `wabtec_igbt_desat_test.slx`, with matching high-resolution PNG and vector PDF exports. The final-folder README gives open/run commands and limitations.
- RL sheet contains the physical supply, R/L load, commutation impedance, diode/capacitor, detailed IGBT, driver, eight sensors/converters/raw logs/meters, four explicit pulse edges, three scopes, terminal-power/energy observer and KCL residual. The separate DESAT sheet exposes precharge, short-circuit network, sampled comparator, blanking, latch and actual gate inhibit.
- Executed RL compile and 2 us initialization, full 1.5 ms run and half-step run: existing analyzer assertions PASS; peak Vce/Ic and bus-energy differences from the source are below 2.3e-7 relative. Event-energy step differences are below 1.5e-5 relative. Visible terminal-energy integrator cross-check passed. Raw outputs and `rl_validation.json` are retained in build02/.
- The DESAT layout was compiled and initialized; no new full short-circuit run. Both final cosmetic copies passed compile and 2 us initialization (`final/layout_validation.json`). Full RL results apply to the pre-cleanup electrical-equivalent sheet; only annotations/routing were changed for the final copies.
- Two implementation issues were corrected without loosening checks: deleting the old command left a dangling input line (now removed before reconnecting); JSON column-vector pulse times broke transient plotting (normalized to a row). Physics checks had already passed before the plotting failure, so exports resumed from saved raw results instead of repeating simulations. Generated subsystem area annotations and literal newline text were cleaned up in separate final copies.
- Original reference SLX files and device parameters remain preserved. Source DESAT response is about 24.42 us from detection to the defined current-clearance criterion and does not demonstrate a 10 us clearing response. Short-circuit current and tail dynamics remain uncalibrated. Hardware verdict stays INCONCLUSIVE; hardware-only features from the example were not fabricated.

## Russian engineering PDF report completed 2026-10-18

- Delivered `deliverables/engineering_report_ru_20261018_002741/release/Wabtec_IGBT_Test_Cell_Electrical_Report_RU.pdf` (20 pages), with a self-contained HTML, dated source list, equipment-budget CSV, evidence JSON and two vector hardware diagrams. Earlier review drafts, technical_report_revB and diagram v2 remain preserved.
- Covers parameter selection and rationale, actual proposed instruments, published USD prices versus custom-build estimates, electrical topology, operator procedure, simulation operation, real bench tests, independent benchmarking, decision/uncertainty rules and a conditional 210 s time budget. HV/large-current qualification is explicitly separate from the LV bench budget.
- Published-instrument subtotal is USD 5,896.13. Custom hardware allowance USD 2,530–4,850 yields option A USD 8,426.13–10,746.13, excluding taxes/shipping. Optional Keithley 2450 adds USD 7,880 for guarded static measurements. A 20% project contingency is shown separately; neither option is a complete locomotive HV qualification cell. Manufacturer/distributor URLs and availability limitations are included.
- Important source correction: inspected the PPTX speaker notes, not only extracted slide text. They do confirm about 3.5 minutes per IGBT, citing IM-LE-0008 step 14; the original OEM instruction itself is unavailable. Notes to slide 8 define protection relative to detection. Slide 6 supplies 100 VAC; 25 kHz and a two-key DUT topology in diagram v2 remain unverified assumptions.
- Recomputed DESAT timestamps from `results/desat_test_traction_20261018_000313_736/desat_waveforms.csv`: first observed FaultNow 27.55 us, latch 27.60 us, interpolated VGE below 6.3 V 29.542 us. The 10%-peak current criterion is at 52.025 us: about 24.475 us from the first FaultNow sample, or 24.425 us from the latch. The report distinguishes these origins and does not claim 10 us current clearing.
- PDF generation/QA: Chromium print, 20/20 nonempty pages, Cyrillic text extraction, 35 hyperlink annotations, no HTML page overflow; selected pages visually inspected. Generation script and source evidence are retained. No new simulation, hardware experiment, purchasing or external messaging was performed for this report.


## Dashboard cleanup - 2026-10-18
- Removed screenshot-marked header explanation, MATLAB source/run/static-check/limits badges, excluded-runs sidebar expander and caption, and excluded-DESAT warning banner from app_virtual_lab.py.
- Preserved measurement tiles, simulated provenance, hardware INCONCLUSIVE badge, verdict logic, and saved results. Detailed model limitations remain in Model validation.
- Validation: 11 targeted dashboard/verdict tests passed; live Playwright checks passed on localhost:8599. Preview: deliverables/ui_cleanup_20261018_0120/dashboard.png.
- Next: review refreshed dashboard. Electrical-model limitations unchanged.

- Additional UI cleanup: removed sidebar Reference conditions block at user request. Streamlit render check passed; simulation and verdict logic unchanged.

## Targeted code review - 2026-10-18 morning
- Re-ran dashboard/verdict unittest suite: 11/11 passed. No new MATLAB simulation executed.
- Remaining engineering limits: uncalibrated current tail and omitted diode reverse recovery; estimated driver power excludes quiescent losses; DESAT detection tile checks occurrence without a maximum detection-delay criterion; related records selected by schema rather than immutable experiment identity.
- Next priority: bind dynamic/static/diode/DESAT evidence to the same device parameter identity before extending fault classification. No implementation or saved results changed by this review.

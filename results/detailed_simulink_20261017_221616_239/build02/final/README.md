# Detailed electrical Simulink diagrams

These are executable native SLX models, not illustrations or empty architecture blocks.

## Open the RL test circuit

From the project root in MATLAB:

```matlab
open_system('results/detailed_simulink_20261017_221616_239/build02/final/wabtec_igbt_test_cell.slx')
```

The top sheet shows the actual DC supply, R-L load, stray inductance/resistance,
freewheel diode and explicit junction capacitor, N-Channel IGBT, physical gate
driver, gate resistor, all eight sensors and acquisition chains. Four Step
blocks explicitly generate the 50/300/400/500 us pulse edges.

The three Scope blocks show gate, switching and freewheel signals. Open them
before clicking Run. Meter blocks display instantaneous simulated values.
The right-hand observers calculate Vce*Ic, its terminal-energy integral and
the IL-Ic-Id current-continuity residual. They do not drive the plant.

## Open the protection circuit

```matlab
open_system('results/detailed_simulink_20261017_221616_239/build02/final/wabtec_igbt_desat_test.slx')
```

This separate experiment shows the bus precharge command/filter, short-circuit
power path, gate driver, voltage/current sensors, sampled Vce comparator,
blanking window, latched trip, gate inhibit and raw logs. It preserves the
previous DESAT model. Do not connect its short-circuit branch to the RL fixture.

Both SLX files carry their required stimulus data or explicit constants.
They need MATLAB/Simulink/Simscape Electrical, but not the Python dashboard.
Use zoom in Simulink to inspect individual components. PNG and vector PDF
exports have the same base names as the SLX files.

## What was actually checked

- The expanded RL circuit was compiled, initialized for 2 us, and simulated for
  the full 1.5 ms. Existing electrical assertions passed. A half-step rerun
  passed the existing 3 percent event-terminal-energy convergence check.
- Peak Vce, peak Ic and bus energy agree with the source run to better than
  2.3e-7 relative error. The visible energy integrator agrees with quadrature
  within the explicit numerical check. See ../rl_validation.json and raw MATs.
- Both final cosmetic SLX copies were compiled and initialized for 2 us.
  See layout_validation.json. Their full simulations were not repeated after
  the final annotation cleanup.
- The new DESAT sheet was not given a new full short-circuit validation run.
  Its source is results/desat_test_traction_20261017_212553_145. That source
  reports detection 7.6 us after gate-on and current below 10 percent of peak
  32.02 us after gate-on, or 24.42 us after detection. It does not demonstrate
  a 10 us current-clearing response. Its short-circuit current level is uncalibrated.

## Engineering boundaries

The CM1500HC-66XB is a representative module, not an identified Wabtec part.
Load and several parasitic/driver parameters are illustrative assumptions.
The diode lacks reverse recovery; the IGBT tail dynamics remain incompletely
calibrated. Vce*Ic integration is terminal energy, not calibrated pure Eon/Eoff.
Sensors/converters are ideal; analog bandwidth, ADC noise and quantization
are not included. AC/DC and 24 V auxiliary supplies, optical isolation,
CAN/USB and hardware interlocks from the user's example are not implemented
as hardware circuits. No physical dimensions or hardware acceptance limits
are inferred. Hardware health remains INCONCLUSIVE.

Reproduce new models with `testcell.build_detailed_models`. Existing reference
models and results are preserved. Earlier failed/intermediate exports remain
in the parent folders; use this final/ folder for the deliverable models.

# Electrical laboratory architecture and requirements traceability

The validated ideal-switch baseline is preserved under results/20261017_163035_757. New detailed fixtures are separate generated models using shared +testcell functions. Rebuilds and experiments create unique output folders and retain parameters, raw SimulationOutput, source snapshots, tables and numerical checks.

## Evidence categories

1. Executed numerical validation: a model passed the stated circuit-law, calibration-recovery or convergence check. This is not validation against a physical device.
2. Illustrative simulation: circuit operation for explicitly assumed parameters.
3. Assumed device parameters: values in testcell.parameters, including the I-V calibration points, capacitances, stored-charge time, resistances, test voltage, load and fixture parasitics. These are not ratings.
4. Unverified hypotheses: correspondence of those parameters/faults to a particular locomotive module. Device identity, measurements, datasheet and approved acceptance limits remain missing.

## Primary source

references/NU IEEE 2026 IGBT test cell_AK_Final.pptx, SHA256 85AE5E16E96CBA88A343F8D171894B0D10121FED24CAB68777060BD33288C611.

| Requirement | Evidence | Implementation/meaning |
|---|---|---|
| +15 V ON, -15 V OFF | Slides 5, 8 | Gate Driver electrical output with finite impedance. Does not establish gate absolute maximum. |
| Approximately +4 to +7 V turn-on region | Slide 8 | Assumed model threshold 6 V; a real threshold needs an explicit current criterion and temperature. |
| Approximately 10 us protection | Slides 5, 8 | Future detector timing must separate blanking, threshold persistence, command delay, gate discharge and current clearing. |
| Characterize before installation | Slides 9-11 | Static I-V, leakage and Vce(sat), then R/RL dynamic tests. |
| Parameter choice, duration, instructions, report, cost | Slide 11 | Test matrix and experiment records; hardware limits and cost sourcing remain separate work. |
| 3.5 minute reference duration | User-supplied, not in extracted slide text | Not used as electrical simulation duration or a device qualification requirement. |
| Busbar insulation leakage up to 2 mA | Slide 5 | Separate insulation measurement; not transistor leakage acceptance. Test voltage unspecified. |
| Driver power up to 20 W, di/dt 0-5000 A/us | Slide 5 | Reference context; not enough information to infer driver current, module current/voltage ratings or test limits. |

## Modular fixtures

- DUT: installed N-Channel IGBT with fundamental nonlinear I-V equations, finite terminal capacitances and PNP forward transit time. Electrical validation initially uses a fixed device temperature, without thermal feedback.
- GateDrive: DC gate supply with finite resistance in static fixtures; physical Gate Driver plus external resistor in switching fixtures. Measures actual terminal Vge and Ig. No dead-time requirement exists for a single active low-side device; a future half bridge needs validated interlocking.
- Supply: controlled voltage or controlled current fixture for static tests, DC bus for switching tests. Voltage fixture has 0.1 ohm ballast; report measured device Vce, not source setpoint, as the characteristic x coordinate.
- LoadBank: resistive load or series R-L, commutation inductance with resistance, freewheel diode back to the positive bus, and diode capacitance.
- Measurements: terminal Vge/Vce and collector/gate/load/bus/diode currents with explicit sign conventions. Ideal sensors are validated first; noise and bandwidth are separate acquisition effects.
- Experiment controller: explicit source trajectories, repeated cases, deterministic parameter inputs, unique outputs. Model workspace stores the default stimulus so saved models can run independently.

## Static experiments

| Experiment | Independent conditions | Numerical checks |
|---|---|---|
| Calibration recovery | Assumed 20 A / 2 V / 15 V gate at 25 C; 2.4 V at 125 C | Recover supplied calibration points; this tests parameterization and wiring, not physical accuracy. |
| Output characteristics | 25/75/125 C; gate 5/7/10/15 V; multiple force voltages | Settling, finite values, monotonic current; record actual terminal Vce. |
| Vce(sat) versus current | 1-40 A current-clamp; gate 15 V; three temperatures | Settling, increasing Vce with current, calibration consistency. Ideal current source is a numerical characterization fixture, not a hardware circuit proposal. |
| Leakage | Gate -15 and 0 V; 12/24/48/72/100 V; three temperatures | Settling and recovery of assumed leakage at calibration voltage. No avalanche or breakdown characterization. |

The original 50 us stepped sweep and a filtered-source sweep failed numerical checks near the turn-on region. The present static fixture solves independent DC operating points and checks consistency over 2 us. The 25 C cases pass; an intermediate-temperature voltage point still stalls. That temperature issue is blocked after three approaches. It has no relation to production contact stabilization or instrument integration time. Three temperatures are imposed; this is not self-heating or a chamber response model.

## Dynamic experiments and validation

A low-side switch controls a 48 V, 2 ohm / 1 mH load, with a 100 nH commutation inductance and 0.01 ohm series resistance. All values are illustrative. The freewheel diode conducts from the switch node to the positive bus after turn-off. The initial diode implementation has piecewise-linear conduction and explicit capacitance. Reverse-recovery stored charge is not yet modeled; capacitance must not be described as reverse recovery.

Double pulse: first ON 50-300 us, OFF 300-400 us, second ON 400-500 us, then OFF until 1.5 ms. First pulse establishes inductor current; the freewheel interval enables hard commutation at the second turn-on. The 0.5 ms load L/R time constant justifies this experiment scale. Extend the final interval when measuring complete load-energy discharge.

Required checks: KCL (IL = Ic + Id), OFF diode-current continuity, integrated inductor voltage law, complete terminal energy accounting including change in stored energy, and repeat with half maximum solver step for switching-energy convergence. Use raw solver timestamps for integrations. Switching event windows and threshold crossing definitions must be saved with results.

Terminal energy integral int(Vce*Ic dt) contains conduction and reactive-energy transfer. It is not automatically pure switching dissipation. Gate input energy and charge storage matter. Thermal coupling will use the device heat flow or a separately validated loss formulation to avoid double counting.

## Next validated layers

After electrical tests pass: characterize the detailed diode charge model; add independently validated thermal RC impedance and electrothermal feedback; add desaturation logic with explicit blanking/persistence/propagation times; then inject one fault at a time. Parameter tolerances, measurement noise, degradation and Monte Carlo distributions are explicitly assumed until fleet/device data exist. Hardware decisions stay INCONCLUSIVE without approved test conditions and limits.

Official model reference: https://www.mathworks.com/help/simscape-electrical/ref/nchanneligbt.html

The off interval was extended to 100 us after the original 50 us gap left approximately 1.5 percent tail current near the second pulse for this assumed TF=0.2 us / BF=50 model. This is an observed model property, not a locomotive module specification. Current-clearance times are measured separately from gate command delay. No transit time was shortened to force agreement with the 10 us protection reference.


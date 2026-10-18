# Single-IGBT simulated switching baseline

This project is a NU-Wabtec IEEE Hackathon 2026 simulation baseline. The MATLAB scripts inspect the installed libraries, generate an SLX model, run it, log measurements, check switching behavior, and export plots. See PROJECT_STATUS.md for current progress. The first successful run is results/20261017_163035_757; its validation.json and resume_baseline_01.log provide execution evidence.

## Circuit and assumptions

- The topology is an ideal 12 V DC source, 100 ohm resistor, collector current sensor, IGBT collector, and grounded emitter in series. Voltage sensors measure gate-to-emitter and collector-to-emitter directly. Positive current flows into the collector. These are ideal sensors with no loading.
- Supply/load values and device electrical parameters are illustrative. The +15/-15 V gate command is supported by Wabtec presentation slides 5 and 8. No manufacturer, part number, voltage/current rating, safe operating area, gate absolute maximum, thermal rating, or datasheet fit is specified or inferred.
- The installed IGBT (Ideal, Switching) block is selected for a minimal functional baseline. Its gate is an electrical conserving port. Explicit illustrative parameters are threshold 6 V, forward drop 0.8 V, ON resistance 0.1 ohm, and OFF conductance 1e-8 S. Thermal ports are disabled. All remaining library defaults are recorded in selected_blocks.txt; inactive diode and thermal tables are illustrative defaults, not device ratings.
- The Gate Driver uses its physical-signal logic input and electrical G/S output connected to IGBT gate/emitter. The demanded output levels are +15 V ON and -15 V OFF. This is compatible with the selected threshold-based ideal model, which does not enforce real-device gate voltage limits. It establishes no permission to use these voltages on an unspecified physical IGBT.
- Driver logic is 0/1, 500 Hz, 50 percent duty cycle, with its first rising edge at 1 ms. The run lasts 6 ms and begins OFF. Driver output impedance, hysteresis, and propagation delay use the installed illustrative defaults recorded in driver_interface.txt. There is no explicit gate capacitance in this ideal IGBT, so the result cannot characterize gate charge, Miller effects, realistic switching time, or switching energy.
- The load is purely resistive. There is no intentional inductor, DC-link capacitor, freewheel diode, snubber, or stored load energy. The block's external protection-diode setting means no integral diode is added. The ideal source has unlimited energy over unlimited time; the short simulation limits this test to millijoules. Source power is bounded by approximately 1.44 W for this topology.
- Expected steady ON current is approximately (12-0.8)/(100+0.1) = 0.111888 A, and Vce is approximately 0.811189 V. Expected OFF current is approximately 0.12 microampere from the illustrative leakage conductance, and Vce is approximately 12 V.
- The variable-step ode23t solver uses maximum step 2 microseconds, relative tolerance 1e-6, and absolute tolerance 1e-8. Validation excludes 200 microseconds around switching edges. Exported waveforms use a 2 microsecond grid; raw solver times and full simulation output are retained in baseline_results.mat. This is baseline functional validation, not a numerical convergence study or device certification.
- No fault injection is configured.

## Reproduce from PowerShell

Run from this project directory with MATLAB on PATH:

```powershell
matlab -batch "run('inspect_libraries.m')" -logfile inspect_batch.log
matlab -batch "build_baseline" -logfile baseline_batch.log
```

build_baseline.m creates a unique results folder for each run and refuses to build when igbt_baseline is already loaded. Existing result folders and models are preserved. Use verify_saved_baseline with an absolute SLX path to compile and rerun an existing model without rebuilding or saving it. Verification also uses a new result folder.

## Outputs (generated files are inside each run folder)

- library_inspection.txt: installed product versions, matching electrical blocks, and IGBT mask defaults.
- selected_blocks.txt and port_mapping.txt: inspected interfaces and actual build wiring information.
- driver_interface.txt: driver parameter values before the explicit +15/-15 V overrides.
- igbt_baseline.slx: generated physical circuit, solver, and sensor logging blocks.
- baseline_results.mat: raw SimulationOutput, including Vge, Vce, Ic timeseries and Simscape logging.
- baseline_waveforms.csv / .png / .fig: sampled numerical data and three waveform plots.
- validation.json: successful assertion results and computed source energy.
- Batch logs are in the project root. Historical baseline_batch.log records the interrupted wiring failure; resume_baseline_01.log records the successful corrected build.

These assertions are numerical model checks, not manufacturer acceptance limits. The validation checks all three ON and OFF plateaus, gate levels within 0.01 V, ON current within 0.1 mA of the circuit equation, ON Vce within 0.01 V, OFF current below 1 microampere, OFF Vce within 0.01 V of the supply, KVL within 0.01 V, and three rising gate edges with at least two falling edges. Assertions fail the batch process when these conditions do not hold.

References: [IGBT (Ideal, Switching)](https://www.mathworks.com/help/simscape-electrical/ref/igbtidealswitching.html) and [Gate Driver](https://www.mathworks.com/help/simscape-electrical/ref/gatedriver.html). Installed R2026b block masks are the implementation source of truth.

Primary engineering source: references/NU IEEE 2026 IGBT test cell_AK_Final.pptx (slides 5, 8, 10 and 11). SHA256: 85AE5E16E96CBA88A343F8D171894B0D10121FED24CAB68777060BD33288C611. Slide 11 requires parameter coverage, justified duration, instructions, reports and approximate equipment cost. The user-supplied 3.5-minute reference is not stated in the extracted slide text. Future hardware thresholds require device identification and defined test conditions.


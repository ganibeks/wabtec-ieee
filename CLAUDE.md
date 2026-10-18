# CLAUDE.md — session rules for the IEEE × Wabtec IGBT Test Cell project

MATLAB R2026b + Simscape Electrical on Windows 11; Python available.

## Results preservation
- Never delete or overwrite anything in `results/`. Every run creates a new folder (`testcell.new_run`).

## Device parameters
- Do not edit `+testcell/parameters.m` (validated 48 V baseline).
- The locomotive-class device is `+testcell/parameters_traction.m` (Mitsubishi CM1500HC-66XB,
  3.3 kV / 1500 A). It is a representative traction module, NOT a confirmed Wabtec part.
- With `parameters_traction`, run ONLY `'dynamic_rl'`, NEVER `'dynamic_r'`
  (the 0.01 ohm load would draw about 180 kA).

## Validation honesty
- Never loosen assertion thresholds or tolerances to make a check pass.
- Never call anything "validated" unless its validation JSON says PASS.
- The hardware decision always stays INCONCLUSIVE. Do not invent Wabtec ratings or acceptance limits.
- `results/dynamic_20261017_165503_678/rl_diagnostic.csv` is SUPERSEDED (failed).
  `results/electrothermal_*` is NOT_VALIDATED. Never present either as valid.

## Data and provenance
- Every displayed number must come from simulation data. Never fabricate values for visuals.
- Label data provenance everywhere: SIMULATED / PRESET-DEMO / MEASURED / ASSUMED.
- Report actual command output. Never assume success.

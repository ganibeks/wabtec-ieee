# Presentation assets

Use **slide/igbt_test_cell_slide.png** for a slide (3840 x 2160, 16:9).
Use **slide/igbt_test_cell_slide.svg** for vector graphics in PowerPoint;
the PDF is also vector. Labels are in English for the hackathon presentation.

The figure represents the saved double-pulse RL circuit. Power wiring,
diode polarity, capacitance branch and sensor locations follow the existing
fixture. Auxiliary sensor wiring and solver infrastructure are omitted for
readability; see slide/SCHEMATIC_NOTES.txt. The timing trace shows commands.

The source is results/dynamic_20261017_195453_347, a representative traction
device simulation. Fixture assumptions remain assumptions. This is not a
complete hardware tester schematic or a protection-validation result.

Open **simulink_final/tc_dynamic_rl.slx** for the separate formatted model.
It was compiled successfully in MATLAB batch mode; no new electrical
simulation was run. Screenshots of the overview, DUT, gate driver and load
bank are in simulink_final/. The original model was preserved; its SHA256
before and after export is:

70E1CDA3BBB450DFBDE08E77DB6D020F774D040819F5D63DCD8B53A96F98E5A0

Earlier render/export attempts are retained in the parent folder and
simulink/. Use slide/ and simulink_final/ for the final assets.

Reproduction scripts: docs/render_circuit_slide.py and
+testcell/export_presentation.m. Export into a new empty folder to preserve
previous outputs. MATLAB layout warnings are recorded in matlab_export_03.log.

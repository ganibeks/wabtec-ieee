function folder = run_static(p)
if nargin<1, p=testcell.parameters; end
folder=testcell.new_run('static'); testcell.write_json(fullfile(folder,'parameters.json'),p);
rig=testcell.build_rig('static_v',p,folder); cleanup=onCleanup(@()close_system(rig.model,0)); %#ok<NASGU>
set_param(rig.model,'SimulationCommand','update');
% Targeted parameter-recovery checks before the full sweep matrix.
a=testcell.static_case(rig,p.VceCalibration_V+0.1*p.IcCalibration_A,15,25,'calibration_IV',folder);
assert(abs(a.Ic_A-p.IcCalibration_A)/p.IcCalibration_A<0.02,'25 C I-V calibration recovery failed.');
b=testcell.static_case(rig,100,0,25,'calibration_leakage25',folder);
assert(abs(b.Ic_A-p.leakageCalibration_A)/p.leakageCalibration_A<0.05,'25 C leakage recovery failed.');
c=testcell.static_case(rig,100,0,125,'calibration_leakage125',folder);
assert(abs(c.Ic_A-p.leakageSecond_A)/p.leakageSecond_A<0.05,'125 C leakage recovery failed.');
fprintf('STATIC TARGETED PARAMETER RECOVERY: PASS\n');
allPoints=table; temperatures=[25 75 125]; gates=[5 7 10 15];
for T=temperatures
 for gate=gates
  label=sprintf('output_T%d_G%d',T,gate);
  pts=testcell.static_case(rig,[0 .5 1 1.5 2 3 4 5 7 10 15],gate,T,label,folder);
  assert(all(diff(pts.Ic_A)>-1e-5),'Output characteristic not monotonic in forced voltage');
  allPoints=[allPoints;pts]; %#ok<AGROW>
 end
 for gate=[-15 0]
  pts=testcell.static_case(rig,[12 24 48 72 100],gate,T,sprintf('leak_T%d_G%d',T,gate),folder);
  allPoints=[allPoints;pts]; %#ok<AGROW>
 end
end
close_system(rig.model,0); clear cleanup;
rig=testcell.build_rig('static_i',p,folder); cleanup=onCleanup(@()close_system(rig.model,0)); %#ok<NASGU>
saturation=table;
for T=temperatures
 pts=testcell.static_case(rig,[1 2 5 10 20 30 40],15,T,sprintf('saturation_T%d',T),folder);
 assert(all(diff(pts.Vce_V)>0),'Vce(sat) must rise with forced collector current.');
 saturation=[saturation;pts]; %#ok<AGROW>
end
v25=saturation.Vce_V(saturation.temperature_C==25 & saturation.force_command==20);
v125=saturation.Vce_V(saturation.temperature_C==125 & saturation.force_command==20);
assert(abs(v25-2)<.04 && abs(v125-2.4)<.05,'Vce(sat) temperature calibration recovery failed.');
writetable(allPoints,fullfile(folder,'static_curves.csv')); writetable(saturation,fullfile(folder,'saturation.csv'));
testcell.plot_static(allPoints,saturation,folder);
checks=struct('status','PASS','scope','Equation model and assumed parameter recovery; no physical device validation', ...
 'hardware_decision','INCONCLUSIVE','output_points',height(allPoints),'saturation_points',height(saturation), ...
 'Vce_at20A25C_V',v25,'Vce_at20A125C_V',v125,'Ices25C_A',b.Ic_A,'Ices125C_A',c.Ic_A, ...
 'dc_consistency_interval_s',2e-6,'acceptance_limits','Not supplied; numerical checks only');
testcell.write_json(fullfile(folder,'validation.json'),checks);
fprintf('STATIC MATRIX PASS: %d points. Output: %s\n',height(allPoints)+height(saturation),folder);
end


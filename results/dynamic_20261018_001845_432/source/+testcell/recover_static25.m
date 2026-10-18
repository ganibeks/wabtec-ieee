function folder = recover_static25
% Reuse completed raw DC points; do not retry the blocked 75 C voltage fixture.
root=fileparts(fileparts(mfilename('fullpath')));
prior=fullfile(root,'results','static_20261017_165422_423');
folder=testcell.new_run('static25'); p=testcell.parameters;
testcell.write_json(fullfile(folder,'parameters.json'),p);
allPoints=table; files=dir(fullfile(prior,'*_T25_G*_raw.mat'));
for n=1:numel(files)
 d=load(fullfile(prior,files(n).name));
 label=erase(files(n).name,'_raw.mat');
 for k=1:numel(d.values)
  s=d.out{k}; testcell.assert_no_solver_warnings(s); x=testcell.measurements(s,{'Ic','Vce','Vge'}); ix=x.t>1e-6;
  row=table(string(label),d.T_C,d.gate,d.values(k),mean(x.Vce(ix)),mean(x.Ic(ix)),mean(x.Vge(ix)),max(x.Ic(ix))-min(x.Ic(ix)), ...
   'VariableNames',{'experiment','temperature_C','gate_command_V','force_command','Vce_V','Ic_A','Vge_V','settling_range_A'});
  allPoints=[allPoints;row]; %#ok<AGROW>
 end
end
assert(height(allPoints)==54,'Expected the 54 completed 25 C voltage-fixture points.');
writetable(allPoints,fullfile(folder,'static_curves.csv'));
rig=testcell.build_rig('static_i',p,folder); cleanup=onCleanup(@()close_system(rig.model,0)); %#ok<NASGU>
set_param(rig.model,'SimulationCommand','update');
sat=testcell.static_case(rig,[1 2 5 10 20 30 40],15,25,'saturation_T25',folder);
assert(all(diff(sat.Vce_V)>0),'Current-clamp saturation curve not monotonic.');
hot=testcell.static_case(rig,20,15,125,'saturation_calibration125',folder);
v25=sat.Vce_V(sat.force_command==20);
assert(abs(v25-2)<.04 && abs(hot.Vce_V-2.4)<.05,'Current-clamp calibration recovery failed.');
sat=[sat;hot]; writetable(sat,fullfile(folder,'saturation.csv'));
testcell.plot_static(allPoints,sat,folder);
record=struct('status','PARTIAL','hardware_decision','INCONCLUSIVE','numerical_checks','PASS for the listed completed cases', ...
 'voltage_fixture_points25C',height(allPoints),'current_fixture_points',height(sat), ...
 'Vce20A25C_V',v25,'Vce20A125C_V',hot.Vce_V,'prior_raw_folder',prior, ...
 'blocked','Intermediate-temperature voltage fixture numerical stiffness; stopped after three approaches', ...
 'scope','25 C output/leakage plus current-clamp and two-temperature calibration; not a complete temperature matrix');
testcell.write_json(fullfile(folder,'validation.json'),record);
fprintf('PARTIAL STATIC CHARACTERIZATION: %d completed points. %s\n',height(allPoints)+height(sat),folder);
end

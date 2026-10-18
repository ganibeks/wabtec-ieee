function folder = analyze_electrical
% Electrical-only assessment of existing validated results; no new simulation.
root=fileparts(fileparts(mfilename('fullpath')));
sdir=fullfile(root,'results','static25_20261017_165838_504');
ddir=fullfile(root,'results','dynamic_20261017_165933_696');
s=readtable(fullfile(sdir,'static_curves.csv'));
c=readtable(fullfile(sdir,'saturation.csv'));
v=jsondecode(fileread(fullfile(ddir,'dynamic_rl_validation.json')));
p=jsondecode(fileread(fullfile(ddir,'parameters.json')));
assert(strcmp(v.status,'PASS'),'Dynamic reference is not validated.');
% Use a single common operating condition; do not combine unlike test conditions.
s=s(s.temperature_C==25,:); c=c(c.temperature_C==25,:);
assert(height(s)==54 && height(c)==7,'Unexpected reference coverage.');
assert(all(isfinite([s.Vce_V;s.Ic_A;c.Vce_V;c.Ic_A])));
folder=testcell.new_run('electrical_assessment');
getLeak=@(voltage)s.Ic_A(s.gate_command_V==-15 & s.force_command==voltage);
getVce=@(current)c.Vce_V(c.force_command==current);
r=struct('scope','Electrical-only assumed-device assessment', ...
 'simulation_status','Executed reference electrical tests PASS; full characterization incomplete', ...
 'hardware_decision','INCONCLUSIVE','acceptance_limits','Not supplied', ...
 'static_reference',sdir,'dynamic_reference',ddir,'static_points_used',height(s)+height(c));
r.gate_on_V=p.gateOn_V; r.gate_off_V=p.gateOff_V;
r.Vce_at20A_V=getVce(20); r.conduction_power_at20A_W=20*r.Vce_at20A_V;
r.apparent_Vce_over_I_at20A_Ohm=r.Vce_at20A_V/20;
r.incremental_on_resistance_10to30A_Ohm=(getVce(30)-getVce(10))/20;
r.leakage_at48V_A=getLeak(48); r.leakage_at100V_A=getLeak(100);
r.peak_Vce_V=v.peak_Vce_V; r.overshoot_above48V_V=v.peak_Vce_V-p.bus_V;
r.peak_Ic_A=v.peak_Ic_A; r.peak_Ig_A=v.peak_Ig_A;
r.external_gate_resistance_Ohm=p.RgateExternal_Ohm;
r.total_nominal_gate_resistance_Ohm=p.RgateExternal_Ohm+p.RdriverOn_Ohm+p.RgInternal_Ohm;
r.simple_gate_RC_s=r.total_nominal_gate_resistance_Ohm*p.Cies_F;
r.expected_initial_gate_peak_A=(p.gateOn_V-p.gateOff_V)/r.total_nominal_gate_resistance_Ohm;
r.normal_turnoff_clearance_1percent_s=[v.events([2 4]).current_clearance_1percent_s];
r.second_turnon_voltage_transition_s=v.events(3).Vce_transition_10_90_s;
r.second_turnon_current_transition_s=v.events(3).Ic_transition_10_90_s;
r.positive_gate_charge_minus15to15_C=v.events(3).gate_charge_C;
r.supply_energy_J=v.bus_energy_J;
r.collector_terminal_energy_J=v.dut_collector_terminal_energy_J;
r.energy_balance_relative_error=v.energy_balance_relative_error;
r.max_half_step_event_energy_change=max(v.half_step_event_energy_relative_errors);
r.electrical_limitations={'No manufacturer rating or SOA validation','No oxide breakdown or DC gate leakage characterization', ...
 'Freewheel reverse-recovery charge not modeled','No desaturation fault-response validation', ...
 'Finite-window terminal energy is not calibrated switching dissipation', ...
 'Current-clearance criterion is a measurement definition, not an acceptance limit'};
gates=[5 7 10 15]'; currentAt2=zeros(size(gates));
for k=1:numel(gates)
 ix=s.gate_command_V==gates(k) & startsWith(s.experiment,'output');
 [voltage,order]=sort(s.Vce_V(ix)); current=s.Ic_A(ix); current=current(order);
 currentAt2(k)=interp1(voltage,current,2,'linear');
end
gateComparison=table(gates,currentAt2,'VariableNames',{'Vge_V','interpolated_Ic_at_Vce2V_A'});
writetable(gateComparison,fullfile(folder,'gate_comparison.csv'));
writetable(c(:,{'force_command','Vce_V','Ic_A','Vge_V'}),fullfile(folder,'conduction_characteristic.csv'));
testcell.write_json(fullfile(folder,'electrical_assessment.json'),r);
fid=fopen(fullfile(folder,'README.md'),'w'); cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
fprintf(fid,'# Electrical assessment\n\nExisting reference results were analyzed; no new physical simulation was executed.\n\n');
fprintf(fid,'Vce at 20 A: %.6g V; corresponding instantaneous conduction power: %.6g W.\n\n',r.Vce_at20A_V,r.conduction_power_at20A_W);
fprintf(fid,'Leakage: %.6g microampere at 48 V; %.6g microampere at 100 V. These are simulated values, not acceptance limits.\n\n',r.leakage_at48V_A*1e6,r.leakage_at100V_A*1e6);
fprintf(fid,'RL test: peak Vce %.6g V, peak Ic %.6g A, gate peak %.6g A. Normal turn-off current clearance is approximately %.6g microseconds, distinct from the unimplemented desaturation/protection delay.\n\n',r.peak_Vce_V,r.peak_Ic_A,r.peak_Ig_A,mean(r.normal_turnoff_clearance_1percent_s)*1e6);
fprintf(fid,'Electrical solution and diagnostic sequence: ../../../docs/ELECTRICAL_SOLUTION.md. Hardware decision: INCONCLUSIVE.\n');
disp(r); disp(gateComparison); fprintf('ELECTRICAL ASSESSMENT: %s\n',folder);
end

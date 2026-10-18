function folder = run_electrothermal
p=testcell.parameters; p.electrothermal=true;
folder=testcell.new_run('electrothermal'); testcell.write_json(fullfile(folder,'parameters.json'),p);
rig=testcell.build_rig('dynamic_rl',p,folder); cleanup=onCleanup(@()close_system(rig.model,0)); %#ok<NASGU>
set_param(rig.model,'SimulationCommand','update');
fprintf('ELECTROTHERMAL COMPILE PASS\n');
in=Simulink.SimulationInput(rig.model); in=in.setModelParameter('StopTime','2e-6');
initial=sim(in); testcell.assert_no_solver_warnings(initial);
assert(all(isfinite(initial.Tj.Data)),'Invalid thermal initialization');
fprintf('ELECTROTHERMAL INITIALIZATION PASS\n');
out=sim(rig.model); save(fullfile(folder,'electrothermal_raw.mat'),'out','p');
testcell.assert_no_solver_warnings(out); electrical=testcell.analyze_dynamic(out,p,'dynamic_rl');
x=testcell.measurements(out,{'Vge','Vce','Ic','Ig','IL','Id','Ibus','Vswitch','Tj','Tc','DeviceHeat'});
th=p.thermal;
energy=trapz(x.t,x.DeviceHeat);
stored=th.Cj_J_K*(x.Tj(end)-x.Tj(1))+th.Cc_J_K*(x.Tc(end)-x.Tc(1));
ambient=trapz(x.t,(x.Tc-th.ambient_K)/th.Rca_K_W);
thermalError=abs(energy-stored-ambient)/max(abs(energy),1e-8);
assert(thermalError<.005,'Coupled thermal energy balance failed.');
assert(x.Tj(end)>x.Tj(1) && all(x.Tj>=th.ambient_K-1e-4),'Junction temperature response invalid.');
% The port carries heat dissipation; terminal electrical integrals also change stored charge energy.
record=struct('status','PASS','hardware_decision','INCONCLUSIVE', ...
 'scope','Short low-energy electrothermal run near 25 C; broad temperature range remains unvalidated', ...
 'heat_energy_J',energy,'thermal_stored_energy_J',stored,'ambient_energy_J',ambient, ...
 'thermal_energy_relative_error',thermalError,'junction_rise_K',x.Tj(end)-x.Tj(1), ...
 'max_junction_C',max(x.Tj)-273.15,'electrical',electrical);
testcell.write_json(fullfile(folder,'validation.json'),record);
testcell.plot_dynamic(out,p,'electrothermal_switching',folder);
writetable(table(x.t,x.Tj,x.Tc,x.DeviceHeat,'VariableNames',{'time_s','Tj_K','Tc_K','heat_W'}),fullfile(folder,'electrothermal.csv'));
f=figure('Visible','off','Color','w'); tiledlayout(2,1);
nexttile; plot(x.t*1e3,1e3*[x.Tj-x.Tj(1),x.Tc-x.Tc(1)],'LineWidth',1.4); ylabel('Temperature rise (mK)'); legend('Junction','Case'); grid on;
nexttile; plot(x.t*1e3,x.DeviceHeat,'LineWidth',1.2); ylabel('Device heat flow (W)'); xlabel('Time (ms)'); grid on;
set(findall(f,'Type','axes'),'Color','w','XColor','k','YColor','k'); set(findall(f,'Type','text'),'Color','k');
exportgraphics(f,fullfile(folder,'electrothermal.png'),'Resolution',160,'BackgroundColor','white'); close(f);
fprintf('ELECTROTHERMAL PASS: heat %.6g J, junction rise %.6g K, thermal balance error %.3g. %s\n',energy,record.junction_rise_K,thermalError,folder);
end

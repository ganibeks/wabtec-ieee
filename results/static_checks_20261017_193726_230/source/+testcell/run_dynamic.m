function folder = run_dynamic(p,kinds)
if nargin<1, p=testcell.parameters; end
if nargin<2, kinds={'dynamic_r','dynamic_rl'}; end
folder=testcell.new_run('dynamic'); testcell.write_json(fullfile(folder,'parameters.json'),p);
allResults=struct;
for kind=kinds
 rig=testcell.build_rig(kind{1},p,folder); cleanup=onCleanup(@()close_system(rig.model,0)); %#ok<NASGU>
 set_param(rig.model,'SimulationCommand','update');
 fprintf('TARGETED COMPILE PASS: %s\n',kind{1});
 out=sim(rig.model); save(fullfile(folder,[kind{1} '_raw.mat']),'out','p');
 testcell.assert_no_solver_warnings(out);
r=testcell.analyze_dynamic(out,p,kind{1});
 testcell.plot_dynamic(out,p,kind{1},folder);
 % Validation JSON is written only after the half-step convergence check below,
 % so a convergence failure can never leave a PASS file on disk.
 % Half-step rerun tests event-energy convergence, not just visual similarity.
 in=Simulink.SimulationInput(rig.model); in=in.setModelParameter('MaxStep',num2str(p.dynamicMaxStep_s/2,17));
 fine=sim(in); save(fullfile(folder,[kind{1} '_fine_raw.mat']),'fine','p');
 testcell.assert_no_solver_warnings(fine);
 rf=testcell.analyze_dynamic(fine,p,kind{1});
 e=[r.events.gross_collector_terminal_energy_J]; ef=[rf.events.gross_collector_terminal_energy_J];
 rel=abs(e-ef)./max(abs(ef),1e-7);
 assert(all(rel<.03),'Switching event terminal energy failed 3 percent half-step convergence.');
 r.half_step_event_energy_relative_errors=rel; r.fine_max_step_s=p.dynamicMaxStep_s/2;
 testcell.write_json(fullfile(folder,[kind{1} '_validation.json']),r);
 allResults.(kind{1})=r;
 fprintf('%s: PASS; peak Vce %.3f V, Ic %.3f A, energy residual %.3g, convergence %.3g\n',kind{1},r.peak_Vce_V,r.peak_Ic_A,r.energy_balance_relative_error,max(rel));
 close_system(rig.model,0); clear cleanup;
end
testcell.write_json(fullfile(folder,'validation.json'),allResults);
fprintf('DYNAMIC VALIDATION COMPLETE: %s\n',folder);
end





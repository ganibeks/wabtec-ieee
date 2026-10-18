function targeted_checks
p=testcell.parameters; folder=testcell.new_run('targeted'); testcell.write_json(fullfile(folder,'parameters.json'),p);
for kind={'static_v','static_i','dynamic_r','dynamic_rl'}
 rig=testcell.build_rig(kind{1},p,folder);
 try
  set_param(rig.model,'SimulationCommand','update');
  fprintf('COMPILE PASS: %s\n',kind{1});
  in=Simulink.SimulationInput(rig.model); in=in.setModelParameter('StopTime','2e-6');
  out=sim(in); assert(all(isfinite(out.Ic.Data))); assert(all(isfinite(out.Vce.Data)));
  fprintf('INITIALIZATION PASS: %s\n',kind{1}); close_system(rig.model,0);
 catch ME
  close_system(rig.model,0); rethrow(ME);
 end
end
testcell.write_json(fullfile(folder,'targeted_checks.json'),struct('status','PASS','checks','4 fixture compilation and 2 us initialization','hardware_decision','INCONCLUSIVE'));
end

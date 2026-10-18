function [points,out] = static_case(rig,values,gate,T_C,label,folder)
% Independent DC operating points avoid forcing an artificial transient sweep.
% Each equilibrium is held for 2 us to check numerical drift, not instrument dwell.
values=values(:); step=2e-6;
set_param(rig.gate,'v0',num2str(gate));
set_param(rig.device,'Tdevice',num2str(T_C),'Tdevice_unit','degC');
ws=get_param(rig.model,'ModelWorkspace'); points=table; out=cell(numel(values),1);
for k=1:numel(values)
 assignin(ws,'tcSweep',timeseries([values(k);values(k)],[0;step]));
 in=Simulink.SimulationInput(rig.model);
 in=in.setModelParameter('StopTime',num2str(step,17),'MaxStep','1e-7');
 s=sim(in); out{k}=s;
 testcell.assert_no_solver_warnings(s);
 x=testcell.measurements(s,{'Ic','Vce','Vge'}); ix=x.t>step/2;
 assert(nnz(ix)>=3,'Insufficient DC consistency samples');
 row=table(string(label),T_C,gate,values(k),mean(x.Vce(ix)),mean(x.Ic(ix)),mean(x.Vge(ix)),max(x.Ic(ix))-min(x.Ic(ix)), ...
  'VariableNames',{'experiment','temperature_C','gate_command_V','force_command','Vce_V','Ic_A','Vge_V','settling_range_A'});
 points=[points;row]; %#ok<AGROW>
end
save(fullfile(folder,[label '_raw.mat']),'out','values','gate','T_C','step');
assert(all(points.settling_range_A<max(1e-7,abs(points.Ic_A)*1e-3)),'DC operating point drifted.');
end

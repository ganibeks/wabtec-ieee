function [points,out] = static_case(rig,values,gate,T_C,label,folder)
% Piecewise-constant force, 50 us per point; sample only final 10 us.
step=50e-6; values=values(:); time=(0:numel(values))'*step;
wave=timeseries([values;values(end)],time);
set_param(rig.gate,'v0',num2str(gate));
set_param(rig.device,'Tdevice',num2str(T_C),'Tdevice_unit','degC');
ws=get_param(rig.model,'ModelWorkspace'); assignin(ws,'tcSweep',wave);
in=Simulink.SimulationInput(rig.model);
in=in.setModelParameter('StopTime',num2str(time(end),17),'MaxStep','5e-7');
out=sim(in); save(fullfile(folder,[label '_raw.mat']),'out','values','gate','T_C','step');
testcell.assert_no_solver_warnings(out);
t=out.Ic.Time; current=out.Ic.Data; voltage=interp1(out.Vce.Time,out.Vce.Data,t); gateV=interp1(out.Vge.Time,out.Vge.Data,t);
assert(all(isfinite([t;current;voltage;gateV])),'Nonfinite static data');
points=table;
for k=1:numel(values)
 ix=t>(k-0.2)*step & t<(k-0.01)*step;
 assert(nnz(ix)>=3,'Insufficient settled samples');
 row=table(string(label),T_C,gate,values(k),mean(voltage(ix)),mean(current(ix)),mean(gateV(ix)),max(current(ix))-min(current(ix)), ...
  'VariableNames',{'experiment','temperature_C','gate_command_V','force_command','Vce_V','Ic_A','Vge_V','settling_range_A'});
 points=[points;row]; %#ok<AGROW>
end
assert(all(points.settling_range_A<max(1e-7,abs(points.Ic_A)*1e-3)),'Static point did not settle; extend dwell.');
end



function folder = run_diode_test(p,label)
% Free-wheeling diode check as specified on Wabtec slide 5: "0.2 V to 0.8 V, reverse direction - open".
% Emulates a multimeter diode-test mode on the model's freewheel diode (same Diode block and parameters
% as build_rig.m). Test conditions are ASSUMED typical DMM values: 1 mA forward test current, 3 V open-circuit.
%   forward: find V_AK at which I = 1 mA (bisection on a DC voltage source)
%   reverse: apply V_AK = -3 V; "open" if the diode cannot carry the 1 mA test current (DMM shows OL)
if nargin<1, p=testcell.parameters; end
if nargin<2, label='device'; end
Itest=1e-3; Vopen=3;
folder=testcell.new_run(['diode_test_' label]); testcell.write_json(fullfile(folder,'parameters.json'),p);
load_system('ee_lib'); load_system('fl_lib'); load_system('nesl_utility');
m='tc_diode'; assert(~bdIsLoaded(m),'Model already open: %s',m); new_system(m);
c=onCleanup(@()close_system(m,0));
set_param(m,'Solver','ode15s','RelTol','1e-9','AbsTol','1e-12','MaxStep','1e-7','StopTime','1e-6', ...
 'ReturnWorkspaceOutputs','on','SaveTime','on');
a=@(src,name,pos,varargin)testcell.add(m,src,name,pos,varargin{:}); w=@(x,y)testcell.wire(m,x,y); P=@testcell.ports;
src=a('fl_lib/Electrical/Electrical Sources/DC Voltage Source','DMM',[80 90 130 160],'v0','0'); S=P(src);
is=a('fl_lib/Electrical/Electrical Sensors/Current Sensor','IdSensor',[200 90 240 120]); IS=P(is);
d=a(sprintf('ee_lib/Semiconductors &\nConverters/Diode'),'FreewheelDiode',[320 90 370 120], ...
 'Vf',num2str(p.diodeVf_V,17),'Ron',num2str(p.diodeRon_Ohm,17),'Goff',num2str(p.diodeGoff_S,17)); Dd=P(d);
vs=a('fl_lib/Electrical/Electrical Sensors/Voltage Sensor','VakSensor',[420 140 460 190]); VS=P(vs);
g=a('fl_lib/Electrical/Electrical Elements/Electrical Reference','Ground',[300 260 340 290]); G=P(g);
sol=a('nesl_utility/Solver Configuration','Solver',[100 240 210 280],'DoDC','on'); SO=P(sol);
w(S.LConn,IS.LConn); w(IS.RConn(2),Dd.LConn); w(Dd.RConn,G.LConn); w(S.RConn,G.LConn); w(SO.RConn,G.LConn);
w(VS.LConn,Dd.LConn); w(VS.RConn(2),G.LConn);
testcell.log_signal(m,IS.RConn(1),'Id','A',[560 90 610 120]);
testcell.log_signal(m,VS.RConn(1),'Vak','V',[560 160 610 190]);
save_system(m,fullfile(folder,[m '.slx']));
set_param(m,'SimulationCommand','update');
    function [I,V]=point(v)
        set_param(src,'v0',sprintf('%.15g',v));
        out=sim(m); testcell.assert_no_solver_warnings(out);
        I=out.Id.Data(end); V=out.Vak.Data(end);
    end
% forward
lo=0; hi=Vopen; [Ihi,~]=point(hi); assert(Ihi>Itest,'Diode cannot reach the 1 mA test current within %g V',Vopen);
pts=zeros(0,3);
for k=1:60
 v=(lo+hi)/2; [I,V]=point(v); pts(end+1,:)=[v I V]; %#ok<AGROW>
 if I<Itest, lo=v; else, hi=v; end
 if abs(I/Itest-1)<1e-6, break; end
end
[~,j]=min(abs(pts(:,2)-Itest));
r=struct('scope','DMM diode-mode emulation on the model freewheel diode (slide 5 check)', ...
 'hardware_decision','INCONCLUSIVE','test_current_A',Itest,'open_circuit_V',Vopen, ...
 'test_conditions','ASSUMED typical multimeter diode mode (1 mA, 3 V)', ...
 'slide5_spec','Free-wheeling diode 0.2 V to 0.8 V, reverse direction - open');
r.forward_V=pts(j,3); r.forward_at_A=pts(j,2); r.forward_iterations=size(pts,1);
assert(abs(r.forward_at_A/Itest-1)<1e-4,'Forward bisection did not converge to the test current');
% reverse
[Ir,Vr]=point(-Vopen); r.reverse_V=Vr; r.reverse_A=Ir; r.reverse_open=abs(Ir)<Itest;
r.forward_within_slide5=r.forward_V>=0.2 && r.forward_V<=0.8;
r.model_note=sprintf('Piecewise-linear diode: V(1 mA) = Vf + Ron*1mA = %.6g V by construction; the result reflects the diode parameters.', ...
 p.diodeVf_V+p.diodeRon_Ohm*Itest);
r.status='PASS';  % numerical: no solver warnings, bisection converged
testcell.write_json(fullfile(folder,'validation.json'),r);
fprintf('DIODE TEST %s: forward %.6g V at %.6g A (slide 0.2-0.8 V: %d); reverse %.3g A at %.3g V (open: %d)\n', ...
 label,r.forward_V,r.forward_at_A,r.forward_within_slide5,r.reverse_A,r.reverse_V,r.reverse_open);
fprintf('DIODE TEST DONE: %s\n',folder);
end

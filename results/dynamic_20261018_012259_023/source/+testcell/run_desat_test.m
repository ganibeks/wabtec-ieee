function folder = run_desat_test(p,label,cfg)
% Wabtec slides 5/8: "Desat turn-off <= 10 us". Type-I short circuit (gate turned on into a shorted
% load: bus -> stray inductance -> DUT) with a closed-loop DESAT protection modelled in Simulink:
%   comparator Vce > threshold, enabled only after the blanking time from the gate-on command,
%   latched, removes the gate command. Detector sampled at cfg.sample_s (breaks the algebraic loop).
% All protection settings are ASSUMED (no Wabtec values). The equation-based IGBT is calibrated to
% on-state/threshold data only, so the short-circuit current level is NOT validated: the result shows
% the protection loop timing in the model, not device survival.
if nargin<1, p=testcell.parameters_traction; end
if nargin<2, label='traction'; end
d=struct('threshold_V',9,'blanking_s',7.5e-6,'sample_s',50e-9,'onAt_s',20e-6,'pulse_s',30e-6, ...
 'stop_s',70e-6,'maxStep_s',50e-9,'faultR_Ohm',0,'timeout_s',300,'precharge_s',8e-6,'precharge_from_V',10);
% precharge_s: DC-link ramp 0 -> bus_V from t = 1 us (filtered, tau = precharge_s/8); gate turns on at onAt_s.
% faultR_Ohm: resistance of the short (0 = stray L and its R only). timeout_s: wall-clock limit per sim;
% a run that does not reach stop_s fails with the time reached instead of hanging.
% blanking 7.5 us: the healthy traction double pulse needs > 6.99 us before Vce falls below 9 V
% (firmware simulation on dynamic_20261017_195453_347); 5 us false-trips there.
if nargin>=3, f=fieldnames(cfg); for k=1:numel(f), d.(f{k})=cfg.(f{k}); end, end
cfg=d;
if isfield(p,'desatThreshold_V'), cfg.threshold_V=p.desatThreshold_V; end   % injected driver fault only
if isfield(p,'desatStop_s'), cfg.stop_s=p.desatStop_s; end                  % injected slow-driver fault only
folder=testcell.new_run(['desat_test_' label]);
testcell.write_json(fullfile(folder,'parameters.json'),p); testcell.write_json(fullfile(folder,'desat_config.json'),cfg);
load_system('ee_lib'); load_system('fl_lib'); load_system('nesl_utility');
m='tc_desat'; assert(~bdIsLoaded(m),'Model already open: %s',m); new_system(m);
c=onCleanup(@()close_system(m,0));
solverName='ode23t'; if isfield(p,'dynamicSolver'), solverName=p.dynamicSolver; end
set_param(m,'Solver',solverName,'RelTol',num2str(p.relTol),'AbsTol',num2str(p.absTol), ...
 'MaxStep',num2str(cfg.maxStep_s,17),'StopTime',num2str(cfg.stop_s,17),'ReturnWorkspaceOutputs','on','SaveTime','on');
a=@(src,name,pos,varargin)testcell.add(m,src,name,pos,varargin{:}); w=@(x,y)testcell.wire(m,x,y); P=@testcell.ports;
% --- power circuit: bus -> Ibus sensor -> stray L (short) -> Ic sensor -> DUT -> ground
q=a(sprintf('ee_lib/Semiconductors &\nConverters/N-Channel IGBT'),'IGBT',[590 270 650 350]);
testcell.apply_device(q,p,25); Q=P(q);
g=a('fl_lib/Electrical/Electrical Elements/Electrical Reference','Ground',[610 580 650 610]); G=P(g);
sol=a('nesl_utility/Solver Configuration','Solver',[100 540 210 580]); SO=P(sol); set_param(sol,'DoDC','on'); w(G.LConn,SO.RConn);
w(Q.RConn(2),G.LConn);
% DC link is precharged by a smooth ramp before the test (as a bench charger does). Starting the network in
% the 1800 V DC equilibrium stalled the solver in steady state (desat_test_02.log: stuck at 0.33 us).
bus=a('fl_lib/Electrical/Electrical Sources/Controlled Voltage Source','Bus',[80 90 130 160]); B=P(bus); w(B.RConn(2),G.LConn);
ib=a('fl_lib/Electrical/Electrical Sensors/Current Sensor','IbusSensor',[180 90 220 120]); IB=P(ib); w(B.LConn,IB.LConn);
% The ramp starts from precharge_from_V, not 0: with the DUT held at exactly Vce = 0 the solver stalled at
% 0.21 us (desat_test_03.log); 10/50/100 V starts all ran without warnings and gave identical trip results.
assignin(get_param(m,'ModelWorkspace'),'tcBusRamp',timeseries([cfg.precharge_from_V cfg.precharge_from_V p.bus_V p.bus_V]', ...
 [0 1e-6 1e-6+cfg.precharge_s cfg.stop_s]'));
a('simulink/Sources/From Workspace','BusRamp',[40 20 140 50],'VariableName','tcBusRamp','Interpolate','on','OutputAfterFinalValue','Holding final value');
bps=a(sprintf('nesl_utility/Simulink-PS\nConverter'),'BusPS',[170 20 230 55],'Unit','V'); BPS=P(bps);
set_param(bps,'FilteringAndDerivatives','filter','InputFilterTimeConstant',num2str(cfg.precharge_s/8,17));
add_line(m,'BusRamp/1','BusPS/1'); w(BPS.RConn,B.RConn(1));
vb=a('fl_lib/Electrical/Electrical Sensors/Voltage Sensor','VbusSensor',[130 180 170 230]); VB=P(vb); w(VB.LConn,B.LConn); w(VB.RConn(2),G.LConn);
testcell.log_signal(m,VB.RConn(1),'Vbus','V',[940 310 990 340]);
st=a('fl_lib/Electrical/Electrical Elements/Inductor','ShortCircuitL',[300 90 360 120],'l',num2str(p.strayL_H,17),'r',num2str(p.strayR_Ohm),'g','0'); ST=P(st);
w(IB.RConn(2),ST.LConn);
ic=a('fl_lib/Electrical/Electrical Sensors/Current Sensor','IcSensor',[560 170 610 200]); IC=P(ic); w(IC.RConn(2),Q.RConn(1));
if cfg.faultR_Ohm>0
 fr=a('fl_lib/Electrical/Electrical Elements/Resistor','FaultR',[400 90 450 120],'R',num2str(cfg.faultR_Ohm,17)); FR=P(fr);
 w(ST.RConn,FR.LConn); w(FR.RConn,IC.LConn);
else, w(ST.RConn,IC.LConn);
end
vc=a('fl_lib/Electrical/Electrical Sensors/Voltage Sensor','VceSensor',[770 310 810 365]); VC=P(vc); w(VC.LConn,Q.RConn(1)); w(VC.RConn(2),G.LConn);
vg=a('fl_lib/Electrical/Electrical Sensors/Voltage Sensor','VgeSensor',[460 420 500 470]); VG=P(vg); w(VG.LConn,Q.LConn); w(VG.RConn(2),G.LConn);
testcell.log_signal(m,IC.RConn(1),'Ic','A',[940 90 990 120]);
testcell.log_signal(m,IB.RConn(1),'Ibus','A',[940 145 990 175]);
testcell.log_signal(m,VC.RConn(1),'Vce','V',[940 200 990 230]);
testcell.log_signal(m,VG.RConn(1),'Vge','V',[940 255 990 285]);
% --- gate driver (same as build_rig dynamic branch)
rg=a('fl_lib/Electrical/Electrical Elements/Resistor','GateResistor',[420 290 480 320],'R',num2str(p.RgateExternal_Ohm)); RG=P(rg); w(RG.RConn,Q.LConn);
dr=a(sprintf('ee_lib/Semiconductors &\nConverters/Gate Driver'),'Driver',[280 280 370 350], ...
 'vHigh',num2str(p.gateOn_V),'vLow',num2str(p.gateOff_V),'rHigh',num2str(p.RdriverOn_Ohm),'rLow',num2str(p.RdriverOff_Ohm), ...
 'tHigh',num2str(p.driverDelay_s,17),'tHigh_unit','s','tLow',num2str(p.driverDelay_s,17),'tLow_unit','s'); DR=P(dr);
w(DR.RConn(1),RG.LConn); w(DR.RConn(2),G.LConn);
% --- DESAT protection logic (discrete, sample cfg.sample_s)
Ts=num2str(cfg.sample_s,17); ws=get_param(m,'ModelWorkspace');
tOn=cfg.onAt_s; tOff=cfg.onAt_s+cfg.pulse_s;
assignin(ws,'tcCommand',timeseries([0 1 0 0]',[0 tOn tOff cfg.stop_s]'));
assignin(ws,'tcBlanked',timeseries([0 1 0 0]',[0 tOn+cfg.blanking_s tOff cfg.stop_s]'));
a('simulink/Sources/From Workspace','Command',[40 640 140 670],'VariableName','tcCommand','Interpolate','off','OutputAfterFinalValue','Holding final value','SampleTime',Ts);
a('simulink/Sources/From Workspace','BlankingDone',[40 720 140 750],'VariableName','tcBlanked','Interpolate','off','OutputAfterFinalValue','Holding final value','SampleTime',Ts);
vd=a(sprintf('nesl_utility/PS-Simulink\nConverter'),'VceDesat_PS',[40 800 100 830],'Unit','V'); VD=P(vd); w(VC.RConn(1),VD.LConn(1));
a('simulink/Discrete/Zero-Order Hold','DesatSample',[150 800 190 830],'SampleTime',Ts);
a('simulink/Logic and Bit Operations/Compare To Constant','DesatComparator',[230 800 290 830],'relop','>','const',num2str(cfg.threshold_V));
a('simulink/Logic and Bit Operations/Logical Operator','FaultNow',[340 740 380 800],'Operator','AND','Inputs','2');
a('simulink/Logic and Bit Operations/Logical Operator','LatchOr',[420 740 460 800],'Operator','OR','Inputs','2');
a('simulink/Discrete/Unit Delay','LatchMem',[500 750 540 790],'SampleTime',Ts,'InitialCondition','0');
a('simulink/Logic and Bit Operations/Logical Operator','Inhibit',[580 750 620 790],'Operator','NOT');
a('simulink/Logic and Bit Operations/Logical Operator','GateEnable',[660 640 700 700],'Operator','AND','Inputs','2');
a('simulink/Signal Attributes/Data Type Conversion','CmdDouble',[740 650 790 680],'OutDataTypeStr','double');
a('simulink/Signal Attributes/Data Type Conversion','TripDouble',[660 830 710 860],'OutDataTypeStr','double');
a('simulink/Sinks/To Workspace','Trip_Log',[760 830 860 860],'VariableName','Trip','SaveFormat','Timeseries');
a('simulink/Sinks/To Workspace','Gate_Log',[860 700 960 730],'VariableName','GateCmd','SaveFormat','Timeseries');
ps=a(sprintf('nesl_utility/Simulink-PS\nConverter'),'CommandPS',[830 640 890 680],'Unit','1','FilteringAndDerivatives','zero'); PSb=P(ps);
L=@(x,y)add_line(m,x,y,'autorouting','on');
L('VceDesat_PS/1','DesatSample/1'); L('DesatSample/1','DesatComparator/1');
L('DesatComparator/1','FaultNow/1'); L('BlankingDone/1','FaultNow/2');
L('FaultNow/1','LatchOr/1'); L('LatchOr/1','LatchMem/1'); L('LatchMem/1','LatchOr/2');
% The delayed latch (one detector sample) gates the command: realistic comparator/logic delay, no algebraic loop.
L('LatchMem/1','Inhibit/1'); L('Command/1','GateEnable/1'); L('Inhibit/1','GateEnable/2');
L('GateEnable/1','CmdDouble/1'); L('CmdDouble/1','CommandPS/1'); w(PSb.RConn,DR.LConn);
L('LatchMem/1','TripDouble/1'); L('TripDouble/1','Trip_Log/1'); L('CmdDouble/1','Gate_Log/1');
a('simulink/Signal Attributes/Data Type Conversion','FaultDouble',[420 830 470 860],'OutDataTypeStr','double');
a('simulink/Sinks/To Workspace','Fault_Log',[500 870 600 900],'VariableName','FaultNow','SaveFormat','Timeseries');
L('FaultNow/1','FaultDouble/1'); L('FaultDouble/1','Fault_Log/1');
set_param(m,'SimscapeLogType','none');
save_system(m,fullfile(folder,[m '.slx']));
set_param(m,'SimulationCommand','update'); fprintf('TARGETED COMPILE PASS: %s\n',m);
out=sim(m,'TimeOut',cfg.timeout_s); save(fullfile(folder,'desat_raw.mat'),'out','p','cfg'); reached(out,cfg);
testcell.assert_no_solver_warnings(out);
r=analyze(out,p,cfg);
fine=sim(m,'MaxStep',num2str(cfg.maxStep_s/2,17),'TimeOut',2*cfg.timeout_s);
save(fullfile(folder,'desat_fine_raw.mat'),'fine','p','cfg'); reached(fine,cfg); testcell.assert_no_solver_warnings(fine);
rf=analyze(fine,p,cfg);
assert(abs(r.bus_at_turn_on_V/p.bus_V-1)<1e-3,'DC link not precharged at gate-on: %.6g V',r.bus_at_turn_on_V);
assert(r.tripped==rf.tripped,'Normal and half-step runs disagree on whether DESAT tripped');
if isfield(p,'fault'), r.fault=p.fault; end
if r.tripped
 rel=[abs(r.desat_turnoff_s-rf.desat_turnoff_s)/rf.desat_turnoff_s, abs(r.sc_energy_J-rf.sc_energy_J)/max(abs(rf.sc_energy_J),1e-9)];
else
 % No trip is a valid RESULT (e.g. injected dead-DESAT driver); convergence is checked on the short-circuit energy.
 assert(isfield(p,'fault'),'DESAT never tripped on a device without an injected fault; check threshold/blanking');
 rel=abs(r.sc_energy_J-rf.sc_energy_J)/max(abs(rf.sc_energy_J),1e-9);
end
assert(all(rel<.03),'Turn-off time / short-circuit energy failed 3 percent half-step convergence.');
assert(r.energy_balance_relative_error<.01,'Energy balance residual %.3g exceeds 1 percent',r.energy_balance_relative_error);
r.half_step_relative_errors=rel; r.fine_max_step_s=cfg.maxStep_s/2;
r.config=cfg; r.config_provenance='ASSUMED (threshold, blanking, detector sampling, pulse width); bus/stray/gate from parameter set';
r.scope=['Type-I short circuit (turn-on into short through stray L) with closed-loop DESAT in the model. SIMULATED. ' ...
 'Short-circuit current level NOT validated (equation-based IGBT calibrated on on-state/threshold data only); ' ...
 'demonstrates protection loop timing, not device survival.'];
r.slide_spec='Wabtec slides 5/8: Desat turn-off <= 10 us';
r.datasheet_reference='CM1500HC-66XB tpSC 10 us at VCC <= 2500 V, VGE = 15 V (Tj 150 C); not modelled as a failure limit';
r.hardware_decision='INCONCLUSIVE';
r.status='PASS';  % numerical: no solver warnings, half-step converged, energy balance closed
testcell.write_json(fullfile(folder,'validation.json'),r);
% Portable raw waveform export (analog channels on the solver time base; logic channels held, 'previous').
t=out.Ic.Time; an=@(s)interp1(s.Time,double(s.Data),t); lg=@(s)interp1(s.Time,double(s.Data),t,'previous','extrap');
W=table(t,an(out.Vce),an(out.Ic),an(out.Vge),an(out.Vbus),lg(out.FaultNow),lg(out.GateCmd),lg(out.Trip), ...
 'VariableNames',{'time_s','Vce_V','Ic_A','Vge_V','Vbus_V','FaultNow','GateCmd','Trip'});
writetable(W,fullfile(folder,'desat_waveforms.csv'));
fprintf('DESAT WAVEFORMS: %d samples -> desat_waveforms.csv\n',height(W));
fprintf('DESAT TEST %s: trip %.3f us, turn-off %.3f us after gate-on (slide <= 10 us: %d), peak Ic %.0f A, peak Vce %.0f V, Esc %.3f J, conv %.3g\n', ...
 label,r.trip_after_on_s*1e6,r.desat_turnoff_s*1e6,r.within_slide_10us,r.peak_Ic_A,r.peak_Vce_after_trip_V,r.sc_energy_J,max(rel));
fprintf('DESAT TEST DONE: %s\n',folder);
end

function reached(out,cfg)
tEnd=out.tout(end);
fprintf('SIM REACHED %.6g us of %.6g us\n',tEnd*1e6,cfg.stop_s*1e6);
assert(tEnd>=cfg.stop_s*(1-1e-9),'testcell:Timeout','Simulation stopped at %.6g us (timeout %g s); stop time %.6g us', ...
 tEnd*1e6,cfg.timeout_s,cfg.stop_s*1e6);
end

function r=analyze(out,p,cfg)
t=out.Ic.Time; ic=out.Ic.Data; vce=interp1(out.Vce.Time,out.Vce.Data,t); ib=interp1(out.Ibus.Time,out.Ibus.Data,t);
vbus=interp1(out.Vbus.Time,out.Vbus.Data,t); r.bus_at_turn_on_V=interp1(t,vbus,cfg.onAt_s);
[pk,j]=max(ic); r.peak_Ic_A=pk; r.peak_Ic_time_s=t(j);
Esrc=trapz(t,vbus.*ib); Edev=trapz(t,vce.*ic); Er=trapz(t,(p.strayR_Ohm+cfg.faultR_Ohm)*ib.^2); EL=0.5*p.strayL_H*ib(end)^2;
r.energy_source_J=Esrc; r.energy_device_J=Edev; r.energy_balance_relative_error=abs(Esrc-Edev-Er-EL)/max(abs(Esrc),1e-9);
r.final_Ic_A=ic(end); r.datasheet_VCES_V=3300;
tr=out.Trip.Time; trip=out.Trip.Data; k=find(trip>0.5,1);
r.tripped=~isempty(k);
if ~r.tripped
 % Protection never acted: the short lasts the whole command pulse (only the command edge ends it).
 tOff=cfg.onAt_s+cfg.pulse_s;
 r.trip_time_s=NaN; r.trip_after_on_s=NaN; r.desat_turnoff_s=NaN; r.within_slide_10us=false;
 r.short_duration_without_protection_s=cfg.pulse_s;
 r.Ic_at_command_off_A=interp1(t,ic,tOff);
 r.peak_Vce_after_trip_V=NaN; r.peak_Vce_within_VCES=max(vce)<=3300;
 sc=t>=cfg.onAt_s & t<=t(end); r.sc_energy_J=trapz(t(sc),vce(sc).*ic(sc));
 return
end
tTrip=tr(k);
r.trip_time_s=tTrip; r.trip_after_on_s=tTrip-cfg.onAt_s;
after=find(t>tTrip & ic<0.1*pk,1); assert(~isempty(after),'Collector current did not fall below 10 percent of peak after trip');
r.ic_below_10pct_time_s=t(after);
r.desat_turnoff_s=t(after)-cfg.onAt_s;   % gate-on command (start of short) to Ic < 10 % of peak
r.within_slide_10us=r.desat_turnoff_s<=10e-6;
r.peak_Vce_after_trip_V=max(vce(t>=tTrip));
r.peak_Vce_within_VCES=r.peak_Vce_after_trip_V<=3300;
sc=t>=cfg.onAt_s & t<=t(after); r.sc_energy_J=trapz(t(sc),vce(sc).*ic(sc));
end

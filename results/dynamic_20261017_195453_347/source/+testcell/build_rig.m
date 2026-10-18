function rig = build_rig(kind,p,folder)
% Reusable full-I/V Simscape fixtures. All non-Wabtec values are assumed.
load_system('ee_lib'); load_system('fl_lib'); load_system('nesl_utility');
m=['tc_' kind]; assert(~bdIsLoaded(m),'Model already open: %s',m); new_system(m);
set_param(m,'Solver','ode15s','RelTol',num2str(p.relTol),'AbsTol',num2str(p.absTol), ...
 'MaxStep',num2str(p.dynamicMaxStep_s,17),'StopTime',num2str(p.dynamicStop_s,17), ...
 'ReturnWorkspaceOutputs','on','SaveTime','on');
a=@(src,name,pos,varargin)testcell.add(m,src,name,pos,varargin{:});
w=@(x,y)testcell.wire(m,x,y); ports=@testcell.ports;
coupled=isfield(p,'electrothermal') && p.electrothermal;
if coupled
 q=a(sprintf('nesl_utility/Simscape\nComponent'),'IGBT',[590 270 650 350]);
 simscape.setBlockComponent(q,'ee.semiconductors.n_igbt_thermal');
else
 q=a(sprintf('ee_lib/Semiconductors &\nConverters/N-Channel IGBT'),'IGBT',[590 270 650 350]);
end
testcell.apply_device(q,p,25); Q=ports(q);
if coupled
 assert(numel(Q.LConn)==2 && numel(Q.RConn)==2,'Unexpected thermal component interface.');
 heatPort=Q.LConn(2); Q.LConn=Q.LConn(1);
end
g=a('fl_lib/Electrical/Electrical Elements/Electrical Reference','Ground',[610 580 650 610]); G=ports(g);
solver=a('nesl_utility/Solver Configuration','Solver',[100 540 210 580]); S=ports(solver); set_param(solver,'DoDC','on'); w(G.LConn,S.RConn);
w(Q.RConn(2),G.LConn);
ic=a('fl_lib/Electrical/Electrical Sensors/Current Sensor','IcSensor',[560 170 610 200]); IC=ports(ic); w(IC.RConn(2),Q.RConn(1));
vg=a('fl_lib/Electrical/Electrical Sensors/Voltage Sensor','VgeSensor',[460 420 500 470]); VG=ports(vg); w(VG.LConn,Q.LConn); w(VG.RConn(2),G.LConn);
vc=a('fl_lib/Electrical/Electrical Sensors/Voltage Sensor','VceSensor',[770 310 810 365]); VC=ports(vc); w(VC.LConn,Q.RConn(1)); w(VC.RConn(2),G.LConn);
measure=[ic vg vc];
measure=[measure testcell.log_signal(m,IC.RConn(1),'Ic','A',[940 90 990 120])];
measure=[measure testcell.log_signal(m,VG.RConn(1),'Vge','V',[940 145 990 175])];
measure=[measure testcell.log_signal(m,VC.RConn(1),'Vce','V',[940 200 990 230])];
rg=a('fl_lib/Electrical/Electrical Elements/Resistor','GateResistor',[420 290 480 320],'R',num2str(p.RgateExternal_Ohm)); RG=ports(rg);
ig=a('fl_lib/Electrical/Electrical Sensors/Current Sensor','IgSensor',[500 290 540 320]); IG=ports(ig);
w(RG.RConn,IG.LConn); w(IG.RConn(2),Q.LConn);
measure=[measure ig testcell.log_signal(m,IG.RConn(1),'Ig','A',[940 255 990 285])];
ws=get_param(m,'ModelWorkspace'); loadBlocks=[]; supplyBlocks=[]; gateBlocks=rg;
if startsWith(kind,'static')
 gs=a('fl_lib/Electrical/Electrical Sources/DC Voltage Source','GateSupply',[300 280 340 350],'v0',num2str(p.gateOn_V)); GS=ports(gs);
 w(GS.LConn,RG.LConn); w(GS.RConn,G.LConn); gateBlocks=[gateBlocks gs];
 if strcmp(kind,'static_i'), type='Controlled Current Source'; unit='A'; else, type='Controlled Voltage Source'; unit='V'; end
 src=a(['fl_lib/Electrical/Electrical Sources/' type],'ForceSource',[130 100 180 165]); F=ports(src);
 % Controlled current source injects from bottom (reference) to top.
  if strcmp(kind,'static_v')
  ballast=a('fl_lib/Electrical/Electrical Elements/Resistor','FixtureResistance',[300 110 350 140],'R','0.1'); BA=ports(ballast);
  w(F.LConn,BA.LConn); w(BA.RConn,IC.LConn); supplyBlocks=ballast;
 else, w(F.LConn,IC.LConn);
 end
 w(F.RConn(2),G.LConn);
 sw=a('simulink/Sources/From Workspace','Sweep',[40 210 140 240],'VariableName','tcSweep','Interpolate','off','OutputAfterFinalValue','Holding final value');
 ps=a(sprintf('nesl_utility/Simulink-PS\nConverter'),'SweepPS',[170 210 230 245],'Unit',unit,'FilteringAndDerivatives','zero'); PS=ports(ps);
 set_param(ps,'FilteringAndDerivatives','filter','InputFilterTimeConstant','1e-6');
 add_line(m,'Sweep/1','SweepPS/1'); w(PS.RConn,F.RConn(1));
 assignin(ws,'tcSweep',timeseries([1;1],[0;p.dynamicStop_s])); supplyBlocks=[supplyBlocks src sw ps];
else
 % Default ode23t (validated 48 V runs). A parameter set may request another stiff solver (traction: ode15s).
 if isfield(p,'dynamicSolver'), set_param(m,'Solver',p.dynamicSolver); else, set_param(m,'Solver','ode23t'); end
 src=a('fl_lib/Electrical/Electrical Sources/DC Voltage Source','Bus',[80 90 130 160],'v0',num2str(p.bus_V)); B=ports(src); w(B.RConn,G.LConn);
 ib=a('fl_lib/Electrical/Electrical Sensors/Current Sensor','IbusSensor',[180 90 220 120]); IB=ports(ib); w(B.LConn,IB.LConn);
 il=a('fl_lib/Electrical/Electrical Sensors/Current Sensor','ILSensor',[320 90 360 120]); IL=ports(il); w(IB.RConn(2),IL.LConn);
 r=a('fl_lib/Electrical/Electrical Elements/Resistor','LoadR',[390 90 440 120],'R',num2str(p.loadR_Ohm)); R=ports(r); w(IL.RConn(2),R.LConn);
 if strcmp(kind,'dynamic_rl')
  l=a('fl_lib/Electrical/Electrical Elements/Inductor','LoadL',[470 90 520 120],'l',num2str(p.loadL_H,17),'r','0','g','0'); L=ports(l); w(R.RConn,L.LConn); switchNode=L.RConn; loadBlocks=[r l];
 else, switchNode=R.RConn; loadBlocks=r;
 end
 stray=a('fl_lib/Electrical/Electrical Elements/Inductor','CommutationL',[550 90 610 120],'l',num2str(p.strayL_H,17),'r',num2str(p.strayR_Ohm),'g','0'); ST=ports(stray); w(switchNode,ST.LConn); w(ST.RConn,IC.LConn); loadBlocks=[loadBlocks stray];
 diode=a(sprintf('ee_lib/Semiconductors &\nConverters/Diode'),'FreewheelDiode',[710 90 760 120], ...
  'Vf',num2str(p.diodeVf_V),'Ron',num2str(p.diodeRon_Ohm),'Goff',num2str(p.diodeGoff_S,17)); D=ports(diode);
 id=a('fl_lib/Electrical/Electrical Sensors/Current Sensor','IdSensor',[650 90 690 120]); ID=ports(id);
 w(switchNode,ID.LConn); w(ID.RConn(2),D.LConn); w(D.RConn,IL.LConn);
  vs=a('fl_lib/Electrical/Electrical Sensors/Voltage Sensor','VswitchSensor',[810 90 850 150]); VS=ports(vs);
 w(VS.LConn,switchNode); w(VS.RConn(2),G.LConn);
 measure=[measure vs testcell.log_signal(m,VS.RConn(1),'Vswitch','V',[940 475 990 505])];
 % Explicit diode junction capacitance; ideal conduction has no reverse recovery.
 cap=a('fl_lib/Electrical/Electrical Elements/Capacitor','DiodeC',[710 170 760 200],'c',num2str(p.diodeC_F,17)); CAP=ports(cap); w(CAP.LConn,D.LConn); w(CAP.RConn,D.RConn);
 % Sensor branch includes displacement and conductive diode current.
 measure=[measure ib il id];
 measure=[measure testcell.log_signal(m,IB.RConn(1),'Ibus','A',[940 310 990 340])];
 measure=[measure testcell.log_signal(m,IL.RConn(1),'IL','A',[940 365 990 395])];
 measure=[measure testcell.log_signal(m,ID.RConn(1),'Id','A',[940 420 990 450])];
 loadBlocks=[loadBlocks diode cap]; supplyBlocks=src;
 driver=a(sprintf('ee_lib/Semiconductors &\nConverters/Gate Driver'),'Driver',[280 280 370 350], ...
  'vHigh',num2str(p.gateOn_V),'vLow',num2str(p.gateOff_V), ...
  'rHigh',num2str(p.RdriverOn_Ohm),'rLow',num2str(p.RdriverOff_Ohm), ...
  'tHigh',num2str(p.driverDelay_s,17),'tHigh_unit','s','tLow',num2str(p.driverDelay_s,17),'tLow_unit','s'); DR=ports(driver);
 w(DR.RConn(1),RG.LConn); w(DR.RConn(2),G.LConn);
 cmd=a('simulink/Sources/From Workspace','Command',[50 290 150 320],'VariableName','tcCommand','Interpolate','off','OutputAfterFinalValue','Holding final value');
 ps=a(sprintf('nesl_utility/Simulink-PS\nConverter'),'CommandPS',[170 285 230 325],'Unit','1','FilteringAndDerivatives','zero'); PS=ports(ps);
 add_line(m,'Command/1','CommandPS/1'); w(PS.RConn,DR.LConn);
 times=[0 p.pulseEdges_s p.dynamicStop_s];
 assignin(ws,'tcCommand',timeseries([0 1 0 1 0 0]',times'));
 gateBlocks=[gateBlocks driver cmd ps];
end
if coupled
 net=testcell.thermal_network(m,p.thermal);
 % Start the electrical/thermal model in the solved OFF equilibrium.
 for b=net.masses, set_param(b,'T_specify','off'); end
 hs=a('fl_lib/Thermal/Thermal Sensors/Heat Flow Rate Sensor','DeviceHeatSensor',[650 530 700 560]); HS=ports(hs);
 w(heatPort,HS.LConn); w(HS.RConn(2),net.junction);
 thermalBlocks=[net.blocks hs testcell.log_signal(m,HS.RConn(1),'DeviceHeat','W',[940 850 990 880])];
 Simulink.BlockDiagram.createSubsystem(thermalBlocks,'Name','ThermalPlant');
end
% Physical connections are preserved as subsystem Connection Ports.
Simulink.BlockDiagram.createSubsystem(q,'Name','DUT');
Simulink.BlockDiagram.createSubsystem(gateBlocks,'Name','GateDrive');
if ~isempty(loadBlocks), Simulink.BlockDiagram.createSubsystem(loadBlocks,'Name','LoadBank'); end
Simulink.BlockDiagram.createSubsystem(supplyBlocks,'Name','Supply');
Simulink.BlockDiagram.createSubsystem(measure,'Name','Measurements');
set_param(m,'SimscapeLogType','all');
rig.model=m; rig.device=[m '/DUT/IGBT']; rig.gate=[m '/GateDrive/GateSupply']; rig.kind=kind;
rig.file=fullfile(folder,[m '.slx']);
save_system(m,rig.file);
end








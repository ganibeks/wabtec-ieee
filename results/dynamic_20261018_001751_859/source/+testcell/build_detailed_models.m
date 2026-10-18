function folder = build_detailed_models(folder,stage)
% Detailed, executable SLX sheets based on preserved electrical experiments.
% Expand project wrappers, preserve the physical network, add passive instruments.
root=fileparts(fileparts(mfilename('fullpath')));
if nargin<1, folder=testcell.new_run('detailed_simulink'); end
assert(isfolder(folder));
source=fullfile(root,'results','dynamic_20261017_195453_347');
if nargin>1
 if strcmp(stage,'polish'), polish_outputs(folder); return; end
 assert(strcmp(stage,'finish'),'Resume either finish or polish stage.');
 finish_exports(folder,source,root); return;
end
p=jsondecode(fileread(fullfile(source,'parameters.json')));
p.pulseEdges_s=p.pulseEdges_s(:)';
testcell.write_json(fullfile(folder,'parameters.json'),p);
m='tc_dynamic_rl'; assert(~bdIsLoaded(m),'Source model is already loaded.');
load_system(fullfile(source,[m '.slx'])); modelHandle=get_param(m,'Handle');
cleanup=onCleanup(@()close_system(modelHandle,0)); %#ok<NASGU>
for name={'DUT','GateDrive','LoadBank','Supply','Measurements'}
 Simulink.BlockDiagram.expandSubsystem([m '/' name{1}]);
end
clean_notes(m);
style_blocks(m);
% Actual controller schedule, made explicit as four steps rather than hidden
% From Workspace data. The resulting command is exactly 0/1/0/1/0.
commandLines=get_param([m '/CommandPS'],'LineHandles');
delete_line(commandLines.Inport);
delete_block([m '/Command']);
add_block('simulink/Math Operations/Sum',[m '/Command'],'Inputs','++++', ...
 'Position',[390 1240 435 1410]);
for k=1:4
 name=sprintf('Pulse_edge_%d',k); y=1160+90*(k-1);
 add_block('simulink/Sources/Step',[m '/' name], ...
  'Time',num2str(p.pulseEdges_s(k),17),'Before','0','After',num2str((-1)^(k+1)), ...
  'Position',[130 y 245 y+45]);
 add_line(m,[name '/1'],sprintf('Command/%d',k),'autorouting','on');
 note(m,sprintf('%s at %.0f us',onoff(k),p.pulseEdges_s(k)*1e6),[80 y-35],11);
end
add_line(m,'Command/1','CommandPS/1','autorouting','on');
% Power schematic. Coordinates are intentional; no automatic layout of the
% library internals or regrouping that would hide sensors is performed.
put(m,'Bus',[180 400 240 515],'down');
put(m,'IbusSensor',[420 350 485 395],'right');
put(m,'ILSensor',[650 350 715 395],'right');
put(m,'LoadR',[800 350 900 395],'right');
put(m,'LoadL',[1010 350 1120 395],'right');
put(m,'FreewheelDiode',[920 190 1020 235],'left');
put(m,'IdSensor',[1150 190 1215 235],'left');
put(m,'DiodeC',[920 270 1020 305],'right');
put(m,'CommutationL',[1300 440 1355 525],'down');
put(m,'IcSensor',[1300 600 1355 650],'down');
put(m,'IGBT',[1250 770 1380 895],'right');
put(m,'Driver',[690 760 835 865],'right');
put(m,'GateResistor',[925 790 1000 830],'right');
put(m,'IgSensor',[1080 790 1140 830],'right');
put(m,'VgeSensor',[1080 925 1130 995],'down');
put(m,'VceSensor',[1510 795 1565 875],'down');
put(m,'VswitchSensor',[1510 460 1565 540],'down');
put(m,'Ground',[1340 1080 1380 1120],'right');
put(m,'Solver',[180 870 350 940],'right');
put(m,'CommandPS',[510 1250 585 1295],'right');
% Eight fully visible physical-to-Simulink measurement chains, logs and meters.
names={'Vge','Vce','Ic','Ig','IL','Id','Ibus','Vswitch'};
units={'V','V','A','A','A','A','A','V'};
for k=1:numel(names)
 n=names{k}; y=210+(k-1)*100;
 put(m,[n '_PS'],[1880 y 1960 y+40],'right');
 put(m,[n '_Log'],[2240 y 2380 y+40],'right');
 add_block('simulink/Signal Routing/Goto',[m '/TAG_' n], ...
  'GotoTag',['DETAIL_' n],'TagVisibility','local','Position',[2040 y+48 2160 y+78]);
 add_line(m,[n '_PS/1'],['TAG_' n '/1'],'autorouting','on');
 add_block('simulink/Sinks/Display',[m '/METER_' n],'Position',[2480 y 2610 y+40]);
 add_line(m,[n '_PS/1'],['METER_' n '/1'],'autorouting','on');
 set_param([m '/' n '_PS'],'BackgroundColor','[0.90 0.95 1.00]');
 note(m,sprintf('%s [%s]  |  physical sensor -> ideal converter -> raw log',n,units{k}),[1860 y-32],10);
end
% Passive real-time monitors. These do not feed control or the electrical plant.
scope(m,'Gate_waveforms',{'Vge','Ig'},[470 1510 660 1590]);
scope(m,'Switching_waveforms',{'Vce','Ic','IL'},[930 1510 1120 1610]);
scope(m,'Freewheel_waveforms',{'Id','Vswitch','Ibus'},[1400 1510 1590 1610]);
add_block('simulink/Math Operations/Product',[m '/Collector_terminal_power'],'Inputs','**', ...
 'Position',[2050 1220 2110 1275]);
from(m,'Vce','Power_Vce',[1850 1200 1960 1235]);
from(m,'Ic','Power_Ic',[1850 1270 1960 1305]);
add_line(m,'Power_Vce/1','Collector_terminal_power/1','autorouting','on');
add_line(m,'Power_Ic/1','Collector_terminal_power/2','autorouting','on');
add_block('simulink/Continuous/Integrator',[m '/Collector_terminal_energy'], ...
 'InitialCondition','0','Position',[2200 1230 2260 1280]);
add_line(m,'Collector_terminal_power/1','Collector_terminal_energy/1','autorouting','on');
add_block('simulink/Sinks/To Workspace',[m '/Terminal_energy_log'], ...
 'VariableName','CollectorTerminalEnergy','SaveFormat','Timeseries','Position',[2390 1230 2580 1280]);
add_line(m,'Collector_terminal_energy/1','Terminal_energy_log/1','autorouting','on');
add_block('simulink/Math Operations/Sum',[m '/KCL_residual'],'Inputs','+--', ...
 'Position',[2200 1440 2250 1545]);
for k=1:3
 labels={'IL','Ic','Id'}; name=['KCL_' labels{k}];
 from(m,labels{k},name,[1880 1400+70*k 2000 1435+70*k]);
 add_line(m,[name '/1'],sprintf('KCL_residual/%d',k),'autorouting','on');
end
add_block('simulink/Sinks/To Workspace',[m '/KCL_log'],'VariableName','KCLResidual', ...
 'SaveFormat','Timeseries','Position',[2400 1460 2580 1505]);
add_line(m,'KCL_residual/1','KCL_log/1','autorouting','on');
note(m,'IGBT TEST CELL | DETAILED ELECTRICAL SCHEMATIC',[70 20],24);
note(m,'Executable RL double-pulse test. Expanded physical components, explicit pulse sequence, eight measurement channels and passive numerical monitors.',[70 75],12);
note(m,'01  DC SUPPLY / SOLVER',[70 150],16);
note(m,'02  POWER PATH + FREEWHEEL BRANCH',[650 120],16);
note(m,'03  GATE DRIVER + DEVICE UNDER TEST',[650 660],16);
note(m,'04  TEST SEQUENCE / VIRTUAL CONTROLLER',[70 1090],16);
note(m,'05  MEASUREMENT / ACQUISITION',[1860 135],16);
note(m,'06  SCOPES / TERMINAL ENERGY / KCL',[1830 1090],16);
note(m,sprintf('DC bus = %g V\nIdeal source; not a charger or finite DC link',p.bus_V),[70 575],11);
note(m,sprintf('Rload = %.4g ohm (ASSUMED)',p.loadR_Ohm),[760 460],11);
note(m,sprintf('Lload = %.4g uH (ASSUMED)',p.loadL_H*1e6),[990 460],11);
note(m,sprintf('Lstray = %.4g nH\nRstray = %.4g mOhm',p.strayL_H*1e9,p.strayR_Ohm*1e3),[1390 570],11);
note(m,sprintf('Cdiode = %.4g nF (ASSUMED)\nDiode: Vf %.3g V + Ron %.4g ohm; NO reverse recovery', ...
 p.diodeC_F*1e9,p.diodeVf_V,p.diodeRon_Ohm),[710 500],11);
note(m,sprintf('VON = +%g V / VOFF = %g V\nRon / Roff = %g / %g ohm\nPropagation delay = %g ns (ASSUMED)', ...
 p.gateOn_V,p.gateOff_V,p.RdriverOn_Ohm,p.RdriverOff_Ohm,p.driverDelay_s*1e9),[620 920],11);
note(m,sprintf('External Rg = %g ohm\nInternal Rg = %g ohm (ASSUMED)',p.RgateExternal_Ohm,p.RgInternal_Ohm),[880 1045],11);
note(m,sprintf('Representative CM1500HC-66XB; NOT identified Wabtec module\nEquation-based full I-V and charge model; fixed 25 degC\nVth input %.3g V; calibration Vce %.3g V at %.4g A / %.3g degC\nCies / Cres / Coes = %.4g / %.4g / %.4g nF\nTransit time %.4g us (ASSUMED); dynamic calibration remains incomplete', ...
 p.Vth_V,p.VceCalibration_V,p.IcCalibration_A,p.Tcal_C,p.Cies_F*1e9,p.Cres_F*1e9,p.Coes_F*1e9,p.transit_s*1e6),[650 1730],11);
note(m,'ON-1: 50..300 us | OFF: 300..400 us | ON-2: 400..500 us\nActual command edges above; driver includes propagation delay.\nOpen scopes after Run to inspect simulated signals.',[70 1620],11);
note(m,'Integral of Vce*Ic is collector TERMINAL energy.\nIt includes conduction and reactive transfer; not calibrated pure Eon/Eoff.',[1830 1330],10);
note(m,'KCL = IL - Ic - Id. Ideal sensor model; no ADC quantisation or noise.\nAuxiliary AC/DC, 24 V supply, optical isolation, CAN/USB and interlocks\nare not represented as hardware in this fixture. Hardware decision: INCONCLUSIVE.',[1830 1700],11);
finish_layout(m);
target='igbt_test_cell_detailed'; file=fullfile(folder,[target '.slx']);
assert(~isfile(file)); save_system(m,file); m=get_param(modelHandle,'Name');
set_param(m,'SimulationCommand','update'); fprintf('DETAILED RL COMPILE PASS\n');
initial=Simulink.SimulationInput(m); initial=initial.setModelParameter('StopTime','2e-6');
probe=sim(initial); testcell.assert_no_solver_warnings(probe);
assert(all(isfinite(probe.Ic.Data)) && all(isfinite(probe.Vce.Data)));
fprintf('DETAILED RL INITIALIZATION PASS\n');
out=sim(m,'TimeOut',180); testcell.assert_no_solver_warnings(out);
save(fullfile(folder,'detailed_rl_raw.mat'),'out','p');
r=testcell.analyze_dynamic(out,p,'dynamic_rl');
reference=jsondecode(fileread(fullfile(source,'dynamic_rl_validation.json')));
fields={'peak_Vce_V','peak_Ic_A','bus_energy_J'};
for k=1:numel(fields)
 key=fields{k}; rel=abs(r.(key)-reference.(key))/max(abs(reference.(key)),1e-9);
 assert(rel<.005,'Detailed sheet differs from saved fixture by more than 0.5 percent: %s',key);
 r.reference_relative_errors.(key)=rel;
end
fine=sim(m,'MaxStep',num2str(p.dynamicMaxStep_s/2,17),'TimeOut',180);
testcell.assert_no_solver_warnings(fine); save(fullfile(folder,'detailed_rl_fine_raw.mat'),'fine','p');
rf=testcell.analyze_dynamic(fine,p,'dynamic_rl');
ec=[r.events.gross_collector_terminal_energy_J]; ef=[rf.events.gross_collector_terminal_energy_J];
rel=abs(ec-ef)./max(abs(ef),1e-7); assert(all(rel<.03),'Half-step convergence failed.');
r.half_step_event_energy_relative_errors=rel;
% Cross-check the visible integrator against numerical quadrature of sensor data.
last=out.CollectorTerminalEnergy.Data(end);
r.passive_integrator_energy_J=last;
assert(abs(last-r.dut_collector_terminal_energy_J)/max(abs(last),1e-9)<.005,'Visible energy monitor disagrees with terminal integral.');
testcell.write_json(fullfile(folder,'rl_validation.json'),r);
fprintf('DETAILED RL FULL RUN PASS: peak Vce %.6g V, peak Ic %.6g A\n',r.peak_Vce_V,r.peak_Ic_A);
clear cleanup;
finish_exports(folder,source,root);
end

function finish_exports(folder,source,root)
% Resume presentation exports without repeating already successful physics runs.
file=fullfile(folder,'igbt_test_cell_detailed.slx');
validated=jsondecode(fileread(fullfile(folder,'rl_validation.json')));
assert(strcmp(validated.status,'PASS'));
data=load(fullfile(folder,'detailed_rl_raw.mat'),'out','p');
p=data.p; p.pulseEdges_s=p.pulseEdges_s(:)';
plots=fullfile(folder,'waveforms'); assert(~isfolder(plots),'Preserve existing waveform exports.'); mkdir(plots);
testcell.plot_dynamic(data.out,p,'dynamic_rl',plots);
load_system(file); m='igbt_test_cell_detailed'; h=get_param(m,'Handle');
cleanup=onCleanup(@()close_system(h,0));
set_param(m,'SimulationCommand','update');
print(['-s' m],'-dpng','-r180',fullfile(folder,'detailed_rl_diagram.png'));
print(['-s' m],'-dpdf',fullfile(folder,'detailed_rl_diagram.pdf'));
clear cleanup;
% Protection is a separate physical experiment, preserving its own test circuit.
desatSource=fullfile(root,'results','desat_test_traction_20261017_212553_145');
desatFile=build_desat_sheet(desatSource,folder);
manifest=struct('status','PASS','scope','Detailed executable electrical diagrams; RL re-simulated; DESAT layout compiled and initialized only', ...
 'rl_model',file,'desat_model',desatFile,'rl_source',source,'desat_source',desatSource, ...
 'hardware_decision','INCONCLUSIVE');
testcell.write_json(fullfile(folder,'validation.json'),manifest);
polish_outputs(folder);
fprintf('DETAILED_MODELS_FOLDER=%s\n',folder);
end

function polish_outputs(folder)
% Separate cosmetic copies: preserve the numerically checked intermediate SLX.
targetFolder=fullfile(folder,'final'); assert(~isfolder(targetFolder)); mkdir(targetFolder);
old={'igbt_test_cell_detailed','igbt_desat_detailed'};
new={'wabtec_igbt_test_cell','wabtec_igbt_desat_test'};
checks=struct;
for k=1:2
 load_system(fullfile(folder,[old{k} '.slx'])); m=old{k}; h=get_param(m,'Handle');
 cleanup=onCleanup(@()close_system(h,0));
 clean_notes(m);
 if k==1
  annotations=find_system(m,'FindAll','on','Type','annotation');
  for ah=annotations'
   a=get_param(ah,'Object');
   if startsWith(a.Text,'Rload ='), a.Position=[760 460]; end
   if startsWith(a.Text,'Lload ='), a.Position=[990 460]; end
  end
 end
 finish_layout(m);
file=fullfile(targetFolder,[new{k} '.slx']); save_system(m,file); m=get_param(h,'Name');
 set_param(m,'SimulationCommand','update');
 in=Simulink.SimulationInput(m); in=in.setModelParameter('StopTime','2e-6');
 out=sim(in); testcell.assert_no_solver_warnings(out);
 assert(all(isfinite(out.Ic.Data)) && out.tout(end)>=2e-6*(1-1e-9));
 print(['-s' m],'-dpng','-r180',fullfile(targetFolder,[new{k} '.png']));
 print(['-s' m],'-dpdf',fullfile(targetFolder,[new{k} '.pdf']));
 checks.(new{k})=struct('compile','PASS','initialization','PASS','initialization_duration_s',2e-6);
 fprintf('FINAL DETAILED SHEET PASS: %s\n',new{k});
 clear cleanup;
end
record=struct('status','PASS','scope','Cosmetic final copies: compiled and initialized; full RL numerical evidence in parent rl_validation.json', ...
 'hardware_decision','INCONCLUSIVE','checks',checks);
testcell.write_json(fullfile(targetFolder,'layout_validation.json'),record);
end

function clean_notes(m)
annotations=find_system(m,'FindAll','on','Type','annotation');
for ah=annotations'
 a=get_param(ah,'Object');
 if any(strcmp(a.Text,{'DUT','GateDrive','LoadBank','Supply','Measurements'}))
  delete(a);
 else
  a.Text=strrep(a.Text,'\n',newline);
 end
end
end

function file=build_desat_sheet(source,folder)
m='tc_desat'; assert(~bdIsLoaded(m)); load_system(fullfile(source,[m '.slx']));
h=get_param(m,'Handle'); cleanup=onCleanup(@()close_system(h,0)); %#ok<NASGU>
cfg=jsondecode(fileread(fullfile(source,'desat_config.json')));
testcell.write_json(fullfile(folder,'desat_config.json'),cfg);
style_blocks(m);
% Same saved short-circuit and sampled comparator/latch circuit, with readable wiring.
layout={ 'BusRamp',[70 210 220 255];'BusPS',[320 210 410 255];'Bus',[420 390 480 480]; ...
 'IbusSensor',[670 280 740 325];'ShortCircuitL',[900 280 1000 330]; ...
 'IcSensor',[1210 360 1270 410];'IGBT',[1210 590 1330 715]; ...
 'VbusSensor',[540 480 590 555];'VceSensor',[1470 580 1525 660]; ...
 'VgeSensor',[1030 755 1085 825];'Driver',[740 585 865 685]; ...
 'GateResistor',[980 610 1050 650];'Ground',[1310 850 1350 895]; ...
 'Solver',[200 780 380 850];'Command',[80 1060 230 1105];'BlankingDone',[80 1260 230 1305]; ...
 'VceDesat_PS',[70 1420 170 1465];'DesatSample',[280 1420 375 1465]; ...
 'DesatComparator',[500 1420 650 1470];'FaultNow',[790 1290 860 1370]; ...
 'LatchOr',[1000 1290 1070 1370];'LatchMem',[1200 1300 1300 1360]; ...
 'Inhibit',[1450 1190 1520 1240];'GateEnable',[1650 1050 1720 1130]; ...
 'CmdDouble',[1830 1070 1930 1115];'CommandPS',[2010 1070 2100 1115]; ...
 'TripDouble',[1450 1440 1530 1485];'Trip_Log',[1660 1440 1820 1485]; ...
 'Gate_Log',[2010 1190 2170 1235]};
for k=1:size(layout,1), put(m,layout{k,1},layout{k,2},'right'); end
channels={'Vbus','Vge','Vce','Ic','Ibus'};
for k=1:numel(channels)
 n=channels{k}; y=240+120*(k-1);
 put(m,[n '_PS'],[1890 y 1980 y+40],'right');
 put(m,[n '_Log'],[2190 y 2350 y+40],'right');
end
note(m,'IGBT TEST CELL | CLOSED-LOOP DESAT SCHEMATIC',[70 20],24);
note(m,'Separate Type-I short-circuit experiment: precharged supply -> stray impedance -> DUT. Protection feeds back into the actual gate command.',[70 75],12);
note(m,'01  PRECHARGE / SHORT-CIRCUIT POWER PATH',[70 140],16);
note(m,'02  PHYSICAL GATE DRIVER / DUT / SENSORS',[740 490],16);
note(m,'03  IDEAL ACQUISITION / RAW LOGS',[1850 140],16);
note(m,'04  COMMAND / BLANKING / COMPARATOR / LATCH / INHIBIT',[70 970],16);
note(m,sprintf('Source ramp: %.3g V -> 1800 V\nRamp duration %.3g us; filter tau %.3g us\nGate command: %.3g..%.3g us',cfg.precharge_from_V,cfg.precharge_s*1e6,cfg.precharge_s/8*1e6,cfg.onAt_s*1e6,(cfg.onAt_s+cfg.pulse_s)*1e6),[70 575],11);
note(m,sprintf('DESAT threshold = %.3g V\nBlanking = %.3g us\nDetector sample / latch delay = %.3g ns\nAll protection settings ASSUMED',cfg.threshold_V,cfg.blanking_s*1e6,cfg.sample_s*1e9),[70 1580],12);
note(m,'FaultNow = (Vce > threshold) AND BlankingDone\nLatchOr + Unit Delay hold the trip until reset / new simulation.\nGateEnable = Command AND NOT(LatchMem); feeds the physical driver.',[800 1580],12);
note(m,'Fault onset, detector latch, gate-disable command and current clearance are different times.\nShort-circuit current level and device survival are NOT validated. No avalanche model.\nThe 10 us reference is not replaced by the blanking setting. Hardware decision: INCONCLUSIVE.',[70 1730],12);
finish_layout(m);
file=fullfile(folder,'igbt_desat_detailed.slx'); assert(~isfile(file)); save_system(m,file); m=get_param(h,'Name');
set_param(m,'SimulationCommand','update');
in=Simulink.SimulationInput(m); in=in.setModelParameter('StopTime','2e-6');
out=sim(in); testcell.assert_no_solver_warnings(out);
assert(all(isfinite(out.Ic.Data)) && out.tout(end)>=2e-6*(1-1e-9));
print(['-s' m],'-dpng','-r180',fullfile(folder,'detailed_desat_diagram.png'));
print(['-s' m],'-dpdf',fullfile(folder,'detailed_desat_diagram.pdf'));
fprintf('DETAILED DESAT COMPILE / INITIALIZATION PASS (full protection run not repeated)\n');
end

function style_blocks(m)
blocks=find_system(m,'SearchDepth',1,'Type','Block');
for k=1:numel(blocks)
 set_param(blocks{k},'FontName','Arial','FontSize','11','ForegroundColor','black');
end
end
function put(m,name,pos,orientation)
set_param([m '/' name],'Position',pos,'Orientation',orientation);
end
function note(m,content,position,size)
a=Simulink.Annotation(m,strrep(content,'\n',newline)); a.FontName='Arial'; a.FontSize=size;
a.Position=position;
end
function from(m,tag,name,pos)
add_block('simulink/Signal Routing/From',[m '/' name],'GotoTag',['DETAIL_' tag],'Position',pos);
end
function scope(m,name,signals,pos)
add_block('simulink/Sinks/Scope',[m '/' name],'NumInputPorts',num2str(numel(signals)),'Position',pos);
for k=1:numel(signals)
 n=sprintf('%s_input_%d',name,k); y=pos(2)-10+45*(k-1);
 from(m,signals{k},n,[pos(1)-190 y pos(1)-70 y+28]);
 add_line(m,[n '/1'],sprintf('%s/%d',name,k),'autorouting','on');
end
end
function finish_layout(m)
lines=find_system(m,'FindAll','on','SearchDepth',1,'Type','line');
lines=lines(arrayfun(@(h)get_param(h,'LineParent')==-1,lines));
for k=1:numel(lines), Simulink.BlockDiagram.routeLine(lines(k)); end
set_param(m,'ZoomFactor','FitSystem','PaperOrientation','landscape','PaperPositionMode','auto');
end
function s=onoff(k)
if mod(k,2), s='ON'; else, s='OFF'; end
end

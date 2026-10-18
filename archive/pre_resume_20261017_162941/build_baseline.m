function build_baseline
% All electrical values are illustrative; no hardware ratings are claimed.
root=fileparts(mfilename('fullpath')); cd(root);
load_system('ee_lib'); load_system('fl_lib'); load_system('nesl_utility');
m='igbt_baseline'; if bdIsLoaded(m), close_system(m,0); end
new_system(m);
set_param(m,'Solver','ode23t','StopTime','0.006','MaxStep','2e-6', ...
 'RelTol','1e-6','AbsTol','1e-8','ReturnWorkspaceOutputs','on');
A=@(src,name,pos)add_block(src,[m '/' name],'Position',pos);
q=A(sprintf('ee_lib/Semiconductors &\nConverters/IGBT\n(Ideal,\nSwitching)'), 'IGBT_illustrative',[540 210 610 290]);
set_param(q,'port_option','ee.enum.controlport.elec','Vf','0.8','Ron','0.1','Goff','1e-8','Vth','6');
d=A(sprintf('ee_lib/Semiconductors &\nConverters/Gate Driver'),'Gate_Driver',[330 230 420 300]);
fid=fopen('driver_interface.txt','w');
n=get_param(d,'MaskNames'); v=get_param(d,'MaskValues'); p=get_param(d,'MaskPrompts');
for k=1:numel(n), fprintf(fid,'%s = %s | %s\n',n{k},v{k},p{k}); end
fprintf(fid,'%s\n',get_param(d,'MaskDisplay')); fclose(fid);
% Select output voltages by mask prompt to tolerate release-specific names.
set_param(d,'vHigh','15','vLow','-15');

s=A('fl_lib/Electrical/Electrical Sources/DC Voltage Source','Supply_12V_illustrative',[130 90 180 150]); set_param(s,'v0','12');
r=A('fl_lib/Electrical/Electrical Elements/Resistor','Load_100Ohm_illustrative',[280 85 350 125]); set_param(r,'R','100');
i=A('fl_lib/Electrical/Electrical Sensors/Current Sensor','Collector_Current',[440 85 490 125]);
vce=A('fl_lib/Electrical/Electrical Sensors/Voltage Sensor','Vce_Sensor',[700 180 740 240]);
vge=A('fl_lib/Electrical/Electrical Sensors/Voltage Sensor','Vge_Sensor',[450 350 490 410]);
g=A('fl_lib/Electrical/Electrical Elements/Electrical Reference','Reference',[560 460 600 490]);
sol=A('nesl_utility/Solver Configuration','Solver',[140 410 230 450]);
pulse=A('simulink/Sources/Pulse Generator','Logic_Command',[70 240 130 275]);
set_param(pulse,'Amplitude','1','Period','0.002','PulseWidth','50','PhaseDelay','0.001');
sp=A(sprintf('nesl_utility/Simulink-PS\nConverter'),'Logic_to_PS',[190 235 250 280]); set_param(sp,'Unit','1');
% Port labels and connection handles are recorded to make wiring auditable.
fid=fopen('port_mapping.txt','w');
for b=[q d s r i vce vge g sol sp]
 fprintf(fid,'\n%s\n%s\n',getfullname(b),get_param(b,'MaskDisplay'));
 ph=get_param(b,'PortHandles'); fields={'LConn','RConn'};
 for z=1:2
  hh=ph.(fields{z});
  for k=1:numel(hh), fprintf(fid,'%s%d %s\n',fields{z},k,mat2str(get_param(hh(k),'Position'))); end
 end
end
fclose(fid);
Q=get_param(q,'PortHandles'); D=get_param(d,'PortHandles'); S=get_param(s,'PortHandles'); R=get_param(r,'PortHandles'); I=get_param(i,'PortHandles');
VC=get_param(vce,'PortHandles'); VG=get_param(vge,'PortHandles'); G=get_param(g,'PortHandles'); SO=get_param(sol,'PortHandles'); SP=get_param(sp,'PortHandles');
wire=@(a,b)add_line(m,a,b,'autorouting','on');
% Foundation sensor: LConn1 = +, RConn1 = -, RConn2 = physical output.
wire(S.LConn(1),R.LConn(1)); wire(R.RConn(1),I.LConn(1)); wire(I.RConn(1),Q.RConn(1));
wire(Q.RConn(2),S.RConn(1)); wire(Q.RConn(2),G.LConn(1)); wire(G.LConn(1),SO.RConn(1));
wire(D.RConn(1),Q.LConn(1)); wire(D.RConn(2),Q.RConn(2));
wire(VC.LConn(1),Q.RConn(1)); wire(VC.RConn(1),Q.RConn(2));
wire(VG.LConn(1),Q.LConn(1)); wire(VG.RConn(1),Q.RConn(2));
add_line(m,'Logic_Command/1','Logic_to_PS/1'); wire(SP.RConn(1),D.LConn(1));
outs={VG.RConn(2), VC.RConn(2), I.RConn(2)};
names={'Vge','Vce','Ic'}; units={'V','V','A'};
for k=1:3
 y=90+100*k;
 c=A(sprintf('nesl_utility/PS-Simulink\nConverter'),[names{k} '_to_Simulink'],[830 y 880 y+35]); set_param(c,'Unit',units{k});
 cp=get_param(c,'PortHandles'); wire(outs{k},cp.LConn(1));
 w=A('simulink/Sinks/To Workspace',[names{k} '_Log'],[950 y 1040 y+35]);
 set_param(w,'VariableName',names{k},'SaveFormat','Timeseries');
 add_line(m,[names{k} '_to_Simulink/1'],[names{k} '_Log/1']);
end
Simulink.Annotation(m,sprintf('ILLUSTRATIVE BASELINE: 12 V DC, 100 Ohm, ideal IGBT\n+15/-15 V physical gate driver; 500 Hz, 50%%, initially OFF\nVth=6 V, Vf=0.8 V, Ron=0.1 Ohm, Goff=1e-8 S\nNo hardware ratings, thermal dynamics, parasitic capacitances or faults.'));
set_param(m,'SimscapeLogType','all');
save_system(m,fullfile(root,[m '.slx']));
set_param(m,'SimulationCommand','update');
out=sim(m); save('baseline_results.mat','out');
validate_baseline(out);
save_system(m); close_system(m,0);
end
function setByPrompt(b,prompt,value)
n=get_param(b,'MaskNames'); p=get_param(b,'MaskPrompts');
idx=find(contains(string(p),prompt,'IgnoreCase',true));
if numel(idx)~=1, error('Cannot uniquely identify driver parameter: %s',prompt); end
set_param(b,n{idx},value);
end



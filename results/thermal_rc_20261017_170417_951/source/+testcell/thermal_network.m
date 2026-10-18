function net = thermal_network(m,th)
% Two-node Cauer network; normalized mass only implements C = m*cp.
% The 1 kg normalization does not describe the physical device mass.
a=@(src,name,pos,varargin)testcell.add(m,src,name,pos,varargin{:});
w=@(x,y)testcell.wire(m,x,y); ph=@testcell.ports;
j=a('fl_lib/Thermal/Thermal Elements/Thermal Mass','JunctionMass',[160 700 210 750], ...
 'mass','1','sp_heat',num2str(th.Cj_J_K),'T',num2str(th.ambient_K),'T_unit','K','T_specify','on','T_priority','High'); J=ph(j);
c=a('fl_lib/Thermal/Thermal Elements/Thermal Mass','CaseMass',[400 700 450 750], ...
 'mass','1','sp_heat',num2str(th.Cc_J_K),'T',num2str(th.ambient_K),'T_unit','K','T_specify','on','T_priority','High'); C=ph(c);
rjc=a('fl_lib/Thermal/Thermal Elements/Thermal Resistance','Rjc',[260 650 320 690],'resistance',num2str(th.Rjc_K_W)); RJC=ph(rjc);
rca=a('fl_lib/Thermal/Thermal Elements/Thermal Resistance','Rca',[520 650 580 690],'resistance',num2str(th.Rca_K_W)); RCA=ph(rca);
amb=a('fl_lib/Thermal/Thermal Sources/Temperature Source','Ambient',[640 650 690 700],'temperature',num2str(th.ambient_K),'temperature_unit','K'); AMB=ph(amb);
w(J.LConn,RJC.LConn); w(RJC.RConn,C.LConn); w(C.LConn,RCA.LConn); w(RCA.RConn,AMB.LConn);
ref=a('fl_lib/Thermal/Thermal Elements/Thermal Reference','ThermalReference',[660 820 700 850]); REF=ph(ref);
blocks=[j c rjc rca amb ref];
for name={'Tj','Tc'}
 sensor=a('fl_lib/Thermal/Thermal Sensors/Temperature Sensor',[name{1} 'Sensor'],[760 700 810 750]); SEN=ph(sensor);
 if strcmp(name{1},'Tj'), w(SEN.LConn,J.LConn); else, w(SEN.LConn,C.LConn); end
 w(SEN.RConn(2),REF.LConn);
 blocks=[blocks sensor testcell.log_signal(m,SEN.RConn(1),name{1},'K',[870 700+80*strcmp(name{1},'Tc') 920 735+80*strcmp(name{1},'Tc')])]; %#ok<AGROW>
end
net.junction=J.LConn; net.reference=REF.LConn; net.blocks=blocks; net.masses=[j c];
end

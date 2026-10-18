function folder=validate_thermal
p=testcell.parameters; th=p.thermal; folder=testcell.new_run('thermal_rc');
testcell.write_json(fullfile(folder,'parameters.json'),p);
load_system('fl_lib'); load_system('nesl_utility'); m='tc_thermal_rc'; assert(~bdIsLoaded(m)); new_system(m);
cleanup=onCleanup(@()close_system(m,0)); %#ok<NASGU>
set_param(m,'Solver','ode15s','RelTol','1e-8','AbsTol','1e-9','MaxStep','0.1','StopTime','300','ReturnWorkspaceOutputs','on');
net=testcell.thermal_network(m,th);
s=testcell.add(m,'nesl_utility/Solver Configuration','Solver',[100 850 200 900]); S=testcell.ports(s); testcell.wire(m,S.RConn,net.junction);
h=testcell.add(m,'fl_lib/Thermal/Thermal Sources/Controlled Heat Flow Rate Source','Heater',[70 660 120 720]); H=testcell.ports(h);
testcell.wire(m,H.LConn,net.junction); testcell.wire(m,H.RConn(2),net.reference);
c=testcell.add(m,'simulink/Sources/Constant','Power10W',[40 450 100 480],'Value','10'); %#ok<NASGU>
ps=testcell.add(m,sprintf('nesl_utility/Simulink-PS\nConverter'),'PowerPS',[60 520 120 560],'Unit','W'); PS=testcell.ports(ps);
add_line(m,'Power10W/1','PowerPS/1'); testcell.wire(m,PS.RConn,H.RConn(1));
set_param(m,'SimscapeLogType','all'); save_system(m,fullfile(folder,[m '.slx']));
set_param(m,'SimulationCommand','update'); fprintf('THERMAL RC COMPILE PASS\n'); out=sim(m); save(fullfile(folder,'thermal_raw.mat'),'out','p');
testcell.assert_no_solver_warnings(out);
t=out.Tj.Time; y=[out.Tj.Data,out.Tc.Data];
A=[-1/(th.Cj_J_K*th.Rjc_K_W),1/(th.Cj_J_K*th.Rjc_K_W); ...
 1/(th.Cc_J_K*th.Rjc_K_W),-(1/th.Rjc_K_W+1/th.Rca_K_W)/th.Cc_J_K];
b=[10/th.Cj_J_K;0]; steady=-A\b; analytic=zeros(numel(t),2);
for k=1:numel(t), analytic(k,:)=th.ambient_K+(steady-expm(A*t(k))*steady)'; end
err=max(abs(y-analytic),[],'all'); assert(err<1e-4,'Cauer model disagrees with matrix exponential.');
assert(abs(y(end,1)-(th.ambient_K+12))<1e-3 && abs(y(end,2)-(th.ambient_K+10))<1e-3,'Thermal steady state failed.');
loss=(y(:,2)-th.ambient_K)/th.Rca_K_W;
energyIn=10*t(end); stored=th.Cj_J_K*(y(end,1)-y(1,1))+th.Cc_J_K*(y(end,2)-y(1,2));
res=abs(energyIn-stored-trapz(t,loss))/energyIn; assert(res<1e-4,'Thermal energy balance failed.');
record=struct('status','PASS','scope','Assumed thermal RC equation validation, not module thermal identification', ...
 'hardware_decision','INCONCLUSIVE','max_analytic_error_K',err,'energy_relative_error',res, ...
 'final_junction_C',y(end,1)-273.15,'final_case_C',y(end,2)-273.15,'time_constants_s',-1./eig(A));
testcell.write_json(fullfile(folder,'validation.json'),record);
writetable(table(t,y(:,1),y(:,2),analytic(:,1),analytic(:,2),'VariableNames',{'time_s','Tj_K','Tc_K','analytic_Tj_K','analytic_Tc_K'}),fullfile(folder,'thermal.csv'));
f=figure('Visible','off','Color','w'); plot(t,y-273.15,'LineWidth',1.5); xlabel('Time (s)'); ylabel('Temperature (C)'); title('Assumed two-node thermal RC: 10 W step'); legend('Junction','Case'); grid on;
set(gca,'Color','w','XColor','k','YColor','k'); set(findall(f,'Type','text'),'Color','k'); exportgraphics(f,fullfile(folder,'thermal_rc.png'),'Resolution',160,'BackgroundColor','white'); close(f);
fprintf('THERMAL RC PASS: max error %g K, energy error %g. %s\n',err,res,folder);
end

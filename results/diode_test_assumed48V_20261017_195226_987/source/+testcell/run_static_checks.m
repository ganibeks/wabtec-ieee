function folder = run_static_checks(p)
% Datasheet-condition static tests on the existing fixtures (static_v / static_i, unchanged):
%   VGE(th): VCE = 10 V, find VGE giving IC = 150 mA (bisection), Tj = 25 C
%   ICES   : VCE = Vces (3300 V), VGE = 0, Tj = 25 C; calibration recovery at Tcal / Tsecond
%   VCEsat : IC forced by current clamp, VGE = 15 V, at 25 C, Tcal and Tsecond
% Numerical checks decide status (PASS / PARTIAL). Comparisons with p.datasheetLimits are reported
% separately and are manufacturer limits of a representative device, NOT acceptance limits.
if nargin<1, p=testcell.parameters_traction; end
assert(isfield(p,'datasheetLimits'),'Parameter set has no datasheet limits (use parameters_traction).');
L=p.datasheetLimits;
folder=testcell.new_run('static_checks'); testcell.write_json(fullfile(folder,'parameters.json'),p);
r=struct('scope','Simulated static checks at datasheet conditions; model built from the same datasheet', ...
 'hardware_decision','INCONCLUSIVE','limits_source',L.source,'errors',{{}});
ballast=0.1; % static_v fixture series resistance (build_rig.m)

%% ---- voltage fixture: VGE(th) and ICES ------------------------------------------------------------
rig=testcell.build_rig('static_v',p,folder); cleanup=onCleanup(@()close_system(rig.model,0)); %#ok<NASGU>
set_param(rig.model,'SimulationCommand','update');
fprintf('STATIC CHECKS COMPILE PASS: static_v\n');
try
 force=L.VGEth_VCE_V+ballast*L.VGEth_IC_A;   % so that terminal Vce ~ 10 V at the 150 mA point
 lo=4; hi=9; pts=table;
 a=testcell.static_case(rig,force,lo,25,'vth_lo',folder); b=testcell.static_case(rig,force,hi,25,'vth_hi',folder);
 assert(a.Ic_A<L.VGEth_IC_A && b.Ic_A>L.VGEth_IC_A,'VGE(th) not bracketed by 4..9 V');
 pts=[pts;a;b];
 for k=1:16
  g=round((lo+hi)/2*1e4)/1e4; s=testcell.static_case(rig,force,g,25,sprintf('vth_%02d',k),folder); pts=[pts;s]; %#ok<AGROW>
  if s.Ic_A<L.VGEth_IC_A, lo=g; else, hi=g; end
  if abs(s.Ic_A/L.VGEth_IC_A-1)<1e-3, break; end
 end
 [~,j]=min(abs(pts.Ic_A-L.VGEth_IC_A)); best=pts(j,:);
 assert(abs(best.Ic_A/L.VGEth_IC_A-1)<1e-3,'VGE(th) bisection did not reach 0.1 %% of 150 mA');
 r.VGEth_V=best.Vge_V; r.VGEth_at_Ic_A=best.Ic_A; r.VGEth_at_Vce_V=best.Vce_V; r.VGEth_points=height(pts);
 r.VGEth_model_input_V=p.Vth_V;
 r.VGEth_within_datasheet=best.Vge_V>=L.VGEth_min_V && best.Vge_V<=L.VGEth_max_V;
 writetable(pts,fullfile(folder,'vth_points.csv'));
 fprintf('VGE(th) = %.4f V at Ic = %.6g A, Vce = %.4f V (datasheet %.2f..%.2f V)\n',r.VGEth_V,best.Ic_A,best.Vce_V,L.VGEth_min_V,L.VGEth_max_V);
catch ME
 r.errors{end+1}=['VGEth: ' ME.message]; fprintf(2,'VGEth FAILED: %s\n',ME.message);
end
% Calibration temperatures must recover their inputs; other temperatures are reported as predictions.
temps=unique([25 p.Tcal_C p.Tsecond_C 150]);
leak=struct('T_C',num2cell(temps),'expect',num2cell(NaN(size(temps))));
for k=1:numel(temps)
 if temps(k)==p.Tcal_C, leak(k).expect=p.leakageCalibration_A; elseif temps(k)==p.Tsecond_C, leak(k).expect=p.leakageSecond_A; end
end
r.ICES=[];
for k=1:numel(leak)
 try
  s=testcell.static_case(rig,L.ICES_VCE_V,0,leak(k).T_C,sprintf('ices_T%d',leak(k).T_C),folder);
  e=struct('T_C',leak(k).T_C,'Ic_A',s.Ic_A,'Vce_V',s.Vce_V,'calibration_target_A',leak(k).expect,'recovery_rel_error',NaN);
  if isfinite(leak(k).expect)
   e.recovery_rel_error=abs(s.Ic_A-leak(k).expect)/leak(k).expect;
   assert(e.recovery_rel_error<0.05,'ICES calibration recovery failed at %g C',leak(k).T_C);
  end
  r.ICES=[r.ICES e];
  fprintf('ICES(%g C) = %.6g A at Vce = %.2f V\n',leak(k).T_C,s.Ic_A,s.Vce_V);
 catch ME
  r.errors{end+1}=sprintf('ICES %g C: %s',leak(k).T_C,ME.message); fprintf(2,'ICES %g C FAILED: %s\n',leak(k).T_C,ME.message);
 end
end
if ~isempty(r.ICES) && r.ICES(1).T_C==25
 r.ICES25_A=r.ICES(1).Ic_A; r.ICES25_within_datasheet=r.ICES25_A<=L.ICES_max_A;
end
close_system(rig.model,0); clear cleanup;

%% ---- current fixture: VCEsat -----------------------------------------------------------------------
rig=testcell.build_rig('static_i',p,folder); cleanup=onCleanup(@()close_system(rig.model,0)); %#ok<NASGU>
set_param(rig.model,'SimulationCommand','update');
fprintf('STATIC CHECKS COMPILE PASS: static_i\n');
sat=struct('T_C',num2cell(temps),'expect',num2cell(NaN(size(temps))));
for k=1:numel(temps)
 if temps(k)==p.Tcal_C, sat(k).expect=p.VceCalibration_V; elseif temps(k)==p.Tsecond_C, sat(k).expect=p.VceSecond_V; end
end
r.VCEsat=[];
for k=1:numel(sat)
 try
  s=testcell.static_case(rig,L.VCEsat_IC_A,15,sat(k).T_C,sprintf('vcesat_T%d',sat(k).T_C),folder);
  e=struct('T_C',sat(k).T_C,'Vce_V',s.Vce_V,'Ic_A',s.Ic_A,'calibration_target_V',sat(k).expect,'recovery_abs_error_V',NaN);
  if isfinite(sat(k).expect)
   e.recovery_abs_error_V=abs(s.Vce_V-sat(k).expect);
   assert(e.recovery_abs_error_V<0.05,'VCEsat calibration recovery failed at %g C',sat(k).T_C);
  end
  r.VCEsat=[r.VCEsat e];
  fprintf('VCEsat(%g C) = %.5f V at Ic = %.6g A\n',sat(k).T_C,s.Vce_V,s.Ic_A);
 catch ME
  r.errors{end+1}=sprintf('VCEsat %g C: %s',sat(k).T_C,ME.message); fprintf(2,'VCEsat %g C FAILED: %s\n',sat(k).T_C,ME.message);
 end
end
ix=find([r.VCEsat.T_C]==150,1);
if ~isempty(ix)
 r.VCEsat150_V=r.VCEsat(ix).Vce_V; r.VCEsat150_within_datasheet=r.VCEsat150_V<=L.VCEsat_max150_V;
 if p.Tcal_C==150 || p.Tsecond_C==150
  r.VCEsat150_note='150 C is a model calibration point; agreement with the 3.70 V max is not independent evidence';
 else
  r.VCEsat150_note='150 C is a model prediction (calibrated at 25/125 C); datasheet typ 3.30 V, max 3.70 V';
 end
end
close_system(rig.model,0); clear cleanup;

if isempty(r.errors), r.status='PASS'; else, r.status='PARTIAL'; end
r.numerical_checks='DC drift (static_case), bisection to 0.1 % of 150 mA, ICES/VCEsat calibration recovery (5 % / 0.05 V)';
testcell.write_json(fullfile(folder,'validation.json'),r);
fprintf('STATIC CHECKS %s: %s\n',r.status,folder);
end

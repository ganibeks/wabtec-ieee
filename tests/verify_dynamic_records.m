function folder = verify_dynamic_records(folder)
% Re-analyze saved raw outputs; mutated records are validation test fixtures,
% not physical fault simulations. Original MAT/SLX/JSON files are never written.
if nargin<1, folder=testcell.new_run('validation_guard_regression'); end
root=fileparts(fileparts(mfilename('fullpath')));
names={'Vge','Vce','Ic','Ig','IL','Id','Ibus','Vswitch'};
runs={'dynamic_20261017_165933_696','dynamic_20261017_195453_347'};
cases=struct('name',{},'status',{},'detail',{});
for j=1:numel(runs)
 source=fullfile(root,'results',runs{j});
 saved=jsondecode(fileread(fullfile(source,'dynamic_rl_validation.json')));
 for variant={'raw','fine_raw'}
  data=load(fullfile(source,['dynamic_rl_' variant{1} '.mat']));
  if isfield(data,'out'), out=data.out; else, out=data.fine; end
  r=testcell.analyze_dynamic(out,data.p,'dynamic_rl');
  assert(strcmp(r.status,'PASS') && r.record_complete);
  assert(all(isfinite([r.events([2 4]).current_clearance_1percent_s])));
  if strcmp(variant{1},'raw')
   for field={'peak_Vce_V','peak_Ic_A','bus_energy_J','energy_balance_relative_error'}
    key=field{1}; assert(abs(r.(key)-saved.(key))<=1e-12*max(1,abs(saved.(key))), ...
     'Healthy measurement changed: %s',key);
   end
  end
  record([runs{j} '_' variant{1}], 'Complete healthy record accepted; physical metrics retained');
 end
end
data=load(fullfile(root,'results',runs{1},'dynamic_rl_raw.mat'));
original=struct;
for k=1:numel(names), original.(names{k})=data.out.(names{k}); end
p=data.p;
% Exact previously reproduced failure: data ends before OFF-2 clearance.
bad=trim(original,@(t)t<=535e-6,names);
reject('truncated_at_535us',bad,p,'testcell:IncompleteRecord');
% Catch missing late data even when all switching transitions were recorded.
bad=trim(original,@(t)t<=700e-6,names);
reject('missing_end_of_experiment',bad,p,'testcell:IncompleteRecord');
bad=trim(original,@(t)t>=20e-6,names);
reject('missing_initial_record',bad,p,'testcell:IncompleteRecord');
bad=trim(original,@(t)t<=700e-6,{'Ig'});
reject('single_channel_truncated',bad,p,'testcell:IncompleteRecord');
% Endpoints intact; interpolation must not conceal a hole in just one channel.
bad=trim(original,@(t)t<390e-6 | t>410e-6,{'Vce'});
reject('missing_voltage_transition_samples',bad,p,'testcell:RecordGap');
short=p; short.dynamicStop_s=535e-6;
reject('configured_stop_before_event_end',original,short,'testcell:InvalidRecordPlan');
% Full-length corrupted replay: retain all transition crossings but suppress
% the voltage recovery required by the existing clearance definition.
bad=original; t=original.Vce.Time; v=original.Vce.Data;
edge=p.pulseEdges_s(4);
ic=interp1(original.Ic.Time,original.Ic.Data,t);
ref=median(ic(t>edge-10e-6 & t<edge-5e-6));
ix=t>edge & t<edge+80e-6 & ic<.01*ref;
v(ix)=.985*p.bus_V;
bad.Vce=timeseries(v,t);
reject('complete_record_without_clearance',bad,p,'testcell:UnresolvedClearance');
report=struct('status','PASS','scope','Saved-data software regression; no new physical simulation', ...
 'hardware_decision','INCONCLUSIVE','cases',cases);
target=fullfile(folder,'matlab_regression.json'); assert(~isfile(target),'Preserve existing regression output.');
testcell.write_json(target,report);
fprintf('VALIDATION GUARD REGRESSION: %d/%d PASS\nRESULT_FOLDER=%s\n',numel(cases),numel(cases),folder);

 function record(name,detail)
  cases(end+1)=struct('name',name,'status','PASS','detail',detail);
  fprintf('PASS %s: %s\n',name,detail);
 end
 function reject(name,bad,params,identifier)
  try
   testcell.analyze_dynamic(bad,params,'dynamic_rl');
  catch ME
   assert(strcmp(ME.identifier,identifier),'Unexpected rejection for %s: %s (%s)',name,ME.identifier,ME.message);
   record(name,ME.identifier); return;
  end
  error('testcell:RegressionAcceptedInvalidRecord','Invalid record accepted: %s',name);
 end
end

function out=trim(original,predicate,names)
out=original;
for k=1:numel(names)
 s=original.(names{k}); ix=predicate(s.Time);
 out.(names{k})=timeseries(s.Data(ix),s.Time(ix));
end
end

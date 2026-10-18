function runDir = verify_saved_baseline(modelFile)
% Verify the saved artifact without rebuilding or overwriting it.
root=fileparts(mfilename('fullpath')); addpath(root);
assert(isfile(modelFile),'Saved SLX not found.');
[~,m]=fileparts(modelFile);
assert(~bdIsLoaded(m),'Close the model before standalone verification.');
runDir=fullfile(root,'results',['verify_' char(datetime('now','Format','yyyyMMdd_HHmmss_SSS'))]);
mkdir(runDir); previous=pwd; cd(runDir);
restore=onCleanup(@()cd(previous)); %#ok<NASGU>
copyfile(fullfile(root,'validate_baseline.m'),fullfile(runDir,'validate_baseline_source.m'));
load_system(modelFile); closeModel=onCleanup(@()close_system(m,0)); %#ok<NASGU>
% Targeted saved-configuration checks before executing the full 6 ms run.
q=[m '/IGBT_illustrative']; d=[m '/Gate_Driver'];
assert(strcmp(get_param(q,'port_option'),'ee.enum.controlport.elec'));
assert(str2double(get_param(q,'Vth'))==6);
assert(str2double(get_param(d,'vHigh'))==15 && str2double(get_param(d,'vLow'))==-15);
assert(str2double(get_param([m '/Supply_12V_illustrative'],'v0'))==12);
assert(str2double(get_param([m '/Load_100Ohm_illustrative'],'R'))==100);
set_param(m,'SimulationCommand','update');
fprintf('Saved model configuration and compilation: PASS\n');
out=sim(m); save('baseline_results.mat','out');
validate_baseline(out);
fid=fopen('verified_model.txt','w'); fprintf(fid,'%s\n',modelFile); fclose(fid);
fprintf('Standalone saved-model verification: PASS\nOutput: %s\n',runDir);
end

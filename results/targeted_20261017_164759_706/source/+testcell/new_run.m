function runDir = new_run(label)
root=fileparts(fileparts(mfilename('fullpath')));
runDir=fullfile(root,'results',[label '_' char(datetime('now','Format','yyyyMMdd_HHmmss_SSS'))]);
assert(~isfolder(runDir)); mkdir(runDir);
copyfile(fullfile(root,'+testcell'),fullfile(runDir,'source','+testcell'));
end

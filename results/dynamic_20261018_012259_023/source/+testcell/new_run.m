function runDir = new_run(label)
root=fileparts(fileparts(mfilename('fullpath')));
% mkdir itself is the atomic claim: two MATLAB sessions started in the same millisecond once shared a folder
% (results/dynamic_20261018_001722_232), so a folder that already exists is never reused.
for attempt=1:50
 runDir=fullfile(root,'results',[label '_' char(datetime('now','Format','yyyyMMdd_HHmmss_SSS'))]);
 [ok,~,msgId]=mkdir(runDir);
 if ok && ~strcmp(msgId,'MATLAB:MKDIR:DirectoryExists'), break, end
 assert(attempt<50,'Could not claim a new run folder for %s',label);
 pause(0.002+0.01*rand);
end
copyfile(fullfile(root,'+testcell'),fullfile(runDir,'source','+testcell'));
end

function manifestFolder = run_electrical_lab
% Reproducible sequence; failures remain failures and preserve all prior output.
p=testcell.parameters; manifestFolder=testcell.new_run('electrical_lab');
testcell.write_json(fullfile(manifestFolder,'parameters.json'),p);
manifest=struct('status','RUNNING','hardware_decision','INCONCLUSIVE');
try
 testcell.targeted_checks;
 manifest.static=testcell.run_static(p); testcell.report(manifest.static);
 manifest.dynamic=testcell.run_dynamic(p); testcell.report(manifest.dynamic);
 manifest.status='PASS';
catch ME
 manifest.status='FAILED'; manifest.error_identifier=ME.identifier; manifest.error_message=ME.message;
 testcell.write_json(fullfile(manifestFolder,'manifest.json'),manifest); rethrow(ME);
end
testcell.write_json(fullfile(manifestFolder,'manifest.json'),manifest);
end

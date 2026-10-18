function probe_component
folder=testcell.new_run('component_probe'); diary(fullfile(folder,'interfaces.txt'));
load_system('nesl_utility'); new_system('component_probe');
paths=find_system('nesl_utility','SearchDepth',1,'Type','Block');
for k=1:numel(paths), fprintf('%s\n',paths{k}); end
ix=find(contains(regexprep(string(paths),'\s',''),'SimscapeComponent'));
assert(numel(ix)==1,'Generic Simscape Component library entry not unique.');
q=add_block(paths{ix},'component_probe/IGBT');
simscape.setBlockComponent(q,'ee.semiconductors.n_igbt_thermal');
testcell.apply_device(q,testcell.parameters,25);
disp(get_param(q,'PortHandles'));
save_system('component_probe',fullfile(folder,'thermal_component.slx')); close_system('component_probe',0); diary off;
end

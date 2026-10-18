function folder = export_presentation(folder)
% Format a separate copy of the saved electrical rig; original is read-only.
root=fileparts(fileparts(mfilename('fullpath')));
source=fullfile(root,'results','dynamic_20261017_195453_347','tc_dynamic_rl.slx');
assert(isfile(source),'Saved reference model is missing.');
m='tc_dynamic_rl'; assert(~bdIsLoaded(m),'Close the loaded %s model before running this exporter.',m);
if nargin<1, folder=testcell.new_run('presentation'); end
assert(isfolder(folder),'Presentation output folder must exist.');
assert(~isfile(fullfile(folder,[m '.slx'])),'Preserve existing presentation model.');
copyfile(source,fullfile(folder,[m '.slx']));
load_system(fullfile(folder,[m '.slx']));
c=onCleanup(@()close_system(m,0)); %#ok<NASGU>
names={'DUT','GateDrive','LoadBank','Supply','Measurements'};
for k=1:numel(names)
 sub=[m '/' names{k}];
 Simulink.BlockDiagram.arrangeSystem(sub);
 set_param(sub,'FontName','Arial','FontSize','12','FontWeight','bold','ShowPortLabels','none');
 options=get_param(sub,'ObjectParameters');
 if isfield(options,'ContentPreviewEnabled'), set_param(sub,'ContentPreviewEnabled','off'); end
end
colours=struct('Supply','[0.88 0.93 0.99]','LoadBank','[0.89 0.95 0.94]', ...
 'GateDrive','[0.87 0.96 0.94]','DUT','[1.0 0.91 0.79]','Measurements','[0.92 0.92 0.98]');
for name=fieldnames(colours)'
 set_param([m '/' name{1}],'BackgroundColor',colours.(name{1}),'ForegroundColor','[0.1 0.17 0.26]');
end
Simulink.BlockDiagram.arrangeSystem(m);
set_param(m,'ZoomFactor','FitSystem');
% Compile the cosmetic copy without running a new experiment.
save_system(m,fullfile(folder,[m '.slx']));
set_param(m,'SimulationCommand','update');
print(['-s' m],'-dpng','-r200',fullfile(folder,'simulink_overview.png'));
for name={'DUT','GateDrive','LoadBank'}
 print(['-s' m '/' name{1}],'-dpng','-r200',fullfile(folder,['simulink_' lower(name{1}) '.png']));
end
manifest=struct('source_model',source,'scope','Presentation layout only; compiled, not resimulated', ...
 'hardware_decision','INCONCLUSIVE');
testcell.write_json(fullfile(folder,'presentation.json'),manifest);
fprintf('PRESENTATION_FOLDER=%s\n',folder);
end

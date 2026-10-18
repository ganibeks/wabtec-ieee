function package_electrical
root=fileparts(fileparts(mfilename('fullpath')));
folder=fullfile(root,'results','static25_20261017_165838_504');
a=readtable(fullfile(folder,'static_curves.csv')); b=readtable(fullfile(folder,'saturation.csv'));
% Preserve first successful figures and generate corrected evidence in a new folder.
plotFolder=fullfile(folder,'plots_final'); mkdir(plotFolder); testcell.plot_static(a,b,plotFolder);
copyfile(fullfile(root,'+testcell','plot_static.m'),fullfile(plotFolder,'plot_static_source.m'));
for name={'static25_20261017_165838_504','dynamic_20261017_165933_696'}
 testcell.report(fullfile(root,'results',name{1}));
end
end

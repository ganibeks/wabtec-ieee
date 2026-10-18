function inspect_detailed
root=fileparts(mfilename('fullpath')); outDir=fullfile(root,'results',['interfaces_' char(datetime('now','Format','yyyyMMdd_HHmmss'))]); mkdir(outDir);
diary(fullfile(outDir,'interfaces.txt'));
load_system('ee_lib'); load_system('fl_lib'); load_system('nesl_utility'); new_system('detail_probe');
paths={sprintf('ee_lib/Semiconductors &\nConverters/N-Channel IGBT'),sprintf('ee_lib/Semiconductors &\nConverters/Diode'),'fl_lib/Electrical/Electrical Elements/Inductor','fl_lib/Electrical/Electrical Sources/Controlled Current Source','fl_lib/Thermal/Thermal Sources/Controlled Temperature Source','fl_lib/Thermal/Thermal Elements/Thermal Reference'};
for k=1:numel(paths)
 try
 b=add_block(paths{k},['detail_probe/B' num2str(k)]); fprintf('\nBLOCK %s\n',paths{k});
 names=get_param(b,'MaskNames'); vals=get_param(b,'MaskValues');
 for j=1:numel(names)
  if isempty(regexp(names{j},'_conf|_specify|_priority|_nominal','once')), fprintf('%s = %s\n',names{j},vals{j}); end
 end
 ph=get_param(b,'PortHandles'); disp(ph);
 catch ME, disp(getReport(ME,'basic')); end
end
for name={'ee.enum.igbt.temperatureParameterization','ee.enum.igbt.capacitanceParam','ee.enum.igbt.parameterization'}
 disp(name{1}); disp(enumeration(name{1}));
end
save_system('detail_probe',fullfile(outDir,'detail_probe.slx')); close_system('detail_probe',0); diary off;
end

function inspect_thermal
folder=testcell.new_run('thermal_interfaces'); diary(fullfile(folder,'interfaces.txt'));
load_system('ee_lib'); load_system('fl_lib'); new_system('thermal_probe');
p=testcell.parameters;
q=testcell.add('thermal_probe',sprintf('ee_lib/Semiconductors &\nConverters/N-Channel IGBT'),'IGBT',[500 150 560 230]);
set_param(q,'ComponentPath','ee.semiconductors.n_igbt_thermal'); testcell.apply_device(q,p,25);
disp(get_param(q,'ComponentPath')); disp(get_param(q,'PortHandles'));
paths={'fl_lib/Thermal/Thermal Elements/Thermal Mass','fl_lib/Thermal/Thermal Elements/Thermal Resistance', ...
 'fl_lib/Thermal/Thermal Sources/Temperature Source','fl_lib/Thermal/Thermal Sources/Controlled Heat Flow Rate Source', ...
 'fl_lib/Thermal/Thermal Sensors/Temperature Sensor','fl_lib/Thermal/Thermal Sensors/Heat Flow Rate Sensor'};
for k=1:numel(paths)
 try
 b=testcell.add('thermal_probe',paths{k},['B' num2str(k)],[50+80*k 300 100+80*k 350]);
 fprintf('\n%s\n',paths{k}); names=get_param(b,'MaskNames'); vals=get_param(b,'MaskValues');
 for j=1:numel(names)
  if isempty(regexp(names{j},'_conf|_nominal|ComponentVariant|ClassName|Schema','once')), fprintf('%s = %s\n',names{j},vals{j}); end
 end
 disp(get_param(b,'PortHandles'));
 catch ME, disp(ME.message); end
end
save_system('thermal_probe',fullfile(folder,'thermal_probe.slx')); close_system('thermal_probe',0); diary off;
end

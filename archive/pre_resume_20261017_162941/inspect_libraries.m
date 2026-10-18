diary('library_inspection.txt');
disp(version); ver;
libs = {'ee_lib','fl_lib','nesl_utility'};
for k=1:numel(libs)
 load_system(libs{k});
 b=find_system(libs{k},'LookUnderMasks','all','FollowLinks','on','Type','Block');
 for j=1:numel(b)
  if ~isempty(regexpi(b{j},'IGBT|Gate Driver|Voltage Sensor|Current Sensor|DC Voltage Source|Controlled Voltage Source|Electrical Reference|Solver Configuration|PS-Simulink|Simulink-PS|/Resistor$'))
   disp(b{j});
   if contains(b{j},'IGBT')
    disp(get_param(b{j},'DialogParameters'));
    p=get_param(b{j},'MaskNames'); v=get_param(b{j},'MaskValues'); disp([p(:),v(:)]);
   end
  end
 end
end
diary off;

load_system('ee_lib'); load_system('fl_lib'); load_system('nesl_utility');
diary('selected_blocks.txt');
disp(enumeration('ee.enum.controlport'));
new_system('probe');
paths={sprintf('ee_lib/Semiconductors &\nConverters/IGBT\n(Ideal,\nSwitching)'), 'fl_lib/Electrical/Electrical Sources/Controlled Voltage Source', 'fl_lib/Electrical/Electrical Sources/DC Voltage Source', 'fl_lib/Electrical/Electrical Elements/Resistor', 'fl_lib/Electrical/Electrical Sensors/Voltage Sensor','fl_lib/Electrical/Electrical Sensors/Current Sensor',sprintf('nesl_utility/Simulink-PS\nConverter'),sprintf('nesl_utility/PS-Simulink\nConverter'),'nesl_utility/Solver Configuration'};
for k=1:numel(paths)
 b=add_block(paths{k},['probe/b' num2str(k)]); disp(paths{k});
 p=get_param(b,'MaskNames'); v=get_param(b,'MaskValues'); disp([p(:),v(:)]);
 disp(get_param(b,'PortHandles')); disp(get_param(b,'PortConnectivity'));
end
diary off; close_system('probe',0);

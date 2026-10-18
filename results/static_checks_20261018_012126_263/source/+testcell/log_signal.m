function blocks = log_signal(m,port,name,unit,pos)
c=testcell.add(m,sprintf('nesl_utility/PS-Simulink\nConverter'),[name '_PS'],pos,'Unit',unit);
h=testcell.ports(c); testcell.wire(m,port,h.LConn(1));
w=testcell.add(m,'simulink/Sinks/To Workspace',[name '_Log'],pos+[130 0 180 0], ...
 'VariableName',name,'SaveFormat','Timeseries');
add_line(m,[name '_PS/1'],[name '_Log/1']); blocks=[c w];
end

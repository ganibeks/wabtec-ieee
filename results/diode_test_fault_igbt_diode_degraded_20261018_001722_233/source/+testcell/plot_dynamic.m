function plot_dynamic(out,p,label,folder)
x=testcell.measurements(out,{'Vge','Vce','Ic','Ig','IL','Id','Ibus','Vswitch'});
f=figure('Visible','off','Color','w','Position',[30 30 1300 850]); tiledlayout(3,2);
nexttile; plot(x.t*1e6,x.Vge); ylabel('Vge (V)'); title(label,'Interpreter','none');
nexttile; plot(x.t*1e6,x.Vce); ylabel('Vce (V)');
nexttile; plot(x.t*1e6,[x.IL x.Ic x.Id]); ylabel('Current (A)'); legend('Load','Collector','Diode');
nexttile; plot(x.t*1e6,x.Ig); ylabel('Gate current (A)');
nexttile; plot(x.t*1e6,x.Vce.*x.Ic); ylabel('Collector terminal power (W)');
nexttile; plot(x.t*1e6,cumtrapz(x.t,x.Vce.*x.Ic)*1e3); ylabel('Collector terminal energy (mJ)');
ax=findall(f,'Type','axes'); set(ax,'Color','w','XColor','k','YColor','k');
for a=ax', grid(a,'on'); xlabel(a,'Time (microseconds)'); end
set(findall(f,'Type','text'),'Color','k'); set(findall(f,'Type','line'),'LineWidth',1.2);
exportgraphics(f,fullfile(folder,[label '.png']),'Resolution',170,'BackgroundColor','white'); close(f);
% Detailed hard-turn-on and turn-off views using solver samples.
f=figure('Visible','off','Color','w','Position',[30 30 1300 800]); tiledlayout(3,2);
for edge=p.pulseEdges_s(3:4)
 for type=1:3
  if abs(edge-p.pulseEdges_s(3))<1e-12, tile=2*type-1; else, tile=2*type; end
  nexttile(tile); ix=x.t>edge-1e-6 & x.t<edge+80e-6;
  switch type
   case 1, y=x.Vge; name='Vge (V)';
   case 2, y=x.Vce; name='Vce (V)';
   case 3, y=x.Ic; name='Ic (A)';
  end
  plot((x.t(ix)-edge)*1e6,y(ix)); ylabel(name); xlabel('Time from command (microseconds)'); grid on;
 end
end
set(findall(f,'Type','axes'),'Color','w','XColor','k','YColor','k'); set(findall(f,'Type','text'),'Color','k');
exportgraphics(f,fullfile(folder,[label '_transients.png']),'Resolution',170,'BackgroundColor','white'); close(f);
% Export numerical samples; MAT retains all original timestamps and Simscape data.
writetable(table(x.t,x.Vge,x.Vce,x.Ic,x.Ig,x.IL,x.Id,x.Ibus,x.Vswitch, ...
 'VariableNames',{'time_s','Vge_V','Vce_V','Ic_A','Ig_A','IL_A','Id_A','Ibus_A','Vswitch_V'}),fullfile(folder,[label '.csv']));
end



function plot_static(data,sat,folder)
f=figure('Visible','off','Color','w','Position',[50 50 1300 650]);
temps=unique(data.temperature_C); tiledlayout(1,numel(temps)+1);
for j=1:numel(temps)
 nexttile; hold on;
 for gate=[5 7 10 15]
  ix=data.temperature_C==temps(j) & data.gate_command_V==gate & startsWith(data.experiment,'output');
  plot(data.Vce_V(ix),data.Ic_A(ix),'-o','DisplayName',sprintf('Vge=%g V',gate));
 end
 xlabel('Measured Vce (V)'); ylabel('Ic (A)'); title(sprintf('Assumed I-V, %g C',temps(j))); legend('Location','northwest'); grid on;
end
nexttile; hold on;
for T=unique(sat.temperature_C)'
 ix=sat.temperature_C==T; plot(sat.Ic_A(ix),sat.Vce_V(ix),'-o','DisplayName',sprintf('%g C (%d points)',T,nnz(ix)));
end
xlabel('Forced Ic (A)'); ylabel('Measured Vce(sat) (V)'); title('Vge=15 V, current-clamp fixture'); legend; grid on;
style(f); exportgraphics(f,fullfile(folder,'static_characteristics.png'),'Resolution',170,'BackgroundColor','white'); close(f);
f=figure('Visible','off','Color','w'); hold on;
for T=unique(data.temperature_C)'
 ix=data.temperature_C==T & data.gate_command_V==-15 & startsWith(data.experiment,'leak');
 semilogy(data.Vce_V(ix),data.Ic_A(ix)*1e6,'-o','DisplayName',sprintf('%g C',T));
end
xlabel('Vce (V)'); ylabel('Off current (microampere)'); title('Assumed leakage, Vge=-15 V'); legend; grid on;
style(f); exportgraphics(f,fullfile(folder,'leakage.png'),'Resolution',170,'BackgroundColor','white'); close(f);
end
function style(f)
set(findall(f,'Type','axes'),'Color','w','XColor','k','YColor','k','GridColor',[.7 .7 .7]);
set(findall(f,'Type','text'),'Color','k'); set(findall(f,'Type','line'),'LineWidth',1.3);
end

function diagnose_rl
root=fileparts(fileparts(mfilename('fullpath'))); folder=fullfile(root,'results','dynamic_20261017_165503_678');
d=load(fullfile(folder,'dynamic_rl_raw.mat')); x=testcell.measurements(d.out,{'Vge','Vce','Ic','Ig','IL','Id','Ibus','Vswitch'});
for window=[310 320;330 340;340 348;345 349]'
 ix=x.t>window(1)*1e-6 & x.t<window(2)*1e-6;
 fprintf('%g-%g us: min diode %g A, max Ic/IL %g\n',window(1),window(2),min(x.Id(ix)),max(abs(x.Ic(ix)))/mean(x.IL(ix)));
end
testcell.plot_dynamic(d.out,d.p,'rl_diagnostic',folder);
fprintf('Warnings in RL simulation: %d\n',numel(d.out.SimulationMetadata.ExecutionInfo.WarningDiagnostics));
end

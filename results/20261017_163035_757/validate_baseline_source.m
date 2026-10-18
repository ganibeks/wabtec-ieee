function validate_baseline(out)
% Check measured voltages/current against command timing and DC circuit laws.
t=(0:2e-6:0.006)';
vge=interp1(out.Vge.Time,out.Vge.Data,t,'linear');
vce=interp1(out.Vce.Time,out.Vce.Data,t,'linear');
ic=interp1(out.Ic.Time,out.Ic.Data,t,'linear');
assert(all(isfinite([vge;vce;ic])),'Nonfinite logged measurements.');
phase=mod(t,0.002); on=phase>0.0012 & phase<0.0018;
off=phase>0.0002 & phase<0.0008;
expectedI=(12-0.8)/100.1; expectedV=12-100*expectedI;
checks=struct;
checks.on_gate_error_V=max(abs(vge(on)-15));
checks.off_gate_error_V=max(abs(vge(off)+15));
checks.on_current_error_A=max(abs(ic(on)-expectedI));
checks.on_vce_error_V=max(abs(vce(on)-expectedV));
checks.off_current_max_A=max(abs(ic(off)));
checks.off_vce_error_V=max(abs(vce(off)-12));
checks.kvl_error_V=max(abs(vce+100*ic-12));
checks.on_windows=3; checks.off_windows=3;
checks.expected_on_current_A=expectedI; checks.expected_on_vce_V=expectedV;
checks.source_energy_J=trapz(t,12*ic);
checks.peak_source_power_W=max(12*ic);
assert(checks.on_gate_error_V<0.01 && checks.off_gate_error_V<0.01,'Gate voltage levels failed.');
assert(checks.on_current_error_A<1e-4 && checks.on_vce_error_V<0.01,'ON-state circuit law failed.');
assert(checks.off_current_max_A<1e-6 && checks.off_vce_error_V<0.01,'OFF-state blocking failed.');
assert(checks.kvl_error_V<0.01,'KVL failed: inspect wiring and sensor polarity.');
assert(nnz(diff(vge>6)==1)==3 && nnz(diff(vge>6)==-1)>=2,'Switching edge count failed.');
checks.status='PASS';
fid=fopen('validation.json','w'); fprintf(fid,'%s\n',jsonencode(checks,PrettyPrint=true)); fclose(fid);
writetable(table(t,vge,vce,ic,'VariableNames',{'time_s','gate_emitter_V','collector_emitter_V','collector_A'}),'baseline_waveforms.csv');
f=figure('Visible','off','Color','w','Position',[100 100 1100 800]);
tiledlayout(3,1);
nexttile; plot(t*1e3,vge); grid on; ylabel('V_{GE} (V)'); ylim([-18 18]); title('Illustrative 12 V / 100 Ohm IGBT baseline');
nexttile; plot(t*1e3,vce); grid on; ylabel('V_{CE} (V)');
nexttile; plot(t*1e3,ic); grid on; ylabel('I_C (A)'); xlabel('Time (ms)');
exportgraphics(f,'baseline_waveforms.png','Resolution',160); savefig(f,'baseline_waveforms.fig'); close(f);
disp(checks);
end

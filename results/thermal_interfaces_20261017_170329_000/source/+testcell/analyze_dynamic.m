function r = analyze_dynamic(out,p,kind)
x=testcell.measurements(out,{'Vge','Vce','Ic','Ig','IL','Id','Ibus','Vswitch'}); t=x.t;
r=struct('scope','Assumed device numerical validation; no hardware acceptance','hardware_decision','INCONCLUSIVE');
r.kcl_max_A=max(abs(x.IL-x.Ic-x.Id));
r.bus_kcl_max_A=max(abs(x.Ibus-x.IL+x.Id));
assert(r.kcl_max_A<1e-5 && r.bus_kcl_max_A<1e-5,'Current continuity violated.');
% Electrical terminal energy balance, including the inductor's initial energy.
r.bus_energy_J=trapz(t,p.bus_V*x.Ibus);
r.load_resistor_energy_J=trapz(t,p.loadR_Ohm*x.IL.^2);
r.stray_resistor_energy_J=trapz(t,p.strayR_Ohm*x.Ic.^2);
r.dut_collector_terminal_energy_J=trapz(t,x.Vce.*x.Ic);
r.dut_gate_terminal_energy_J=trapz(t,x.Vge.*x.Ig);
r.diode_terminal_energy_J=trapz(t,(x.Vswitch-p.bus_V).*x.Id);
r.stray_stored_energy_change_J=.5*p.strayL_H*(x.Ic(end)^2-x.Ic(1)^2);
if strcmp(kind,'dynamic_rl')
 r.load_stored_energy_change_J=.5*p.loadL_H*(x.IL(end)^2-x.IL(1)^2);
 flux=p.loadL_H*(x.IL-x.IL(1));
 voltageIntegral=cumtrapz(t,p.bus_V-p.loadR_Ohm*x.IL-x.Vswitch);
 r.inductor_flux_relative_error=max(abs(flux-voltageIntegral))/max(max(abs(flux)),1e-9);
 assert(r.inductor_flux_relative_error<.005,'Integrated inductor law failed.');
 freewheel=t>p.pulseEdges_s(3)-10e-6 & t<p.pulseEdges_s(3)-2e-6;
 r.freewheel_min_current_A=min(x.Id(freewheel));
 r.freewheel_Ic_to_IL_ratio=max(abs(x.Ic(freewheel)))/mean(x.IL(freewheel));
 assert(r.freewheel_min_current_A>0.1 && r.freewheel_Ic_to_IL_ratio<.01,'Inductive current did not commutate into diode.');
else
 r.load_stored_energy_change_J=0;
 r.resistive_kvl_max_V=max(abs(p.bus_V-p.loadR_Ohm*x.IL-x.Vswitch));
 assert(r.resistive_kvl_max_V<1e-3,'Resistive-load voltage law failed.');
end
sumE=r.load_resistor_energy_J+r.stray_resistor_energy_J+r.dut_collector_terminal_energy_J+ ...
 r.diode_terminal_energy_J+r.stray_stored_energy_change_J+r.load_stored_energy_change_J;
r.energy_balance_error_J=r.bus_energy_J-sumE;
r.energy_balance_relative_error=abs(r.energy_balance_error_J)/max(abs(r.bus_energy_J),1e-6);
assert(r.energy_balance_relative_error<.005,'Terminal energy balance failed.');
plateau=t>100e-6 & t<200e-6; off=freewheel_mask(t,p);
r.on_gate_max_error_V=max(abs(x.Vge(plateau)-p.gateOn_V));
r.off_gate_max_error_V=max(abs(x.Vge(off)-p.gateOff_V));
assert(r.on_gate_max_error_V<.02 && r.off_gate_max_error_V<.02,'Actual gate plateaus failed.');
r.peak_Vce_V=max(x.Vce); r.peak_Ic_A=max(x.Ic); r.peak_Ig_A=max(abs(x.Ig));
events=cell(1,4); edges=p.pulseEdges_s;
for k=1:numel(edges)
 e=edges(k); if mod(k,2)==1, duration=15e-6; else, duration=80e-6; end; window=[e-2e-6 e+duration]; idx=t>=window(1) & t<=window(2);
 z=struct('command_time_s',e,'window_s',window,'on_event',mod(k,2)==1, ...
  'gross_collector_terminal_energy_J',trapz(t(idx),x.Vce(idx).*x.Ic(idx)), ...
  'gate_charge_C',trapz(t(idx),x.Ig(idx)),'gate_terminal_energy_J',trapz(t(idx),x.Vge(idx).*x.Ig(idx)));
 % Vce 90/10 levels referenced to bus and measured ON plateau.
 onIx=t>e+5e-6 & t<e+10e-6;
 if z.on_event, low=median(x.Vce(onIx)); else
  before=t>e-10e-6 & t<e-5e-6; low=median(x.Vce(before));
 end
 if z.on_event
  a=crossing(t,x.Vce,e,low+.9*(p.bus_V-low),false);
  b=crossing(t,x.Vce,e,low+.1*(p.bus_V-low),false);
 else
  a=crossing(t,x.Vce,e,low+.1*(p.bus_V-low),true);
  b=crossing(t,x.Vce,e,low+.9*(p.bus_V-low),true);
 end
 z.Vce_transition_10_90_s=b-a; z.command_to_Vce_transition_s=a-e;
 if k==3 || ~z.on_event
  if z.on_event
   ref=median(x.IL(t>e+5e-6 & t<e+10e-6));
   a=crossing(t,x.Ic,e,.1*ref,true); b=crossing(t,x.Ic,e,.9*ref,true);
  else
   ref=median(x.Ic(t>e-10e-6 & t<e-5e-6));
   a=crossing(t,x.Ic,e,.9*ref,false); b=crossing(t,x.Ic,e,.1*ref,false);
  end
  z.Ic_transition_10_90_s=b-a;
 else, z.Ic_transition_10_90_s=NaN; end
  if ~z.on_event
  endIx=find(t>e & t<e+80e-6 & x.Ic<.01*ref & x.Vce>.99*p.bus_V,1);
  if isempty(endIx), z.current_clearance_1percent_s=NaN; else, z.current_clearance_1percent_s=t(endIx)-e; end
 else, z.current_clearance_1percent_s=NaN; end
 assert(isfinite(z.Vce_transition_10_90_s),'Voltage transition not resolved within event window.');
 if k>1, assert(isfinite(z.Ic_transition_10_90_s),'Current transition not resolved.'); end
 events{k}=z;
end
r.events=[events{:}];
r.energy_interpretation='Gross event terminal integrals include conduction and reactive transfer; not calibrated Eon/Eoff dissipation.';
r.status='PASS';
end
function result=crossing(t,v,edge,level,rising)
if rising, candidates=find(v(1:end-1)<level & v(2:end)>=level); else
 candidates=find(v(1:end-1)>level & v(2:end)<=level); end
candidates=candidates(t(candidates)>=edge-0.1e-6 & t(candidates)<edge+80e-6);
if isempty(candidates), result=NaN; return; end
j=candidates(1); result=t(j)+(level-v(j))*(t(j+1)-t(j))/(v(j+1)-v(j));
end


function ix=freewheel_mask(t,p)
ix=t>p.pulseEdges_s(3)-10e-6 & t<p.pulseEdges_s(3)-2e-6;
end


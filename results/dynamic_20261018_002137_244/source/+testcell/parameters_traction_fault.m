function p = parameters_traction_fault(id)
% Injected-fault variants of the representative traction device (parameters_traction.m), for showing that the
% tester catches broken IGBTs and gate drivers. Fault SEVERITIES ARE ASSUMED (no Wabtec failure data);
% each fault gets its own schema so its results are never mixed with the healthy device.
% Use ONLY with kind 'dynamic_rl' (same rule as parameters_traction).
p = testcell.parameters_traction;
p.schema = ['testcell.traction_fault.' id '.v1'];
switch id
 case 'igbt_gate_leak'
  p.faultRge_Ohm = 10;          % [ASSUMED] gate-oxide damage modelled as a 10 ohm gate-emitter leakage path
  f = {'IGBT', 'Gate-oxide degradation: 10 ohm gate-emitter leakage'};
 case 'igbt_vth_shift'
  p.Vth_V = 7.6;                % [ASSUMED] threshold drift (oxide charge trapping) beyond the slide 8 range
  f = {'IGBT', 'Threshold drift: VGE(th) model input 6.3 V -> 7.6 V'};
 case 'igbt_diode_degraded'
  p.diodeVf_V = 1.1;            % [ASSUMED] degraded freewheel diode, knee outside slide 5 range
  p.diodeRon_Ohm = (2.30-0.5)/1500;  % slope kept from the healthy device
  f = {'IGBT', 'Freewheel diode degraded: knee 0.5 V -> 1.1 V'};
 case 'driver_weak_supply'
  p.driverVHigh_V = 12;         % [ASSUMED] driver positive rail sagged; the device model still uses gateOn_V = 15 V data
  f = {'DRIVER', 'Gate-driver supply sag: +15 V output -> +12 V'};
 case 'driver_desat_dead'
  p.desatThreshold_V = Inf;     % [ASSUMED] driver DESAT comparator never fires
  f = {'DRIVER', 'Gate-driver DESAT protection dead: comparator never trips'};
 otherwise
  error('Unknown fault id %s', id);
end
p.fault = struct('id', id, 'component', f{1}, 'description', f{2}, 'severity', 'ASSUMED', ...
 'purpose', 'tester demonstration; not a model of a measured failed module');
p.device = [p.device ' WITH INJECTED FAULT: ' f{2}];
p.provenance = [p.provenance '; INJECTED FAULT (' id '), severity ASSUMED'];
end

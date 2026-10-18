function p = parameters
% Assumed device: no manufacturer, part number or certified ratings.
p.schema='testcell.assumed_device.v1';
p.provenance='Illustrative engineering parameters; not a locomotive module datasheet';
p.gateOn_V=15; p.gateOff_V=-15; % Wabtec slides 5 and 8
p.Vth_V=6; p.VceCalibration_V=2; p.IcCalibration_A=20;
p.leakageCalibration_A=10e-6; p.leakageCalibrationVoltage_V=100;
p.Tcal_C=25; p.Tsecond_C=125; p.VceSecond_V=2.4; p.leakageSecond_A=500e-6;
p.Cies_F=5e-9; p.Cres_F=0.3e-9; p.Coes_F=0.8e-9;
p.transit_s=0.2e-6; p.Rc_Ohm=0.005; p.Re_Ohm=0.005; p.RgInternal_Ohm=0.5;
p.RgateExternal_Ohm=4.7; p.RdriverOn_Ohm=2; p.RdriverOff_Ohm=2;
p.driverDelay_s=50e-9;
p.bus_V=48; p.loadR_Ohm=2; p.loadL_H=1e-3;
p.strayL_H=100e-9; p.strayR_Ohm=0.01;
p.diodeVf_V=0.8; p.diodeRon_Ohm=0.01; p.diodeGoff_S=1e-8;
p.diodeC_F=0.2e-9;
p.pulseEdges_s=[50 300 400 500]*1e-6; % 100 us freewheel gap resolves assumed stored charge
p.dynamicStop_s=1.5e-3; p.dynamicMaxStep_s=0.2e-6;
p.relTol=1e-6; p.absTol=1e-9; p.seed=2026;
p.protectionReference_s=10e-6; % slide reference, not acceptance/certification
p.thermal=struct('Cj_J_K',2,'Cc_J_K',20,'Rjc_K_W',0.2,'Rca_K_W',1,'ambient_K',298.15, ...
 'provenance','Assumed equivalent Cauer network; no physical dimensions or module fit');
p.hardwareDecision='INCONCLUSIVE';
end



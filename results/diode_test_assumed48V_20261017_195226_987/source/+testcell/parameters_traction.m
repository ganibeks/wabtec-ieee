function p = parameters_traction
% Locomotive-class representative device: Mitsubishi CM1500HC-66XB (3.3 kV / 1500 A HVIGBT).
% REPRESENTATIVE traction module, NOT a confirmed Wabtec part. No Wabtec ratings or limits.
% Source: references/cm1500hc-66xb_e.pdf, Dec. 2025 (HVM-1147-B),
% SHA256 19E5A4E07AEEC89EC53FFBD25C2F17FD507500B833C83F14C053EAB69EFA6E44.
% Tags: [DS] datasheet typical/max value at the stated condition; [ASSUMED] not in datasheet.
% Use ONLY with kind 'dynamic_rl'. 'dynamic_r' with this 0.01 ohm load would draw ~180 kA.
p.schema='testcell.traction_device.v1';
p.provenance=['Mitsubishi CM1500HC-66XB datasheet HVM-1147-B (Dec 2025) typical values where available; ' ...
 'representative traction module, not a confirmed Wabtec part; fixture/load values assumed'];
p.device='Mitsubishi CM1500HC-66XB (representative, not a confirmed Wabtec part)';
p.allowedKinds={'dynamic_rl'};
p.gateOn_V=15; p.gateOff_V=-15;          % [DS] VGE = +/-15 V test condition; also Wabtec slides 5/8
p.Vth_V=6.3;                              % [DS] VGE(th) typ, VCE=10 V, IC=150 mA, 25 C
% Calibration history:
%  attempt 1: Tmeas 25 C with ICES 25 C MAX (3.0 mA) vs 125 C typ -> negative energy gap (traction_rl_01.log)
%  attempt 2: Tmeas 125 C / 150 C. WRONG: the block measures ALL main-tab values (incl. Vth) at Tmeas, so the
%             25 C datasheet Vth was applied at 125 C; static check gave VGE(th)=7.80 V at 25 C (static_checks_traction_01.log)
%  attempt 3 (this): Tmeas 25 C (datasheet Vth and VCEsat typ are 25 C values), Tmeas2 125 C.
p.IcCalibration_A=1500;                   % [DS] VCEsat condition IC=1500 A, VGE=15 V
p.Tcal_C=25;  p.VceCalibration_V=2.60;    % [DS] VCEsat typ at 25 C
p.Tsecond_C=125; p.VceSecond_V=3.20;      % [DS] VCEsat typ at 125 C
p.leakageCalibrationVoltage_V=3300;       % [DS] ICES condition VCE=3300 V, VGE=0
p.leakageSecond_A=4.0e-3;                 % [DS] ICES typ at 125 C
% [DERIVED] ICES at 25 C: datasheet gives only a max (3.0 mA). Back-extrapolate the 125 C typ with the energy gap
% implied by the datasheet typ points 4.0 mA (125 C) and 26 mA (150 C), Ices ~ T^3 exp(-EG/kT) (block XTI = 3).
kB=8.617333e-5; T1=25+273.15; T2=125+273.15; T3=150+273.15;
p.leakageEG_eV=kB*log((26.0e-3/4.0e-3)/(T3/T2)^3)/(1/T2-1/T3);
p.leakageCalibration_A=p.leakageSecond_A/((T2/T1)^3*exp(p.leakageEG_eV/kB*(1/T1-1/T2)));
p.datasheetTypical150C=struct('VCEsat_V',3.30,'ICES_A',26.0e-3);  % [DS] typ at 150 C, used as independent predictions
p.Cies_F=164e-9; p.Coes_F=11e-9; p.Cres_F=1.4e-9; % [DS] typ, VCE=10 V, VGE=0, 100 kHz, 25 C
p.transit_s=0.2e-6;                       % [ASSUMED] stored-charge transit time (tail); not in datasheet
p.Rc_Ohm=0.045e-3; p.Re_Ohm=0.045e-3;     % [DS] RCC'+EE' = 0.09 mOhm typ, split equally [ASSUMED split]
p.RgInternal_Ohm=0.5;                     % [ASSUMED] internal gate resistance not in datasheet
p.RgateExternal_Ohm=0;                    % [ASSUMED] asymmetric gate resistors carried by driver Ron/Roff below
p.RdriverOn_Ohm=2.0; p.RdriverOff_Ohm=27; % [DS] RG(on)=2.0 ohm, RG(off)=27 ohm switching test condition
p.driverDelay_s=50e-9;                    % [ASSUMED] same as 48 V baseline
p.bus_V=1800;                             % [DS] VCC = 1800 V switching test condition
p.strayL_H=100e-9;                        % [DS] Ls = 100 nH switching test condition
p.strayR_Ohm=1e-4;                        % [ASSUMED] busbar/fixture series resistance
p.loadL_H=300e-6;                         % [ASSUMED] sized so IL ~1.5 kA at the 2nd turn-on (datasheet IC)
p.loadR_Ohm=0.01;                         % [ASSUMED] load winding resistance
p.diodeVf_V=1.0;                          % [ASSUMED] split of VEC; Vf+Ron*1500 A = 2.30 V [DS VEC typ, 25 C]
p.diodeRon_Ohm=(2.30-1.0)/1500;
p.diodeGoff_S=1e-8;                       % [ASSUMED]
p.diodeC_F=11e-9;                         % [ASSUMED] equal to Coes of an identical module in the freewheel position
p.pulseEdges_s=[50 300 400 500]*1e-6;     % same double-pulse timing as the validated 48 V run
p.dynamicStop_s=1.5e-3; p.dynamicMaxStep_s=0.2e-6;
p.relTol=1e-6; p.absTol=1e-9; p.seed=2026;
% ode23t hit min-step difficulty at the first turn-on with the 25 C-referenced leakage (traction_rl_03.log);
% diag_traction_01.log: ode15s runs without warnings and matches ode23t to 0.2 % at 65 us.
p.dynamicSolver='ode15s';
p.protectionReference_s=10e-6;            % slide reference; datasheet tpSC = 10 us at VCC<=2500 V (not modelled)
% Manufacturer min/max limits (datasheet HVM-1147-B) for the representative device.
% These are NOT Wabtec acceptance limits; hardware decision stays INCONCLUSIVE.
p.datasheetLimits=struct( ...
 'VGEth_min_V',5.80,'VGEth_max_V',6.80,'VGEth_VCE_V',10,'VGEth_IC_A',0.150, ...  % VGE(th), Tj=25 C
 'ICES_max_A',3.0e-3,'ICES_VCE_V',3300, ...                                       % ICES, VGE=0, Tj=25 C
 'VCEsat_max150_V',3.70,'VCEsat_IC_A',1500, ...                                  % VCEsat, VGE=15 V, Tj=150 C
 'source','Mitsubishi CM1500HC-66XB datasheet HVM-1147-B (Dec 2025) min/max; representative device, not Wabtec acceptance');
p.modelLimitations={'Freewheel diode has NO reverse recovery (datasheet Qrr 880 uC, Erec 1.05 J at 25 C not modelled): turn-on overshoot and Eon underestimated', ...
 'transit_s (tail current) is ASSUMED', 'Fixed 25 C device temperature; no self-heating', 'Ideal sensors and source'};
p.hardwareDecision='INCONCLUSIVE';
end

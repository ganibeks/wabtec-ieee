function assert_no_solver_warnings(out)
% Fail conservatively rather than accepting degraded numerical accuracy.
d=out.SimulationMetadata.ExecutionInfo.WarningDiagnostics;
assert(isempty(d),'testcell:SolverDiagnostics','Simulation produced warnings; inspect diagnostics before validation.');
end

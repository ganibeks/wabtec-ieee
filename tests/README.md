# Validation guard regressions

Run from the project root:

```powershell
& 'C:\Users\ganib\anaconda3\python.exe' -m unittest discover -s tests -p 'test_*verdict.py' -v
& 'C:\Program Files\MATLAB\R2026b\bin\matlab.exe' -batch "addpath('tests'); verify_dynamic_records;"
```

The MATLAB test reads preserved raw and fine-step RL records from
`dynamic_20261017_165933_696` and `dynamic_20261017_195453_347`. It checks
that complete records retain their numerical metrics and rejects truncated
records, a missing channel segment, an insufficient configured duration,
and an unresolved turn-off clearance. Corrupted inputs exist only in memory.
The raw-record guard requires solver-resolution data through the configured
stop time; decimated display CSVs are not its input format.

Python tests cover missing, unbounded, nonfinite, failed, and complete checks,
including omission of required slide checks. The Streamlit integration test
temporarily withholds DESAT evidence to verify that a missing result remains
visible and prevents PASS, regardless of newly generated DESAT runs.

These are software regression tests using saved simulation evidence. They
do not execute new electrical simulations, modify the saved models, or
establish hardware health. Hardware decisions remain INCONCLUSIVE for
simulated and demonstration results.

"""Discover simulation result folders and classify them (selectable or excluded, with reason).

Rules (CLAUDE.md): never modify results/; a dataset is presented as validated only if its
validation JSON says PASS; rl_diagnostic is SUPERSEDED; electrothermal is NOT_VALIDATED.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

# Canonical reference runs documented in PROJECT_STATUS.md.
REF_RL = "dynamic_20261017_165933_696"
REF_R = "dynamic_20261017_165503_678"
REF_BASELINE = "20261017_163035_757"
REF_STATIC = "static25_20261017_165838_504"

# Runs kept on disk as evidence but never presented as valid.
SUPERSEDED = {
    "dynamic_20261017_182654_290": "Traction parameterization attempt 2 applied the 25 C datasheet Vth at Tmeas = 125 C "
                                   "(static check: VGE(th) 7.80 V vs datasheet 5.8-6.8 V); superseded by the 25 C-referenced run",
    "static_checks_20261017_193416_029": "Static checks of traction parameterization attempt 2 (Vth referenced at 125 C); "
                                         "found the VGE(th) error; superseded",
    "dynamic_20261017_194219_720": "Traction attempt 4: freewheel diode knee 1.0 V contradicted slide 5 (0.2-0.8 V); "
                                   "superseded by the run with knee 0.5 V",
    "diode_test_traction_20261017_195315_476": "Diode test with knee 1.0 V (1.000 V, outside slide 5 0.2-0.8 V); "
                                               "parameters changed to knee 0.5 V",
    "dynamic_20261018_001722_232": "CONTAMINATED: two parallel MATLAB sessions claimed the same folder; parameters.json "
                                   "is igbt_gate_leak but the simulation ran igbt_vth_shift (p saved in dynamic_rl_raw.mat). "
                                   "new_run.m fixed to claim folders atomically; both faults re-run",
}

DYN_COLUMNS = ["time_s", "Vge_V", "Vce_V", "Ic_A", "Ig_A", "IL_A", "Id_A", "Ibus_A", "Vswitch_V"]


@dataclass
class Dataset:
    id: str
    kind: str                 # dynamic_rl | dynamic_r | baseline | static
    label: str
    folder: Path
    status: str               # PASS | PARTIAL | SUPERSEDED | NOT_VALIDATED | FAILED | INCOMPLETE
    selectable: bool
    reason: str = ""
    csv: Path | None = None
    validation: Path | None = None
    params: dict = field(default_factory=dict)
    edges_s: list = field(default_factory=list)
    edges_source: str = ""
    stop_s: float | None = None
    model_file: Path | None = None
    provenance: str = "SIMULATED"
    analyzer: str = "current"   # which analyze_dynamic.m version produced the validation JSON

    def __repr__(self):
        return f"Dataset({self.id!r}, {self.status}, selectable={self.selectable})"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _edges_from_source(folder: Path) -> list:
    """Pulse edges for runs whose parameters.json predates p.pulseEdges_s (read from the source snapshot)."""
    src = folder / "source" / "+testcell" / "build_rig.m"
    if not src.exists():
        return []
    m = re.search(r"times=\[0 ([^\]]*?) p\.dynamicStop_s\]", src.read_text(encoding="utf-8-sig"))
    if not m or "pulseEdges" in m.group(1):
        return []
    return [float(v) for v in m.group(1).split()]


def _dynamic(folder: Path, kind: str, ds_id: str, label: str) -> Dataset | None:
    csv = folder / f"{kind}.csv"
    vjson = folder / f"{kind}_validation.json"
    pjson = folder / "parameters.json"
    if not pjson.exists():
        return None
    params = _json(pjson)
    edges = params.get("pulseEdges_s") or []
    edges_source = "parameters.json pulseEdges_s"
    if not edges:
        edges = _edges_from_source(folder)
        edges_source = "source/+testcell/build_rig.m snapshot (parameters.json predates pulseEdges_s)"
    ds = Dataset(ds_id, kind, label, folder, "INCOMPLETE", False, csv=csv if csv.exists() else None,
                 validation=vjson if vjson.exists() else None, params=params, edges_s=list(edges),
                 edges_source=edges_source, stop_s=params.get("dynamicStop_s"),
                 model_file=folder / f"tc_{kind}.slx")
    snap = folder / "source" / "+testcell" / "analyze_dynamic.m"
    if snap.exists() and "edges=[50 300 350 450]*1e-6" in snap.read_text(encoding="utf-8-sig"):
        ds.analyzer = "legacy_v0"
    if ds.csv is None or ds.validation is None:
        ds.reason = "Run did not complete: no CSV and/or validation JSON in folder"
        return ds
    v = _json(vjson)
    status = v.get("status", "UNKNOWN")
    # A PASS only counts with evidence that the half-step convergence check ran and passed
    # (older run_dynamic.m wrote status PASS before that check).
    conv = v.get("half_step_event_energy_relative_errors")
    conv = conv if isinstance(conv, list) else [conv] if conv is not None else []
    converged = bool(conv) and all(c is not None and c < 0.03 for c in conv)
    if status == "PASS" and not converged:
        status = "UNCONFIRMED"
    if folder.name in SUPERSEDED:
        ds.status, ds.selectable, ds.reason = "SUPERSEDED", False, SUPERSEDED[folder.name]
        return ds
    ds.status = status
    ds.selectable = status == "PASS" and len(ds.edges_s) == 4
    if status == "UNCONFIRMED":
        ds.reason = "Validation JSON says PASS but has no passed half-step convergence record"
    elif status != "PASS":
        ds.reason = f"Validation JSON status is {status}"
    elif not ds.selectable:
        ds.reason = "Pulse edges could not be recovered"
    return ds


def discover(root: Path | None = None) -> list[Dataset]:
    res = (Path(root) / "results") if root else RESULTS
    out: list[Dataset] = []

    # --- 48 V reference runs (assumed device) ---
    rl = _dynamic(res / REF_RL, "dynamic_rl", "dynamic_rl", "48 V RL double pulse (assumed device)")
    if rl:
        out.append(rl)
    r = _dynamic(res / REF_R, "dynamic_r", "dynamic_r", "48 V resistive switching (assumed device)")
    if r:
        out.append(r)

    b = res / REF_BASELINE
    if (b / "validation.json").exists():
        st = _json(b / "validation.json").get("status", "UNKNOWN")
        out.append(Dataset("baseline", "baseline", "12 V / 100 ohm ideal-switch baseline", b, st, st == "PASS",
                           "" if st == "PASS" else f"Validation status {st}",
                           csv=b / "baseline_waveforms.csv", validation=b / "validation.json",
                           params={"bus_V": 12.0, "loadR_Ohm": 100.0, "gateOn_V": 15.0, "gateOff_V": -15.0,
                                   "Vth_V": 6.0, "Vf_V": 0.8, "Ron_Ohm": 0.1, "Goff_S": 1e-8,
                                   "schema": "build_baseline.m (no parameter struct)",
                                   "provenance": "Illustrative values hard-coded in build_baseline.m"},
                           edges_s=[1e-3, 2e-3, 3e-3, 4e-3, 5e-3],
                           edges_source="build_baseline.m Pulse Generator: period 2 ms, 50 %, phase delay 1 ms",
                           stop_s=6e-3, model_file=b / "igbt_baseline.slx"))

    s = res / REF_STATIC
    if (s / "validation.json").exists():
        v = _json(s / "validation.json")
        st = v.get("status", "UNKNOWN")
        # PARTIAL = numerical checks PASS for the completed 25 C cases; temperature matrix incomplete.
        ok = st == "PASS" or (st == "PARTIAL" and str(v.get("numerical_checks", "")).startswith("PASS"))
        out.append(Dataset("static", "static", "Static curve tracer, 25 C (completed points)", s, st, ok,
                           "Partial: 25 C only; 75 C blocked (solver stall)" if st == "PARTIAL" else "",
                           csv=s / "static_curves.csv", validation=s / "validation.json",
                           params=_json(s / "parameters.json") if (s / "parameters.json").exists() else {},
                           model_file=s / "tc_static_v.slx"))

    # --- Excluded by rule ---
    if (res / REF_R / "rl_diagnostic.csv").exists():
        out.append(Dataset("rl_diagnostic", "dynamic_rl", "Superseded 50 us-gap RL diagnostic", res / REF_R,
                           "SUPERSEDED", False, "Failed commutation check; superseded by " + REF_RL,
                           csv=res / REF_R / "rl_diagnostic.csv"))
    for et in sorted(res.glob("electrothermal_*")):
        review = et / "validation_review.json"
        st = _json(review).get("review_status", "NOT_VALIDATED") if review.exists() else "NOT_VALIDATED"
        out.append(Dataset("electrothermal" if et.name.startswith("electrothermal_20261017_170833") else f"electrothermal@{et.name}",
                           "dynamic_rl", "Electrothermal RL run", et, st, False,
                           "validation_review.json: device kept its internal thermal network; Tj label invalid",
                           csv=et / "electrothermal_switching.csv"))

    # --- Additional dynamic runs (traction, dashboard requests) ---
    known = {REF_RL, REF_R}
    traction_seen = False
    faults_seen: set[str] = set()
    for folder in sorted(res.glob("dynamic_*"), reverse=True):
        if folder.name in known or not (folder / "parameters.json").exists():
            continue
        params = _json(folder / "parameters.json")
        traction = params.get("schema") == "testcell.traction_device.v1"
        fault = params.get("fault") if str(params.get("schema", "")).startswith("testcell.traction_fault.") else None
        for kind in ("dynamic_rl", "dynamic_r"):
            if not (folder / f"tc_{kind}.slx").exists() and not (folder / f"{kind}.csv").exists():
                continue
            if fault and kind == "dynamic_rl":
                # Injected-fault variant of the traction device (parameters_traction_fault.m); newest PASS run per fault.
                fid = f"fault:{fault.get('id')}"
                ds = _dynamic(folder, kind, fid, f"FAULT ({fault.get('component')}): {fault.get('description')} "
                                                 f"[injected, severity ASSUMED]")
                if ds:
                    ds.provenance = "SIMULATED, INJECTED FAULT (severity ASSUMED)"
                    if not ds.selectable or fid in faults_seen:
                        ds.id = f"{fid}@{folder.name}"
                        ds.selectable = False
                        ds.reason = ds.reason or "Older run of the same injected fault"
                    else:
                        faults_seen.add(fid)
                    out.append(ds)
                continue
            if traction and kind == "dynamic_rl" and not traction_seen:
                ds = _dynamic(folder, kind, "traction_rl", "1.8 kV / 1.5 kA RL double pulse - CM1500HC-66XB (representative)")
                if ds and ds.selectable:
                    traction_seen = True
                elif ds:
                    ds.id = f"traction_rl@{folder.name}"
            else:
                tag = "traction" if traction else "run"
                ds = _dynamic(folder, kind, f"{tag}:{kind}@{folder.name}", f"{kind} run {folder.name}")
            if ds:
                out.append(ds)
    return out


def latest_static_checks(schema: str, root: Path | None = None) -> tuple[Path, dict] | None:
    """Newest results/static_checks_* run (testcell.run_static_checks) for a parameter schema."""
    return latest_run("static_checks_*", schema, root)


def latest_diode_test(schema: str, root: Path | None = None) -> tuple[Path, dict] | None:
    """Newest results/diode_test_* run (testcell.run_diode_test) for a parameter schema."""
    return latest_run("diode_test_*", schema, root)


def latest_run(pattern: str, schema: str, root: Path | None = None) -> tuple[Path, dict] | None:
    """Newest non-superseded results folder matching `pattern` whose parameters.json has `schema`.
    Only PASS or PARTIAL runs with a validation.json are returned; PARTIAL keeps its error list.
    Folder names end in a timestamp, so sort on that (prefixes differ, e.g. diode_test_traction_ / _assumed48V_)."""
    res = (Path(root) / "results") if root else RESULTS
    stamp = lambda f: re.search(r"(\d{8}_\d{6}_\d{3})$", f.name).group(1) if re.search(r"\d{8}_\d{6}_\d{3}$", f.name) else ""
    for folder in sorted(res.glob(pattern), key=stamp, reverse=True):
        v, pj = folder / "validation.json", folder / "parameters.json"
        if folder.name in SUPERSEDED or not (v.exists() and pj.exists()) or _json(pj).get("schema") != schema:
            continue
        data = _json(v)
        if data.get("status") in ("PASS", "PARTIAL"):
            return folder, data
    return None


def is_traction(ds: Dataset) -> bool:
    """Locomotive-class device (parameters_traction.m), the device the Wabtec slide checks apply to."""
    """Healthy device or one of its injected-fault variants (parameters_traction_fault.m)."""
    return str(ds.params.get("schema", "")).startswith(("testcell.traction_device.", "testcell.traction_fault."))


def get(ds_id: str, root: Path | None = None) -> Dataset:
    for d in discover(root):
        if d.id == ds_id:
            return d
    raise KeyError(ds_id)


def selectable(root: Path | None = None) -> list[Dataset]:
    return [d for d in discover(root) if d.selectable]

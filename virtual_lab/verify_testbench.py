"""Headless verification of the virtual test bench against the 48 V RL CSV.

Usage (project root):  python virtual_lab/verify_testbench.py
Rebuilds testbench_standalone.html, opens it in headless Chromium, and checks:
  * every meter (window.lab.getReadings) vs numpy.interp of the CSV: rel err < 1e-4 or abs < 1e-6
  * the displayed DMM text agrees with that value to its 4 displayed significant digits
  * DERIVED tiles (P, E_C, V_AK, KCL) vs numpy recomputation
  * expected lamp states at named times; the Vce peak at 400.06 us
  * all 4 scope cursors at the same x pixel inside each scope (2x2 grid; API and actual canvas pixels)
  * every bundled dataset loads without JS errors
Exit code 0 only if every row passes. Screenshots go to virtual_lab/verify_out/.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright  # noqa: E402

from virtual_lab import build_standalone, datasets as D  # noqa: E402

OUT = HERE / "verify_out"
TIMES_US = [40, 200, 300.2, 310, 350, 400.06, 505, 1400]
CH = ["Vge", "Vce", "Ic", "Ig", "IL", "Id", "Ibus", "Vswitch"]
PFX = {"f": 1e-15, "p": 1e-12, "n": 1e-9, "µ": 1e-6, "m": 1e-3, "": 1.0, "k": 1e3, "M": 1e6, "G": 1e9}
rows: list[tuple[str, str, str, str, bool]] = []


def check(name, detail, expected, got, ok):
    rows.append((name, detail, str(expected), str(got), bool(ok)))


def close(a, b):
    return abs(a - b) < 1e-6 or abs(a - b) / max(abs(b), 1e-300) < 1e-4


def parse_si(s: str):
    m = re.match(r"^\s*(-?[\d.]+)\s*([fpnµmkMG]?)([A-Za-zΩ]+)\s*$", s)
    if not m:
        return None, 0
    num = m.group(1)
    decimals = len(num.split(".")[1]) if "." in num else 0
    scale = PFX[m.group(2)]
    return float(num) * scale, 0.5 * 10 ** (-decimals) * scale  # value, display half-step


def main() -> int:
    OUT.mkdir(exist_ok=True)
    html = build_standalone.main()
    rl = D.get("dynamic_rl")
    d = pd.read_csv(rl.csv)
    t = d["time_s"].to_numpy(float)
    csv = {c: d[f"{c}_V" if c.startswith("V") else f"{c}_A"].to_numpy(float) for c in CH}
    P = csv["Vce"] * csv["Ic"]
    E = np.concatenate([[0.0], np.cumsum(np.diff(t) * (P[1:] + P[:-1]) / 2)])
    bus = float(rl.params["bus_V"])

    errors: list[str] = []
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        pg = br.new_page(viewport={"width": 1600, "height": 2400}, device_scale_factor=1)
        pg.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        pg.goto(html.as_uri())
        pg.wait_for_function("window.lab && window.lab.current()")
        check("load", "default dataset", "dynamic_rl", pg.evaluate("lab.current()"), pg.evaluate("lab.current()") == "dynamic_rl")
        thr = None

        for tu in TIMES_US:
            ts = tu * 1e-6
            pg.evaluate(f"lab.seek({ts!r})")
            pg.wait_for_timeout(60)
            r = pg.evaluate("lab.getReadings()")
            s = pg.evaluate("lab.getStates()")
            shown = pg.evaluate("lab.getDisplayed()")
            worst = []
            for c in CH:
                ref = float(np.interp(ts, t, csv[c]))
                ok = close(r[c], ref)
                val, half = parse_si(shown[c])
                disp_ok = val is not None and abs(val - r[c]) <= half * 1.0001 + 1e-15
                worst.append(ok and disp_ok)
                if not (ok and disp_ok):
                    check(f"t={tu} us meter {c}", "vs numpy.interp / displayed", f"{ref:.9g}", f"{r[c]:.9g} [{shown[c]}]", False)
            refP = float(np.interp(ts, t, csv["Vce"])) * float(np.interp(ts, t, csv["Ic"]))
            refE = float(np.interp(ts, t, E))
            refVAK = float(np.interp(ts, t, csv["Vswitch"])) - bus
            refK = float(np.interp(ts, t, csv["IL"]) - np.interp(ts, t, csv["Ic"]) - np.interp(ts, t, csv["Id"]))
            der_ok = close(r["P"], refP) and close(r["E"], refE) and close(r["VAK"], refVAK) and abs(r["KCL"] - refK) < 1e-5
            check(f"t={tu} us", "8 meters vs CSV interp (rel<1e-4 | abs<1e-6) + DMM text",
                  "all match", "all match" if all(worst) else "MISMATCH", all(worst))
            check(f"t={tu} us", "DERIVED P, E_C, V_AK, KCL vs numpy", f"P={refP:.6g} E={refE:.6g}",
                  f"P={r['P']:.6g} E={r['E']:.6g} VAK={r['VAK']:.4g} KCL={r['KCL']:.2e}", der_ok)
            if tu == 200:
                check("t=200 us", "IGBT / diode state", "CONDUCTING-SAT / BLOCKING", f"{s['igbt']} / {s['diode']}",
                      s["igbt"] == "CONDUCTING-SAT" and s["diode"] == "BLOCKING")
            if tu == 310:
                check("t=310 us", "IGBT / diode state", "TAIL CURRENT / FREEWHEELING", f"{s['igbt']} / {s['diode']}",
                      s["igbt"] == "TAIL CURRENT" and s["diode"] == "FREEWHEELING")
            if tu == 350:
                thr = pg.evaluate("lab.getView() && window.__LAB_PAYLOAD__.datasets[0].thresholds.conduct_A")
                check("t=350 us", "diode state; Ic ~ 0 (|Ic| <= conduct_A)", f"FREEWHEELING; |Ic|<={thr:.4g} A",
                      f"{s['diode']}; Ic={r['Ic']:.4g} A ({s['igbt']})",
                      s["diode"] == "FREEWHEELING" and abs(r["Ic"]) <= thr and s["igbt"] == "BLOCKING")
            if tu == 400.06:
                ipk = int(np.argmax(csv["Vce"]))
                pg.evaluate(f"lab.seek({float(t[ipk])!r})")
                pk = pg.evaluate("lab.getReadings()")["Vce"]
                check("t=400.06 us", f"peak Vce at exact solver time {t[ipk]*1e6:.5f} us",
                      f"{csv['Vce'][ipk]:.4f} V (51.14)", f"{pk:.4f} V",
                      abs(pk - csv["Vce"][ipk]) < 1e-4 * abs(csv["Vce"][ipk]) and round(pk, 2) == 51.14)
                pg.evaluate(f"lab.seek({ts!r})")
                pg.wait_for_timeout(60)
            # all four scope cursors at the same x inside their own scope (2x2 grid: page x differs by column)
            cx = pg.evaluate("lab.getCursorX()")
            xs = [c["localX"] for c in cx]
            px = pg.evaluate("""() => [...document.querySelectorAll('#scopes canvas')].map((cv, i) => {
                const x = Math.round(lab.getCursorX()[i].localX * (window.devicePixelRatio||1));
                const g = cv.getContext('2d'); let hits = 0;
                for (const dx of [-1, 0, 1]) { const d = g.getImageData(x + dx, 0, 1, cv.height).data;
                  for (let k = 0; k < d.length; k += 4) if (d[k] > 180 && d[k+1] < 60 && d[k+2] < 70) hits++; }
                return hits; })""")
            same = len(cx) == 4 and max(xs) - min(xs) < 0.5 and all(h > 40 for h in px)
            check(f"t={tu} us", "4 scope cursors same x (API) + cursor pixels present",
                  "spread < 0.5 px; red cursor column in all 4", f"x={xs[0]:.2f} spread={max(xs)-min(xs):.3f}px pixels={px}", same)
            if tu in (200, 310, 400.06):
                pg.screenshot(path=str(OUT / f"rl_t{str(tu).replace('.', '_')}us.png"), full_page=True)

        # zoomed views keep the envelope and cursor aligned
        pg.evaluate("lab.seek(400.06e-6); lab.setWindow('5')")
        pg.wait_for_timeout(100)
        cx = [c["localX"] for c in pg.evaluate("lab.getCursorX()")]
        check("zoom 5 us @400.06", "cursor alignment", "spread < 0.5 px", f"{max(cx)-min(cx):.3f}", max(cx) - min(cx) < 0.5)
        pg.screenshot(path=str(OUT / "rl_zoom5us_400us.png"), full_page=True)

        # play/pause actually advances simulated time
        pg.evaluate("lab.seek(0); lab.play()")
        pg.wait_for_timeout(1200)
        v = pg.evaluate("lab.getView()")
        pg.evaluate("lab.pause()")
        check("play 1.2 s wall", "SIM t advances; slow-motion factor reported", "t > 0", f"t={v['t']*1e6:.4f} us slow={v['slow']:.3g}", v["t"] > 0)

        # every dataset loads cleanly
        for ds_id in pg.evaluate("lab.datasets()"):
            n0 = len(errors)
            pg.evaluate(f"lab.select({ds_id!r})")
            pg.wait_for_timeout(300)
            if ds_id != "static":
                pg.evaluate("lab.seek(window.__LAB_PAYLOAD__.datasets.find(d=>d.meta.id===lab.current()).edges[2].t + 2e-6)")
                pg.wait_for_timeout(100)
            pg.screenshot(path=str(OUT / f"ds_{ds_id}.png"), full_page=True)
            check(f"dataset {ds_id}", "loads and renders without JS errors", "0 errors", f"{len(errors) - n0} errors", len(errors) == n0)
        br.close()

    check("console", "JS errors over whole session", "0", str(len(errors)), not errors)
    for e in errors:
        print("  JS:", e)
    w = [max(len(r[i]) for r in rows) for i in range(4)]
    print()
    print(f"{'CHECK':<{w[0]}}  {'DETAIL':<{w[1]}}  {'EXPECTED':<{w[2]}}  {'GOT':<{w[3]}}  RESULT")
    for r in rows:
        print(f"{r[0]:<{w[0]}}  {r[1]:<{w[1]}}  {r[2]:<{w[2]}}  {r[3]:<{w[3]}}  {'PASS' if r[4] else 'FAIL'}")
    npass = sum(r[4] for r in rows)
    print(f"\n{npass}/{len(rows)} checks PASS -> {'VERIFICATION PASS' if npass == len(rows) else 'VERIFICATION FAIL'}")
    print(f"Screenshots: {OUT}")
    return 0 if npass == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())

"""Generates igbt_tester_block_diagram_v5.svg: STM32-based IGBT tester with one DUT and gate driver, double-pulse load
(inductor with freewheel diode), hard-wired safety relay through contactor K1 and a discharge relay across the DC link.
Run:  python make_block_diagram_v5.py
"""
from pathlib import Path

OUT = Path(__file__).with_name("igbt_tester_block_diagram_v5.svg")
E = []          # svg elements
add = E.append


def sub(main, s):
    """Text with a subscript, original style: V<sub>GE</sub>."""
    return f'{main}<tspan font-size="10" dy="3">{s}</tspan><tspan dy="-3"></tspan>'


def _style(extra):
    """Class CSS overrides presentation attributes, so font-size/weight go into style."""
    import re
    css = "".join(f"{k}:{v}{'px' if k == 'font-size' else ''};" for k, v in re.findall(r' (font-size|font-weight)="([^"]+)"', extra))
    rest = re.sub(r' (font-size|font-weight)="[^"]+"', "", extra)
    return rest + (f' style="{css}"' if css else "")


def text(x, y, s, cls="t", anchor=None, extra=""):
    extra = _style(extra)
    a = f' text-anchor="{anchor}"' if anchor else ""
    add(f'<text class="{cls}" x="{x}" y="{y}"{a}{extra}>{s}</text>')


def rect(x, y, w, h, cls="blk"):
    add(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}"/>')


def line(x1, y1, x2, y2, cls="ctl", end=False, start=False, extra=""):
    m = (' marker-end="url(#arr)"' if end else "") + (' marker-start="url(#arr)"' if start else "")
    add(f'<line class="{cls}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"{m}{extra}/>')


def poly(pts, cls="ctl", end=False, extra=""):
    m = ' marker-end="url(#arr)"' if end else ""
    add(f'<polyline class="{cls}" points="{" ".join(f"{x},{y}" for x, y in pts)}"{m}{extra}/>')


def path(d, cls="ctl", end=False, extra=""):
    m = ' marker-end="url(#arr)"' if end else ""
    add(f'<path class="{cls}" d="{d}"{m}{extra}/>')


def dot(x, y, r=3):
    add(f'<circle class="dot" cx="{x}" cy="{y}" r="{r}"/>')


def term(x, y, r=3.5):
    add(f'<circle class="term" cx="{x}" cy="{y}" r="{r}"/>')


def num(x, y, n, r=9, fs=12):
    add(f'<circle class="num" cx="{x}" cy="{y}" r="{r}"/>'
        f'<text class="numt" x="{x}" y="{y + 4}" text-anchor="middle" style="font-size:{fs}px">{n}</text>')


def vhop(x, y_from, y_to, hops, cls="ctl", end=False, extra=""):
    """Vertical wire from y_from to y_to with 6 px hop arcs at the given y crossings."""
    sgn = 1 if y_to > y_from else -1
    d = f"M{x},{y_from}"
    for h in sorted(hops, reverse=(sgn < 0)):
        d += f" L{x},{h - 6 * sgn} A6,6 0 0 {1 if sgn > 0 else 0} {x},{h + 6 * sgn}"
    d += f" L{x},{y_to}"
    path(d, cls, end, extra)


def hhop(y, x_from, x_to, hops, cls="ctl", end=False, extra=""):
    """Horizontal wire with 6 px hop arcs at the given x crossings."""
    sgn = 1 if x_to > x_from else -1
    d = f"M{x_from},{y}"
    for h in sorted(hops, reverse=(sgn < 0)):
        d += f" L{h - 6 * sgn},{y} A6,6 0 0 {1 if sgn > 0 else 0} {h + 6 * sgn},{y}"
    d += f" L{x_to},{y}"
    path(d, cls, end, extra)


# ---------------------------------------------------------------- domain labels
text(785, 24, "DOMAIN A", "tb", "end")
text(815, 24, "DOMAIN B", "tb")

# ---------------------------------------------------------------- supplies (domain A)
line(4, 85, 60, 85, extra=' stroke-width="1.6"')
text(6, 76, "~230 V", "ts")
rect(60, 55, 190, 60)
text(155, 90, "POWER SUPPLY", "tb", "middle")
line(250, 85, 720, 85, end=True, extra=' stroke-width="1.6"')
text(270, 78, "+24 V")
line(145, 115, 145, 145, extra=' stroke-width="1.6"')
rect(60, 145, 170, 50)
text(145, 175, "DC/DC", "tb", "middle")
line(230, 175, 750, 175, extra=' stroke-width="1.6"')
line(400, 175, 400, 250, end=True, extra=' stroke-width="1.6"')
line(750, 175, 750, 240, end=True, extra=' stroke-width="1.6"')
dot(400, 175)
text(300, 191, "+3.3 V")

# isolated DC/DC and contactor K1 on the barrier
rect(720, 56, 170, 66)
text(712, 78, "ISOLATED DC/DC", "tb", "end")
text(758, 96, "=24 V", "t", "middle")
text(845, 96, "±15 V", "t", "middle")
line(860, 122, 860, 240, end=True, extra=' stroke-width="1.6"')
rect(772, 132, 56, 40)
text(836, 190, "K1", "tb")

# ---------------------------------------------------------------- safety relay (domain A)
rect(40, 240, 210, 190)
text(145, 264, "SAFETY RELAY", "tb", "middle")
for y, lab in ((305, "DOOR"), (345, "E-STOP"), (385, "DC &lt; 50 V")):
    text(56, y + 5, lab, "ts")
    line(140, y, 160, y)
    line(172, y, 192, y)
    line(160, y + 8, 174, y - 8, extra=' stroke-width="1.4"')
# ENABLE and DISCHARGE through K1
poly([(250, 280), (262, 280)], "flt")
vhop(262, 280, 145, [175], "flt")
line(262, 145, 772, 145, "flt", end=True)
poly([(250, 295), (278, 295)], "flt")
vhop(278, 295, 162, [175], "flt")
line(278, 162, 772, 162, "flt", end=True)
# SAFETY OK to the MCU
line(250, 356, 300, 356, end=True)

# ---------------------------------------------------------------- STM32 + PC
rect(300, 250, 200, 560)
text(400, 535, "STM32", "tb", "middle")
text(308, 360, "SAFETY OK", "ts")
for y, lab in ((294, "ENABLE"), (324, "PWM"), (509, "FAULT"), (539, "RESET"), (719, "ADC1"), (749, "ADC2"), (779, "ADC3")):
    text(492, y, lab, "ts", "end")
text(308, 724, "USB", "ts")
line(400, 810, 400, 828)
line(386, 828, 414, 828, extra=' stroke-width="1.6"')
line(391, 834, 409, 834, extra=' stroke-width="1.4"')
line(396, 840, 404, 840)
rect(40, 650, 210, 130)
text(145, 720, "PC", "tb", "middle")
line(250, 720, 300, 720, start=True, end=True, extra=' stroke-width="1.5"')
text(275, 712, "USB", "t", "middle")

# ---------------------------------------------------------------- interlock, latch, OC
line(500, 290, 720, 290, end=True)
line(500, 320, 600, 320, end=True)
rect(600, 305, 50, 50)
text(625, 336, "&amp;", "tb", "middle")
line(650, 330, 720, 330, end=True)
rect(560, 480, 210, 80)
text(665, 526, "FAULT LATCH", "tb", "middle")
line(625, 480, 625, 355, "flt", end=True)
text(633, 420, "PWM_EN", "ts")
line(560, 505, 500, 505, "flt", end=True)
line(500, 535, 560, 535, end=True)
rect(585, 600, 200, 50)
text(685, 630, "OC COMP", "tb", "middle")
line(700, 600, 700, 560, "flt", end=True)
text(706, 586, "OC", "ts")

# ---------------------------------------------------------------- gate driver (on the barrier)
rect(720, 240, 280, 220)
text(878, 232, "GATE DRIVER", "tb")
for x, y, lab, anc in ((728, 258, "VDD1", None), (868, 258, "VDD2", None), (726, 285, "EN", None), (726, 345, "IN", None),
                       (766, 452, "FLT", None), (994, 324, "OUT", "end"), (994, 386, "DESAT", "end"), (994, 436, "E", "end")):
    text(x, y, lab, "ts", anc)
rect(828, 300, 130, 50, "sub")
text(893, 330, "OUTPUT", "tb", "middle")
rect(828, 372, 120, 50, "sub")
text(888, 402, "DESAT", "tb", "middle")
poly([(720, 290), (870, 290), (870, 300)], end=True)
line(720, 330, 828, 330, end=True)
line(958, 325, 1000, 325)
line(1000, 392, 948, 392, end=True)
line(910, 372, 910, 350, "flt", end=True)
poly([(828, 405), (760, 405), (760, 480)], "flt", end=True)

# ---------------------------------------------------------------- DUT (one module, own dashed box)
rect(1056, 262, 196, 196, "dut")
text(1252, 478, "DUT", "tb", "end")
# gate: driver OUT -> hop over DESAT riser -> RG -> G terminal -> gate
hhop(330, 1000, 1022, [1015], extra=' stroke-width="1.6"')
rect(1022, 322, 26, 16, "sub")
text(1035, 316, sub("R", "G"), "ts", "middle", ' font-size="12"')
line(1048, 330, 1052.5, 330, extra=' stroke-width="1.6"')
term(1056, 330)
line(1059.5, 330, 1120, 330, extra=' stroke-width="1.6"')
dot(1080, 330)
text(1062, 323, "G", "ts", extra=' font-size="12"')
# Kelvin emitter
line(1000, 430, 1052.5, 430, extra=' stroke-width="1.6"')
term(1056, 430)
line(1059.5, 430, 1160, 430, extra=' stroke-width="1.6"')
dot(1100, 430)
dot(1160, 430)
text(1052, 423, sub("E", "aux"), "ts", "end", ' font-size="12"')
# IGBT
line(1120, 305, 1120, 355, extra=' stroke-width="1.8"')
line(1130, 300, 1130, 360, extra=' stroke-width="3"')
line(1130, 315, 1160, 296, "pwr")
line(1160, 296, 1160, 274, "pwr")
line(1130, 345, 1160, 364, "pwr")
add('<path d="M1160,364 L1146,363 L1153,353 z" fill="#000" stroke="none"/>')
line(1160, 364, 1160, 441, "pwr")
text(1171, 300, "C", "t")
text(1171, 380, "E", "t")
# anti-parallel diode inside the module
poly([(1160, 286), (1230, 286), (1230, 335)], extra=' stroke-width="1.6"')
line(1219, 335, 1241, 335, extra=' stroke-width="1.8"')
add('<path d="M1220,355 L1240,355 L1230,335 z" fill="#fff" stroke="#000" stroke-width="1.3"/>')
poly([(1230, 355), (1230, 415), (1160, 415)], extra=' stroke-width="1.6"')
dot(1160, 286)
dot(1160, 415)
term(1160, 270, 4)
term(1160, 445, 4)
# DESAT sense: driver DESAT -> D_DESAT (anode at driver) -> collector
poly([(1000, 392), (1015, 392), (1015, 292)])
add('<path d="M1006,292 L1024,292 L1015,276 z" fill="#fff" stroke="#000" stroke-width="1.2"/>')
line(1005, 276, 1025, 276, extra=' stroke-width="1.6"')
poly([(1015, 276), (1015, 250), (1160, 250)])
dot(1160, 250)
text(1022, 243, sub("D", "DESAT"), "ts", extra=' font-size="12"')

# ---------------------------------------------------------------- double-pulse load and HV source
# collector -> node N; load inductor L (N -> P) with the freewheel diode in parallel (anode at N, cathode at P)
poly([(1160, 266), (1160, 230), (1275, 230)], "pwr")
dot(1265, 230, 3.5)
path("M1275,230 c4,-14 15,-14 19,0 c4,-14 15,-14 19,0 c4,-14 15,-14 19,0 c4,-14 15,-14 19,0", "pwr")
text(1313, 214, "L", "t", "middle")
line(1351, 230, 1420, 230, "pwr")
dot(1362, 230, 3.5)
poly([(1265, 230), (1265, 190), (1298, 190)], extra=' stroke-width="1.6"')
add('<path d="M1298,180 L1298,200 L1316,190 z" fill="#fff" stroke="#000" stroke-width="1.3"/>')
line(1316, 180, 1316, 200, extra=' stroke-width="1.8"')
poly([(1316, 190), (1362, 190), (1362, 230)], extra=' stroke-width="1.6"')
# DC- return through the current sensor
poly([(1160, 449), (1160, 490), (1196, 490)], "pwr")
add('<circle cx="1210" cy="490" r="10" fill="#fff" stroke="#000" stroke-width="1.3"/>')
line(1196, 490, 1224, 490, "pwr")
line(1224, 490, 1420, 490, "pwr")
# discharge branch across DC+ / DC-: normally-closed relay + resistor
dot(1390, 230, 3.5)
line(1390, 230, 1390, 268, "pwr")
line(1380, 268, 1400, 268, extra=' stroke-width="1.8"')
line(1390, 296, 1383, 270, extra=' stroke-width="1.8"')
line(1390, 296, 1390, 318, "pwr")
rect(1382, 318, 16, 50, "sub")
line(1390, 368, 1390, 490, "pwr")
dot(1390, 490, 3.5)
# HV source
rect(1420, 200, 140, 320)
text(1490, 365, "HV DC SOURCE", "tb", "middle")
text(1428, 236, "+", "t")
text(1428, 496, "−", "t")
# K1 outputs: ENABLE to the source, DISCHARGE actuates the discharge relay
hhop(145, 828, 1490, [860], "flt")
line(1490, 145, 1490, 200, "flt", end=True)
text(1180, 139, "ENABLE", "t", "middle")
hhop(162, 828, 1412, [860], "flt")
vhop(1412, 162, 282, [230], "flt")
line(1412, 282, 1392, 282, "flt", end=True)
text(1180, 179, "DISCHARGE", "t", "middle")

# ---------------------------------------------------------------- sensors (domain B)
rect(1020, 560, 395, 108, "dut")
for x, w, a in ((1035, 115, sub("V", "GE")), (1165, 85, sub("I", "C")), (1258, 142, sub("V", "CE"))):
    rect(x, 600, w, 55, "sub")
    text(x + w / 2, 633, a, "tb", "middle")
# taps
vhop(1080, 330, 600, [430], "msr", end=True)
line(1100, 430, 1100, 600, "msr", end=True)
line(1210, 500, 1210, 600, "msr", end=True)
vhop(1265, 230, 600, [490], "msr", end=True)                # V_CE + : collector side of L (node N)
dot(1290, 490)
line(1290, 490, 1290, 600, "msr", end=True)                  # V_CE - : emitter return
# sensors -> isolation amplifiers -> ADC
for x, y in ((1092, 715), (1207, 745), (1329, 775)):
    poly([(x, 655), (x, y), (880, y)], "msr", end=True)
rect(720, 695, 160, 100)
text(888, 690, "ISO AMPS", "tb")
for y, lab in ((715, sub("V", "GE")), (745, sub("I", "C")), (775, sub("V", "CE"))):
    line(720, y, 500, y, "msr", end=True)
    text(560, y - 7, lab, "ts", extra=' font-size="12"')
dot(650, 745)
vhop(650, 745, 650, [715], "msr", end=True)

# ---------------------------------------------------------------- isolation barrier
line(797, 46, 797, 815, "bar")
line(803, 46, 803, 815, "bar")

# ---------------------------------------------------------------- legend
add('''<g transform="translate(40,862)">
    <line class="pwr" x1="0" y1="0" x2="36" y2="0"/>
    <text class="ts" x="42" y="5">power</text>
    <line class="ctl" x1="130" y1="0" x2="166" y2="0" marker-end="url(#arr)"/>
    <text class="ts" x="172" y="5">control</text>
    <line class="flt" x1="270" y1="0" x2="306" y2="0" marker-end="url(#arr)"/>
    <text class="ts" x="312" y="5">fault / safety</text>
    <line class="msr" x1="430" y1="0" x2="466" y2="0"/>
    <text class="ts" x="472" y="5">measurement</text>
    <line class="bar" x1="600" y1="-3" x2="636" y2="-3"/><line class="bar" x1="600" y1="3" x2="636" y2="3"/>
    <text class="ts" x="642" y="5">isolation</text>
    <rect class="dut" x="760" y="-7" width="36" height="14"/>
    <text class="ts" x="802" y="5">DUT</text>
    <line class="ctl" x1="900" y1="0" x2="920" y2="0"/><path class="ctl" d="M910,-6 A6,6 0 0 1 910,6"/>
    <text class="ts" x="926" y="5">crossing</text>
  </g>''')

HEAD = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" width="1600" height="900" font-family="'Times New Roman', Times, serif" fill="none" stroke="#000">
  <defs>
    <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="#000" stroke="none"/>
    </marker>
    <style>
      .blk  { stroke:#000; stroke-width:1.4; fill:#fff; }
      .sub  { stroke:#000; stroke-width:1.1; fill:#fff; }
      .pwr  { stroke:#000; stroke-width:2.6; fill:none; }
      .ctl  { stroke:#000; stroke-width:1.2; fill:none; }
      .flt  { stroke:#000; stroke-width:2.0; fill:none; }
      .msr  { stroke:#000; stroke-width:1.2; fill:none; stroke-dasharray:6 4; }
      .bar  { stroke:#000; stroke-width:1.1; fill:none; stroke-dasharray:10 3 2 3; }
      .dut  { stroke:#000; stroke-width:1.1; fill:none; stroke-dasharray:9 5; }
      .t    { fill:#000; stroke:none; font-size:15px; }
      .tb   { fill:#000; stroke:none; font-size:16px; font-weight:bold; letter-spacing:0.3px; }
      .ts   { fill:#000; stroke:none; font-size:13px; }
      .ti   { fill:#000; stroke:none; font-size:13px; font-style:italic; }
      .dot  { fill:#000; stroke:none; }
      .term { fill:#fff; stroke:#000; stroke-width:1.2; }
      .num  { fill:#fff; stroke:#000; stroke-width:1.2; }
      .numt { fill:#000; stroke:none; font-size:12px; font-weight:bold; }
    </style>
  </defs>
  <rect x="0" y="0" width="1600" height="900" fill="#fff" stroke="none"/>
'''
OUT.write_text(HEAD + "\n".join("  " + e for e in E) + "\n</svg>\n", encoding="utf-8")
print("written", OUT)

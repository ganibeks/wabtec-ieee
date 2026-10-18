"""Generates igbt_tester_block_diagram_v2.svg: module-level tester (DUT = IGBT + integrated Wabtec gate driver,
driven over fiber like the locomotive TMC, powered by a 100 VAC / 25 kHz GDPC emulator. The DUT is ONE dual
module (T1 upper, T2 lower); the load inductor return is relay-switched to DC+ (test T2) or DC- (test T1). Style copied from the original igbt_tester_block_diagram.svg.
Run:  python make_block_diagram_v2.py   (writes the SVG next to this script)
"""
from pathlib import Path

OUT = Path(__file__).with_name("igbt_tester_block_diagram_v2.svg")
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
text(785, 40, "control side, earth-referenced (24 V / 3.3 V)", "ti", "end")
text(815, 24, "DOMAIN B", "tb")
text(815, 40, "module / DC-link side (isolated)", "ti")

# ---------------------------------------------------------------- power supplies (domain A)
add('<text class="ts" x="3" y="80" style="font-size:10.5px">~230 V</text>')
line(6, 88, 40, 88, extra=' stroke-width="1.6"')
rect(40, 55, 210, 70)
text(145, 80, "POWER SUPPLY", "tb", "middle")
text(145, 100, "AC/DC  ~230 V / =24 V", "t", "middle")
text(145, 117, "low-voltage DC", "ti", "middle")
# +24 V to isolated DC/DC, with primary-side supply-current sense (GDPC load)
line(250, 88, 410, 88, extra=' stroke-width="1.6"')
add('<circle cx="420" cy="88" r="10" fill="#fff" stroke="#000" stroke-width="1.3"/>')
line(430, 88, 720, 88, end=True, extra=' stroke-width="1.6"')
line(406, 88, 434, 88, extra=' stroke-width="1.6"')
text(270, 81, "+24 V")
line(145, 125, 145, 160, extra=' stroke-width="1.6"')
rect(40, 160, 210, 55)
text(145, 184, "DC/DC  =24 V / 3.3 V", "tb", "middle")
text(145, 203, "MCU and logic supply", "ti", "middle")
poly([(250, 188), (400, 188), (400, 250)], end=True, extra=' stroke-width="1.6"')
text(270, 181, "+3.3 V")
# I_GDPC sense -> STM32 ADC5 (hop over the +3.3 V riser)
hhop(238, 420, 330, [400], "msr")
path("M420,98 L420,238", "msr")
path("M330,238 L330,250", "msr", end=True)
text(426, 170, sub("I", "GDPC"), "ts")

# isolated DC/DC on the barrier, feeding the GDPC emulator
rect(720, 60, 160, 80)
text(712, 78, "ISOLATED DC/DC", "tb", "end")
text(684, 112, "GDPC supply", "ti", "end")
text(758, 92, "=24 V", "t", "middle")
text(758, 110, "primary", "ti", "middle")
text(758, 128, "EN", "ts", "middle")
text(842, 92, "isolated", "ts", "middle")
text(842, 108, "DC bus", "ts", "middle")
line(880, 100, 905, 100, end=True, extra=' stroke-width="1.6"')

# GDPC emulator (domain B)
rect(905, 60, 200, 80)
text(1005, 80, "GDPC EMULATOR", "tb", "middle")
text(1005, 99, "100 VAC / 25 kHz, one output", "ts", "middle")
text(1005, 116, "supply current monitored", "ts", "middle")
text(1005, 132, sub("on primary (I", "GDPC") + ", ADC5)", "ts", "middle")

# ---------------------------------------------------------------- STM32
rect(300, 250, 200, 598)
text(400, 395, "STM32", "tb", "middle")
text(400, 415, "MICROCONTROLLER", "tb", "middle")
text(400, 437, "test sequencer, timers,", "ti", "middle")
text(400, 453, "ADC, USB, fault log", "ti", "middle")
text(308, 266, "ADC5", "ts")
text(492, 266, "GDPC ENABLE", "ts", "end")
text(492, 310, "COMMAND T1 (upper)", "ts", "end")
text(492, 498, "COMMAND T2 (lower)", "ts", "end")
text(492, 512, "(to fiber TX)", "ts", "end", ' font-size="11"')
text(492, 604, "FAULT (EXTI)", "ts", "end")
text(492, 634, "LATCH RESET", "ts", "end")
for i, y in enumerate((760, 785, 810, 835), 1):
    text(492, y + 4, f"ADC{i}", "ts", "end")
text(308, 724, "USB")

# PC (unchanged)
rect(40, 650, 210, 140)
text(145, 676, "PC / LAPTOP", "tb", "middle")
for k, s in enumerate(["• test configuration", "• data acquisition", "• results visualization", "• PASS / FAIL report"]):
    text(55, 701 + 22 * k, s)
line(250, 720, 300, 720, start=True, end=True, extra=' stroke-width="1.5"')
text(275, 712, "USB", "t", "middle")

# GDPC ENABLE -> isolated DC/DC primary EN
poly([(500, 262), (690, 262), (690, 125), (720, 125)], end=True)

# ---------------------------------------------------------------- command interlock (&) and fault latch
# REF channel
line(500, 306, 590, 306, end=True)
rect(590, 296, 50, 40)
text(615, 322, "&amp;", "tb", "middle")
line(640, 316, 720, 316, end=True)
# DUT channel (hop over PWM_EN riser at x=565)
hhop(506, 500, 590, [565], end=True)
rect(590, 496, 50, 40)
text(615, 522, "&amp;", "tb", "middle")
hhop(516, 640, 720, [680], end=True)
text(615, 352, "interlock", "ti", "middle")
# PWM_EN from latch to both & gates
poly([(565, 570), (565, 326), (590, 326)], "flt", end=True)
line(565, 526, 590, 526, "flt", end=True)
dot(565, 526)
text(571, 470, "CMD_EN", "ts", extra=' font-size="11"')
# Status (fault) from fiber RX to latch
poly([(720, 336), (680, 336), (680, 570)], "flt", end=True)
poly([(720, 536), (700, 536), (700, 570)], "flt", end=True)
text(675, 452, "STATUS", "ts", "end", ' font-size="11"')
rect(530, 570, 200, 76)
text(630, 588, "FAULT LATCH (HW)", "tb", "middle")
text(540, 606, "Status FAULT or OC → latched", "ts")
text(540, 622, "blocks Command pulses (&amp;)", "ts")
text(540, 638, "cleared only by LATCH RESET", "ts")
line(530, 600, 500, 600, "flt", end=True)
line(500, 630, 530, 630, end=True)
# overcurrent comparator, fed from the isolated I_C channel
rect(540, 660, 190, 40)
text(635, 677, "OVERCURRENT COMPARATOR", "ts", "middle", ' font-size="12"')
text(635, 693, sub("I", "C") + " &gt; " + sub("I", "lim"), "ts", "middle")
line(705, 660, 705, 646, "flt", end=True)
dot(705, 785)
vhop(705, 785, 700, [760], "msr", end=True)

# ---------------------------------------------------------------- fiber-optic interface (on the barrier)
rect(720, 296, 160, 260)
text(712, 284, "FIBER-OPTIC INTERFACE", "tb", "end", ' font-size="14"')
text(758, 420, "TMC", "ts", "middle")
text(758, 436, "emulator", "ts", "middle")
text(842, 420, "optical", "ts", "middle")
text(842, 436, "TX / RX", "ts", "middle")
for y, s in ((312, "TX1"), (350, "RX1"), (512, "TX2"), (550, "RX2")):
    text(876, y, s, "ts", "end", ' font-size="10"')

# ---------------------------------------------------------------- dual module under test (domain B)
LEG = 1200


def half(y0, label, markers):
    """One switch position of the dual module: integrated driver, R_G, IGBT, anti-parallel diode."""
    X0 = 1000
    text(X0 + 20, y0 + 30, label, "ti", extra=' font-size="11"')
    rect(1022, y0 + 55, 115, 62, "sub")
    text(1080, y0 + 71, "Integrated gate", "ts", "middle", ' font-size="11"')
    text(1080, y0 + 85, "driver (Wabtec)", "ts", "middle", ' font-size="11"')
    text(1044, y0 + 106, "DESAT", "ts", extra=' font-size="10"')
    text(1104, y0 + 106, "soft-off", "ts", extra=' font-size="10"')
    if markers:
        num(1034, y0 + 103, 1, r=7, fs=10)
        num(1095, y0 + 103, 2, r=7, fs=10)
    for dy in (66, 86):                       # fiber Command in, Status out
        term(X0, y0 + dy)
        line(X0 + 3.5, y0 + dy, 1022, y0 + dy)
    # DESAT sense to collector through D_DESAT
    poly([(1118, y0 + 55), (1118, y0 + 44), (1150, y0 + 44)])
    add(f'<path d="M1150,{y0 + 38} L1150,{y0 + 50} L1161,{y0 + 44} z" fill="#fff" stroke="#000" stroke-width="1.1"/>')
    line(1161, y0 + 38, 1161, y0 + 50, extra=' stroke-width="1.4"')
    line(1161, y0 + 44, LEG, y0 + 44)
    dot(LEG, y0 + 44)
    # gate via R_G
    line(1137, y0 + 80, 1139, y0 + 80, extra=' stroke-width="1.6"')
    rect(1139, y0 + 74, 16, 12, "sub")
    text(1147, y0 + 99, sub("R", "G"), "ts", "middle", ' font-size="11"')
    line(1155, y0 + 80, 1163, y0 + 80, extra=' stroke-width="1.6"')
    text(1166, y0 + 74, "G", "ts", extra=' font-size="11"')
    # IGBT symbol
    line(1163, y0 + 58, 1163, y0 + 102, extra=' stroke-width="1.8"')
    line(1171, y0 + 52, 1171, y0 + 108, extra=' stroke-width="3"')
    line(1171, y0 + 64, LEG, y0 + 48, "pwr")
    line(LEG, y0 + 48, LEG, y0, "pwr")
    line(1171, y0 + 96, LEG, y0 + 112, "pwr")
    add(f'<path d="M{LEG},{y0 + 112} L{LEG - 14},{y0 + 111} L{LEG - 7},{y0 + 101} z" fill="#000" stroke="none"/>')
    line(LEG, y0 + 112, LEG, y0 + 150, "pwr")
    text(1207, y0 + 62, "C", "t")
    text(1207, y0 + 100, "E", "t")
    # anti-parallel diode
    poly([(LEG, y0 + 26), (1262, y0 + 26), (1262, y0 + 64)], extra=' stroke-width="1.6"')
    line(1251, y0 + 64, 1273, y0 + 64, extra=' stroke-width="1.8"')
    add(f'<path d="M1252,{y0 + 84} L1272,{y0 + 84} L1262,{y0 + 64} z" fill="#fff" stroke="#000" stroke-width="1.3"/>')
    poly([(1262, y0 + 84), (1262, y0 + 132), (LEG, y0 + 132)], extra=' stroke-width="1.6"')
    dot(LEG, y0 + 26)
    dot(LEG, y0 + 132)


rect(1000, 212, 290, 393, "dut")
text(1008, 228, "MODULE UNDER TEST (DUT)", "tb", extra=' font-size="12"')
text(1008, 243, "dual: 2 × (IGBT + driver)", "ti", extra=' font-size="12"')
half(250, "T1 upper: IGBT + driver 1", False)
half(450, "T2 lower: IGBT + driver 2", True)
# power terminals on the module edge: DC+ (top), AC phase (right), DC- (bottom)
line(LEG, 250, LEG, 215.5, "pwr")
term(LEG, 212, 4)
line(LEG, 400, LEG, 450, "pwr")
dot(LEG, 425, 3.5)
line(LEG, 425, 1286, 425, "pwr")
term(1290, 425, 4)
text(1266, 419, "AC", "ts", extra=' font-size="11"')
text(1215, 442, "phase node", "ts", extra=' font-size="11"')
term(LEG, 605, 4)
# driver power: one shared 100 VAC input, distributed to both drivers (hops over the T2 fiber lines)
term(1000, 556)
line(1003.5, 556, 1022, 556)
dot(1010, 556)
vhop(1010, 556, 356, [536, 516])
line(1010, 356, 1022, 356)
# V_GE test point (T2, optional): gate node -> box edge, dashed
dot(1159, 530)
poly([(1159, 530), (1159, 588), (1003.5, 588)], "msr")
add('<circle class="term" cx="1000" cy="588" r="3.5" stroke-dasharray="2 2"/>')
text(1006, 620, sub("V", "GE") + " test point (if accessible)", "ti", extra=' font-size="11"')

# fiber links: interface <-> module (Command out, Status in), T1 and T2; hops over the 100 VAC riser (x=960)
for y0 in (250, 450):
    hhop(y0 + 66, 880, 996, [960], end=True)
    hhop(y0 + 86, 996, 880, [960], end=True)
text(884, 311, "Command", "ts", extra=' font-size="11"')
text(884, 349, "Status", "ts", extra=' font-size="11"')
text(884, 511, "Command", "ts", extra=' font-size="11"')
text(884, 549, "Status", "ts", extra=' font-size="11"')
vhop(960, 140, 556, [316, 336, 516, 536])
line(960, 556, 996, 556, end=True)
text(974, 260, "100 VAC", "ts", extra=' font-size="11" transform="rotate(-90 974 260)"')
num(912, 566, 3)

# ---------------------------------------------------------------- test fixture power path
poly([(LEG, 208), (LEG, 203), (1470, 203)], "pwr")
line(LEG, 609, LEG, 615, "pwr")
add(f'<circle cx="{LEG}" cy="624" r="9" fill="#fff" stroke="#000" stroke-width="1.3"/>')
line(LEG, 633, LEG, 640, "pwr")
line(LEG, 640, 1470, 640, "pwr")
# load inductor from the AC terminal, return switched to DC+ (test T2) or DC- (test T1)
line(1293.5, 425, 1326, 425, "pwr")
add('<circle cx="1335" cy="425" r="9" fill="#fff" stroke="#000" stroke-width="1.3"/>')
poly([(1344, 425), (1380, 425), (1380, 400)], "pwr")
path("M1380,400 a10,10 0 0 1 0,-20 a10,10 0 0 1 0,-20 a10,10 0 0 1 0,-20 a10,10 0 0 1 0,-20",
     extra=' stroke-width="1.8"')
poly([(1380, 320), (1380, 310), (1398, 310)], "pwr")
text(1300, 356, "LOAD", "ts", extra=' font-size="12" font-weight="bold"')
text(1300, 372, "INDUCTOR", "ts", extra=' font-size="12" font-weight="bold"')
rect(1398, 282, 64, 56, "sub")
text(1430, 299, "L RETURN", "ts", "middle", ' font-size="10"')
text(1430, 312, "RELAY", "ts", "middle", ' font-size="10"')
text(1430, 329, "DC+ / DC−", "ts", "middle", ' font-size="10"')
line(1430, 282, 1430, 203, "pwr")
dot(1430, 203)
line(1430, 338, 1430, 640, "pwr")
dot(1430, 640)
text(1436, 250, "test T2", "ti", extra=' font-size="10"')
text(1436, 470, "test T1", "ti", extra=' font-size="10"')
# controlled DC link
rect(1470, 198, 110, 462)
text(1478, 222, "DC+", "tb", extra=' font-size="13"')
text(1478, 646, "DC−", "tb", extra=' font-size="13"')
for k, s in enumerate(["CONTROLLED", "DC LINK"]):
    text(1525, 380 + 18 * k, s, "tb", "middle", ' font-size="14"')
text(1525, 418, "(conceptual)", "ti", "middle")
for k, s in enumerate(["current-limited,", "interlocked,", "auto-discharge"]):
    text(1525, 444 + 16 * k, s, "ts", "middle")

# ---------------------------------------------------------------- measurement sensors (domain B)
text(1005, 652, "MEASUREMENT SENSORS", "tb", extra=' font-size="12"')
rect(915, 660, 545, 80, "dut")
boxes = [(930, 100, sub("V", "GE") + " (opt.)", "test point"),
         (1120, 100, sub("I", "C"), "current sensor"),
         (1260, 88, sub("I", "L"), "load inductor"),
         (1355, 98, sub("V", "AC") + " / " + sub("V", "CE"), "HV div. + clamp")]
for x, w, a, b in boxes:
    rect(x, 668, w, 62, "sub")
    text(x + w / 2, 690, a, "t", "middle")
    text(x + w / 2, 710, b, "ts", "middle", ' font-size="12"')
# taps into the sensors
poly([(996.5, 588), (980, 588), (980, 668)], "msr", end=True)                 # V_GE test point
poly([(1191, 624), (1170, 624), (1170, 668)], "msr", end=True)                # I_C (DC- path)
vhop(1335, 434, 668, [640], "msr", end=True)                                  # I_L
dot(1362, 425)
vhop(1362, 425, 668, [640], "msr", end=True)                                  # V_AC: phase node
dot(1446, 640)
line(1446, 640, 1446, 668, "msr", end=True)                                   # V_AC: DC-
# sensors -> isolation amplifiers -> STM32 ADC1..4
chan = [(980, 760, sub("V", "GE") + " (opt.)"), (1170, 785, sub("I", "C")),
        (1304, 810, sub("I", "L")), (1404, 835, sub("V", "CE"))]
for x, y, lab in chan:
    poly([(x, 730), (x, y), (880, y)], "msr", end=True)
    text(890, y - 8, lab, "ts", extra=' font-size="12"')
    line(720, y, 500, y, "msr", end=True)
    text(520, y - 8, lab, "ts", extra=' font-size="12"')
rect(720, 748, 160, 100)
text(690, 740, "ISOLATION AMPLIFIERS", "tb", "end", ' font-size="14"')
text(758, 800, "filter,", "ts", "middle")
text(758, 816, "scaling", "ts", "middle")
text(842, 800, "input", "ts", "middle")
text(842, 816, "stage", "ts", "middle")

# ---------------------------------------------------------------- isolation barrier (continuous)
line(797, 46, 797, 850, "bar")
line(803, 46, 803, 850, "bar")

# ---------------------------------------------------------------- fault-chain markers (Domain A part)
num(612, 556, 4)
num(515, 586, 5)

# ---------------------------------------------------------------- response-chain note
rect(1120, 46, 460, 146, "sub")
text(1132, 66, "SHORT-CIRCUIT / DESAT RESPONSE CHAIN", "tb", extra=' font-size="14"')
chain = ["DESAT detected inside the DUT's integrated driver.",
         "DUT driver turns the IGBT off by itself (no tester in the loop).",
         "Fault reported on the fiber Status link.",
         "HW latch blocks Command pulses (&amp;); overcurrent (I<tspan font-size=\"9\" dy=\"3\">C</tspan><tspan dy=\"-3\">) uses it too.</tspan>",
         "STM32 gets FAULT interrupt, logs timestamps, resets latch after inspection."]
for k, s in enumerate(chain):
    y = 86 + 19 * k
    num(1141, y - 4, k + 1, r=8)
    text(1156, y, s, "ts", extra=' font-size="12.5"')
text(1132, 183, "Measured: ① → ② → " + sub("I", "C") + " below 1 %, compared with the Wabtec ≈ 10 µs reference.",
     "ti", extra=' font-size="12.5"')

# ---------------------------------------------------------------- legend, caption, note
add('''<g transform="translate(40,862)">
    <line class="pwr" x1="0" y1="0" x2="36" y2="0"/>
    <text class="ts" x="42" y="5">power path (conceptual)</text>
    <line class="ctl" x1="190" y1="0" x2="226" y2="0" marker-end="url(#arr)"/>
    <text class="ts" x="232" y="5">control signal / fiber link</text>
    <line class="flt" x1="400" y1="0" x2="436" y2="0" marker-end="url(#arr)"/>
    <text class="ts" x="442" y="5">fault / protection signal</text>
    <line class="msr" x1="590" y1="0" x2="626" y2="0"/>
    <text class="ts" x="632" y="5">measurement signal</text>
    <line class="bar" x1="760" y1="-3" x2="796" y2="-3"/><line class="bar" x1="760" y1="3" x2="796" y2="3"/>
    <text class="ts" x="802" y="5">isolation boundary</text>
    <rect class="dut" x="920" y="-7" width="36" height="14"/>
    <text class="ts" x="962" y="5">module / sensor group</text>
    <line class="ctl" x1="1110" y1="0" x2="1130" y2="0"/><path class="ctl" d="M1120,-6 A6,6 0 0 1 1120,6"/>
    <text class="ts" x="1136" y="5">crossing, not connected</text>
  </g>''')
text(40, 890, "Fig. 1.  Functional block diagram of the STM32-based IGBT test system (conceptual architecture; not a construction drawing).")
text(1580, 880, "Assumed: Wabtec slides 5–8 and team input (dual module, one shared 100 VAC input);", "ti", "end", ' font-size="12"')
text(1580, 895, "fiber protocol, connector pinout and gate test-point access to be confirmed with Wabtec.", "ti", "end", ' font-size="12"')

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

"""Draw the saved RL fixture as an editable engineering figure, not a new model."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, FancyArrowPatch, Arc
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results/dynamic_20261017_195453_347"
NAVY, TEAL, AMBER, MUTED = "#18344e", "#008779", "#d48a20", "#647789"


def render(folder):
    p = json.loads((SOURCE / "parameters.json").read_text(encoding="utf-8-sig"))
    plt.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "none", "pdf.fonttype": 42})
    fig, ax = plt.subplots(figsize=(16, 9), facecolor="white")
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.set(xlim=(0, 16), ylim=(0, 9), aspect="equal")
    ax.axis("off")

    def text(x, y, s, size=13, colour=NAVY, **kw):
        ax.text(x, y, s, fontsize=size, color=colour, va="center", **kw)

    def wire(points, colour=NAVY, lw=2.3, **kw):
        x, y = zip(*points)
        ax.plot(x, y, color=colour, lw=lw, solid_capstyle="round", **kw)

    def node(x, y):
        ax.add_patch(Circle((x, y), .047, color=NAVY, zorder=5))

    def sensor(x, y, label, name):
        ax.add_patch(Circle((x, y), .20, facecolor="white", edgecolor=NAVY, lw=2, zorder=3))
        text(x, y, label, 12, ha="center", zorder=4)
        text(x, y+.38, name, 12, ha="center")

    def box(x, y, w, h, fill, edge="#dce5eb"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.025,rounding_size=0.12",
                                  facecolor=fill, edgecolor=edge, lw=1.1, zorder=0))

    def arrow(a, b, colour=TEAL, size=14):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=size, lw=2, color=colour))

    def ground(x, y):
        wire([(x, y), (x, y-.13)])
        for dy, half in ((.13,.18),(.21,.12),(.29,.055)):
            wire([(x-half, y-dy),(x+half, y-dy)], lw=1.7)

    text(.65, 8.27, "IGBT ELECTRICAL TEST CELL", 29, weight="bold")
    text(.68, 7.77, "Double-pulse RL fixture  /  NU IEEE–Wabtec Hackathon 2026", 16, MUTED)
    box(12.25, 7.73, 3.1, .55, "#e8f5f2", "#cce6df")
    text(13.8, 8.0, "SIMULATED ELECTRICAL CIRCUIT", 10, TEAL, weight="bold", ha="center")
    wire([(.68,7.35),(15.32,7.35)], "#e2e9ee", 1)

    # Vbus -> Ibus -> branch point -> IL -> R -> L -> switch node -> Lsigma -> Ic -> DUT.
    wire([(1.25,3.45),(1.25,5),(4.3,5)])
    ax.add_patch(Circle((1.25,3.05),.40, facecolor="white", edgecolor=NAVY,lw=2.3))
    text(1.25,3.18,"+",17,ha="center")
    text(1.25,2.91,"−",17,ha="center")
    wire([(1.25,2.65),(1.25,1.45),(9.2,1.45),(9.2,2.34)])
    text(1.57,4.18,"DC SUPPLY",11,MUTED,weight="bold")
    text(1.57,3.83,f"{p['bus_V']/1000:g} kV",17,weight="bold")
    sensor(2.2,5,"A",r"$I_{bus}$")
    sensor(3.65,5,"A",r"$I_L$")
    node(3,5)
    zig=[(4.3,5)]+[(4.4+i*.12,5+(.13 if i%2==0 else -.13)) for i in range(7)]+[(5.25,5)]
    wire(zig)
    text(4.78,4.57,f"R  {p['loadR_Ohm']*1000:g} mΩ",13,ha="center")
    wire([(5.25,5),(5.7,5)])
    for i in range(5):
        ax.add_patch(Arc((5.85+i*.3,5),.3,.48,theta1=0,theta2=180,color=NAVY,lw=2.3))
    wire([(7.2,5),(9.2,5),(9.2,4.7)])
    text(6.45,4.57,f"L  {p['loadL_H']*1e6:g} µH",13,ha="center")
    node(9.2,5)
    text(9.43,5.07,"SW",11,MUTED)
    # Freewheel diode: anode at SW (right), cathode at supply-side branch (left).
    wire([(9.2,5),(9.2,6.35),(6.55,6.35)])
    wire([(5.65,6.35),(3,6.35),(3,5)])
    ax.add_patch(Polygon([(6.45,6.58),(6.45,6.12),(5.98,6.35)],closed=True,
                         facecolor="white",edgecolor=NAVY,lw=2.1))
    wire([(5.98,6.08),(5.98,6.62)])
    wire([(6.45,6.35),(6.55,6.35)])
    wire([(5.65,6.35),(5.98,6.35)])
    sensor(8.1,6.35,"A",r"$I_D$")
    text(5.95,6.95,"FREEWHEEL PATH",11,TEAL,weight="bold",ha="center")
    arrow((7.4,6.74),(6.7,6.74))
    wire([(5.5,6.35),(5.5,5.76),(6.02,5.76)])
    wire([(6.2,5.76),(6.85,5.76),(6.85,6.35)])
    wire([(6.02,5.59),(6.02,5.93)])
    wire([(6.2,5.59),(6.2,5.93)])
    text(7.02,5.77,f"Cj {p['diodeC_F']*1e9:g} nF",10,MUTED)
    node(5.5,6.35); node(6.85,6.35)

    for i in range(3):
        ax.add_patch(Arc((9.2,4.6-i*.18),.34,.18,theta1=-90,theta2=90,color=NAVY,lw=2.2))
    wire([(9.2,4.15),(9.2,3.26),(8.96,3.1)])
    sensor(9.2,3.79,"A","")
    text(8.78,3.79,r"$I_C$",12,ha="right")
    text(9.64,4.5,f"Lσ  {p['strayL_H']*1e9:g} nH",12)
    text(9.64,4.19,f"Rσ  {p['strayR_Ohm']*1000:g} mΩ",10,MUTED)
    wire([(8.96,3.16),(8.96,2.5)])
    wire([(8.72,3.16),(8.72,2.5)],TEAL)
    wire([(8.96,2.63),(9.2,2.34)])
    arrow((9.0,2.58),(9.2,2.34),NAVY,11)
    text(8.7,2.1,"IGBT / DUT",13,weight="bold",ha="right")
    text(9.44,3.23,"C",11,MUTED)
    text(9.42,2.23,"E",11,MUTED)
    ground(9.2,1.45); ground(1.25,1.45)
    # Actual Vce sensor is shown; other sensor wires are omitted for clarity.
    wire([(9.2,3.32),(10.45,3.32),(10.45,1.45),(9.2,1.45)],AMBER,1.6)
    node(9.2,3.32)
    sensor(10.45,2.44,"V",r"$V_{CE}$")

    box(1.85,2.38,2.65,1.05,"#f1f5f9")
    text(3.175,3.08,"DOUBLE-PULSE CONTROL",11,weight="bold",ha="center")
    text(3.175,2.73,"MATLAB / Simulink",12,MUTED,ha="center")
    arrow((4.55,2.86),(5.05,2.86))
    box(5.15,2.38,2.55,1.05,"#e8f5f2","#b9ded5")
    text(6.425,3.08,"GATE DRIVER",12,TEAL,weight="bold",ha="center")
    text(6.425,2.72,f"+{p['gateOn_V']:g} V ON  /  {p['gateOff_V']:g} V OFF",12,TEAL,ha="center")
    wire([(7.73,2.85),(8.72,2.85)],TEAL)
    text(8.1,3.15,r"$V_{GE}$",12,TEAL,ha="center")
    wire([(6.45,2.36),(6.45,1.45)],TEAL,1.5)
    node(6.45,1.45)
    text(5.25,1.91,f"Driver RON {p['RdriverOn_Ohm']:g} Ω / ROFF {p['RdriverOff_Ohm']:g} Ω",10,MUTED)

    box(11.85,1.45,3.48,5.24,"#f5f8fb")
    text(12.15,6.23,"ACQUIRE & ANALYZE",14,weight="bold")
    text(12.15,5.75,"Electrical measurements",12,MUTED)
    for y,label in [(5.25,"VGE · VCE · IC"),(4.83,"IG · IL · ID · Ibus"),(4.41,"Switch-node voltage")]:
        text(12.15,y,label,14)
    wire([(12.15,4.04),(15.0,4.04)],"#dce5eb",1)
    for y,label in [(3.66,"Gate & switching transients"),(3.2,"Current commutation"),(2.74,"Terminal-energy integrals"),(2.28,"KCL / energy / convergence")]:
        text(12.15,y,label,11.5)
    text(12.15,1.79,"Saved waveforms + test reports",11,TEAL)

    # Timing is a command schedule from saved parameters, not a measured waveform.
    t=np.r_[0,np.array(p['pulseEdges_s'])*1e6,600]
    y=np.array([0,1,0,1,0,0])
    text(1.0,.80,"GATE COMMAND",10,MUTED,weight="bold")
    ax.step(3.1+t/600*6.9,.56+y*.40,where="post",color=TEAL,lw=2)
    for edge in np.array(p['pulseEdges_s'])*1e6:
        text(3.1+edge/600*6.9,.34,f"{edge:g}",9,MUTED,ha="center")
    text(10.25,.75,"µs",11,MUTED)
    text(.68,.13,"Representative traction device · load/parasitics illustrative · simplified wiring · no reverse recovery",10,MUTED)
    for ext in ("svg","pdf","png"):
        file=folder/f"igbt_test_cell_slide.{ext}"
        if file.exists():
            raise FileExistsError(file)
        fig.savefig(file,dpi=240,facecolor="white")
    plt.close(fig)
    (folder/"SCHEMATIC_NOTES.txt").write_text(
        "Presentation drawing of the saved dynamic RL fixture, not a replacement simulation model.\n"
        f"Source: {SOURCE.relative_to(ROOT)}\n"
        "Power topology: bus -> Ibus -> [diode cathode branch] -> IL -> R -> L -> SW -> Lsigma/Rsigma -> Ic -> IGBT -> return.\n"
        "Diode anode connects to SW through Id; diode capacitance is parallel after Id.\n"
        "Driver source reference connects to emitter return. Auxiliary sensor wiring, solver block and internal gate resistance omitted for clarity.\n"
        "Gate command trace is the saved stimulus schedule; it is not a measured gate-voltage waveform.\n"
        "The representative device is Mitsubishi CM1500HC-66XB, not an identified Wabtec assembly.\n"
        "No integrated DESAT or real hardware DAQ is implied. Numerical/reference validation is unchanged.\n",
        encoding="utf-8")
    print(folder / "igbt_test_cell_slide.png")


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("folder",type=Path)
    args=parser.parse_args()
    args.folder.mkdir(parents=True,exist_ok=True)
    render(args.folder)

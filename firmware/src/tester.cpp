#include "tester.hpp"

namespace igbt {
namespace {

constexpr double NaN = __builtin_nan("");
inline double fabs_(double x) { return x < 0 ? -x : x; }
inline bool isnan_(double x) { return x != x; }

struct Mean {
    double sum = 0;
    uint32_t n = 0;
    void add(double v) { sum += v; ++n; }
    double get() const { return n ? sum / n : NaN; }
};

// First crossing of `level` after `after_ns`, linearly interpolated between ADC frames.
struct Crossing {
    double level = NaN;
    bool rising = true;
    uint64_t after_ns = 0;
    double t_ns = NaN;
    bool have_prev = false;
    double pv = 0, pt = 0;
    void arm(double lv, bool up, uint64_t after) { level = lv; rising = up; after_ns = after; t_ns = NaN; have_prev = false; }
    void feed(uint64_t t, double v) {
        if (isnan_(level) || !isnan_(t_ns) || t < after_ns) return;
        if (have_prev) {
            bool hit = rising ? (pv < level && v >= level) : (pv > level && v <= level);
            if (hit) t_ns = pt + (level - pv) * (double(t) - pt) / (v - pv);
        }
        pv = v; pt = double(t); have_prev = true;
    }
};

inline bool in(uint64_t t, uint64_t a, uint64_t b) { return t >= a && t < b; }
constexpr uint64_t US = 1000;

}  // namespace

bool Tester::run_double_pulse(const PulsePlan& p, const Config& c) {
    if (!(p.edge_ns[0] < p.edge_ns[1] && p.edge_ns[1] < p.edge_ns[2] && p.edge_ns[2] < p.edge_ns[3] && p.edge_ns[3] < p.stop_ns)) {
        rep_.status("error", "pulse plan edges not strictly increasing");
        return false;
    }
    if (!gate_.arm(p)) return false;
    rep_.status("sequence", "DOUBLE_PULSE_ARMED");

    const uint64_t e0 = p.edge_ns[0], e1 = p.edge_ns[1], e2 = p.edge_ns[2], e3 = p.edge_ns[3];
    // Measurement windows (same definitions as +testcell/analyze_dynamic.m where one exists).
    const uint64_t pre_a = 0, pre_b = (e0 > 5 * US) ? e0 - 5 * US : e0;   // before ON-1: bus, gate OFF level
    const uint64_t on_a = e1 - 10 * US, on_b = e1 - 2 * US;              // end of pulse 1: Vce(sat), gate ON level
    const uint64_t fw_a = e2 - 10 * US, fw_b = e2 - 2 * US;              // freewheel: diode Vf

    Mean bus, vge_off, vge_on, vce_sat, ic_sat, vf, id_fw, ic_pre_off;
    double vce_pk = -1e30, ic_pk = -1e30, vce_pk_t = 0, ic_pk_t = 0;
    Crossing off_v90, off_i90, off_i10;
    bool off_armed = false;
    uint64_t last_on_ns = e0, trip_ns = 0, fault_seen_ns = 0;
    bool tripped = false, fault_first = false;
    uint32_t frames = 0;
    double ch[NUM_CH];
    float lsb[NUM_CH];
    for (int k = 0; k < NUM_CH; ++k) lsb[k] = adc_.lsb(Ch(k));

    AdcFrame f;
    while (adc_.next(f)) {
        const uint64_t t = f.t_ns;
        ++frames;
        for (int k = 0; k < NUM_CH; ++k) ch[k] = double(f.code[k]) * lsb[k];

        // ---- fault supervision ------------------------------------------------------------------
        const bool on = gate_.commanded_on(t);
        if (t >= e2 && last_on_ns < e2) last_on_ns = e2;
        if (on && t >= last_on_ns + uint64_t(c.desat_blank_us * 1000.0f) && ch[VCE] > c.desat_thr_V) {
            gate_.force_off(t);
            trip_ns = t; tripped = true;
            rep_.event("DESAT_TRIP_FIRMWARE", t / 1e3);
            break;
        }
        if (fault_.asserted(t)) {
            if (!fault_first) { fault_first = true; fault_seen_ns = t; }
            gate_.force_off(t);
            trip_ns = t; tripped = true;
            rep_.event("DRIVER_FAULT_INPUT", t / 1e3);
            break;
        }

        // ---- windowed means -----------------------------------------------------------------------
        if (in(t, pre_a, pre_b)) { bus.add(ch[VBUS]); vge_off.add(ch[VGE]); }
        if (in(t, on_a, on_b)) { vge_on.add(ch[VGE]); vce_sat.add(ch[VCE_CLAMP]); ic_sat.add(ch[IC]); }
        if (in(t, fw_a, fw_b)) { vf.add(ch[VSW] - ch[VBUS]); id_fw.add(ch[ID]); }
        if (in(t, e1 - 10 * US, e1 - 5 * US)) ic_pre_off.add(ch[IC]);
        if (ch[VCE] > vce_pk) { vce_pk = ch[VCE]; vce_pk_t = double(t); }
        if (ch[IC] > ic_pk) { ic_pk = ch[IC]; ic_pk_t = double(t); }

        // ---- OFF-1 timing (armed once the pre-turn-off current and bus are known) ------------------
        if (!off_armed && t >= e1) {
            const double b = bus.get(), i0 = ic_pre_off.get();
            off_v90.arm(0.9 * b, true, e1);
            off_i90.arm(0.9 * i0, false, e1);
            off_i10.arm(0.1 * i0, false, e1);
            off_armed = true;
        }
        if (off_armed && t < e2) { off_v90.feed(t, ch[VCE]); off_i90.feed(t, ch[IC]); off_i10.feed(t, ch[IC]); }
    }
    (void)e3;

    // ---- report -----------------------------------------------------------------------------------
    rep_.meas("frames", frames, "", "ADC frames processed");
    const double b = bus.get();
    rep_.meas("bus_V", b, "V", "mean VBUS before ON-1");
    rep_.status("bus_check", (!isnan_(b) && fabs_(b - c.bus_expected_V) <= c.bus_tol_frac * c.bus_expected_V) ? "OK" : "OUT_OF_PLAN");
    rep_.meas("vge_off_V", vge_off.get(), "V", "mean VGE before ON-1");
    rep_.meas("vge_on_V", vge_on.get(), "V", "mean VGE over last 10-2 us of pulse 1");
    const bool gate_ok = fabs_(vge_off.get() - c.gate_off_V) <= c.gate_tol_V && fabs_(vge_on.get() - c.gate_on_V) <= c.gate_tol_V;
    rep_.status("gate_check", gate_ok ? "OK" : "OUT_OF_PLAN");
    if (tripped) {
        rep_.meas("trip_time_us", trip_ns / 1e3, "us", "firmware turn-off command time");
        if (fault_first) rep_.meas("fault_to_offcmd_us", (trip_ns - fault_seen_ns) / 1e3, "us", "firmware reaction in ADC-frame polling; real path is hardware");
        rep_.status("sequence", "ABORTED_FAULT");
        return false;
    }
    rep_.meas("vce_sat_V", vce_sat.get(), "V", "VCE_CLAMP mean, last 10-2 us of pulse 1");
    rep_.meas("vce_sat_at_A", ic_sat.get(), "A", "IC mean in the same window");
    rep_.meas("diode_vf_V", vf.get(), "V", "VSW-VBUS mean, last 10-2 us of freewheel");
    rep_.meas("diode_vf_at_A", id_fw.get(), "A", "ID mean in the same window");
    rep_.meas("peak_vce_V", vce_pk, "V", "max sampled VCE (edges may be under-sampled)");
    rep_.meas("peak_vce_t_us", vce_pk_t / 1e3, "us", "");
    rep_.meas("peak_ic_A", ic_pk, "A", "max sampled IC");
    rep_.meas("peak_ic_t_us", ic_pk_t / 1e3, "us", "");
    rep_.meas("off1_cmd_to_vce90_us", (off_v90.t_ns - double(e1)) / 1e3, "us", "OFF-1 command to VCE = 90 % bus");
    rep_.meas("off1_ic_fall_90_10_us", (off_i10.t_ns - off_i90.t_ns) / 1e3, "us", "OFF-1 IC 90 % -> 10 % of pre-turn-off current");
    rep_.status("desat", "NOT_TRIPPED");
    rep_.status("sequence", "COMPLETE");
    return true;
}

}  // namespace igbt

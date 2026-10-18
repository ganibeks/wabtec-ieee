#include "sim_board.hpp"

#include <cmath>
#include <cstdlib>
#include <cstring>

namespace igbt {

bool SimBoard::load_csv(const char* path, double bus_V, std::string& err) {
    FILE* fp = std::fopen(path, "rb");
    if (!fp) { err = std::string("cannot open record ") + path; return false; }
    char line[1024];
    if (!std::fgets(line, sizeof line, fp)) { std::fclose(fp); err = "empty record"; return false; }
    // Expected header (plot_dynamic.m): time_s,Vge_V,Vce_V,Ic_A,Ig_A,IL_A,Id_A,Ibus_A,Vswitch_V
    if (std::strncmp(line, "time_s,Vge_V,Vce_V,Ic_A,Ig_A,IL_A,Id_A,Ibus_A,Vswitch_V", 54) != 0) {
        std::fclose(fp); err = "unexpected CSV header (need dynamic_rl/dynamic_r export)"; return false;
    }
    t_.clear(); vge_.clear(); vce_.clear(); ic_.clear(); id_.clear(); vsw_.clear();
    while (std::fgets(line, sizeof line, fp)) {
        double v[9]; char* p = line;
        for (int k = 0; k < 9; ++k) { v[k] = std::strtod(p, &p); if (*p == ',') ++p; }
        t_.push_back(v[0]); vge_.push_back(v[1]); vce_.push_back(v[2]); ic_.push_back(v[3]);
        id_.push_back(v[6]); vsw_.push_back(v[8]);
    }
    std::fclose(fp);
    if (t_.size() < 2) { err = "record too short"; return false; }
    bus_V_ = bus_V;
    return true;
}

bool SimBoard::arm(const PulsePlan& plan) {
    if (t_.empty()) { last_error = "no record loaded"; return false; }
    // The record was produced open-loop by MATLAB with its own pulse plan; the firmware plan must match it,
    // otherwise the replayed device response would not belong to the commanded gate signal.
    if (have_rec_plan_) {
        for (int k = 0; k < 4; ++k)
            if (std::fabs(plan.edge_ns[k] * 1e-9 - rec_edges_s_[k]) > 1e-9) {
                last_error = "pulse plan differs from the plan the simulation record was generated with";
                return false;
            }
    }
    if (plan.stop_ns * 1e-9 > record_end_s() + 1e-12) { last_error = "acquisition longer than record"; return false; }
    plan_ = plan; armed_ = true; off_forced_ = false; n_ = 0; j_ = 0;
    return true;
}

bool SimBoard::commanded_on(uint64_t t_ns) const {
    if (!armed_) return false;
    if (off_forced_ && t_ns >= forced_at_ns_) return false;
    int n = 0;
    for (int k = 0; k < 4; ++k) if (t_ns >= plan_.edge_ns[k]) ++n;
    return (n % 2) == 1;
}

double SimBoard::interp(const std::vector<double>& y, double ts) {
    const size_t n = t_.size();
    if (ts <= t_[0]) return y[0];
    if (ts >= t_[n - 1]) return y[n - 1];
    while (j_ + 1 < n && t_[j_ + 1] <= ts) ++j_;
    const double dt = t_[j_ + 1] - t_[j_];
    if (dt <= 0) return y[j_ + 1];
    return y[j_] + (y[j_ + 1] - y[j_]) * ((ts - t_[j_]) / dt);
}

bool SimBoard::next(AdcFrame& f) {
    if (!armed_ || off_forced_) return false;
    const uint64_t t_ns = uint64_t(std::llround(double(n_) * 1e9 / adc_rate_hz));
    if (t_ns > plan_.stop_ns) return false;
    ++n_;
    const double ts = t_ns * 1e-9;
    const size_t j_save = j_;
    double v[NUM_CH];
    v[VGE] = interp(vge_, ts); j_ = j_save;
    v[VCE] = interp(vce_, ts); j_ = j_save;
    v[IC] = interp(ic_, ts); j_ = j_save;
    v[ID] = interp(id_, ts); j_ = j_save;
    v[VSW] = interp(vsw_, ts);
    v[VBUS] = bus_V_;                                     // ideal source in the Simscape model
    v[VCE_CLAMP] = v[VCE] > clamp_V ? clamp_V : v[VCE];   // on-state clamp front end
    const int half = 1 << (adc_bits - 1);
    for (int k = 0; k < NUM_CH; ++k) {
        long c = std::lround(v[k] / fs[k] * half);
        if (c > half - 1) c = half - 1;
        if (c < -half) c = -half;
        f.code[k] = int16_t(c);
    }
    f.t_ns = t_ns;
    return true;
}

}  // namespace igbt

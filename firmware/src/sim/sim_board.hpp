// Virtual STM32G474 tester board for host simulation (software-in-the-loop).
// The "analogue world" is a MATLAB/Simscape record (results/<run>/dynamic_*.csv, SIMULATED data).
// The board samples it like the real front end would: fixed ADC rate, per-channel full scale,
// 12-bit bipolar quantisation, VCE clamp channel. It does not invent signals: every sample is an
// interpolation of the simulation record. The record is open-loop, so after a firmware trip the
// acquisition stops (the recorded device would not have seen the trip).
#pragma once
#include <cstdio>
#include <string>
#include <vector>

#include "hal.hpp"

namespace igbt {

class SimBoard : public IGate, public IAdc, public IFault {
public:
    // --- configuration (set before load/arm) ---
    double adc_rate_hz = 2e6;          // per-channel simultaneous sample rate (G474 ADC: up to 4 MS/s)
    int adc_bits = 12;
    double fs[NUM_CH] = {20, 100, 12, 100, 100, 20, 20};   // bipolar full scale per channel (engineering units)
    double clamp_V = 10.0;             // VCE_CLAMP on-state clamp level
    double inject_fault_us = -1;       // >= 0: assert driver FAULT input at this time (logic test signal only)

    bool load_csv(const char* path, double bus_V, std::string& err);
    void set_record_plan(const double edges_s[4]) { for (int k = 0; k < 4; ++k) rec_edges_s_[k] = edges_s[k]; have_rec_plan_ = true; }
    double record_end_s() const { return t_.empty() ? 0 : t_.back(); }
    size_t record_rows() const { return t_.size(); }
    std::string last_error;

    // IGate
    bool arm(const PulsePlan& plan) override;
    void force_off(uint64_t t_ns) override { if (!off_forced_) { off_forced_ = true; forced_at_ns_ = t_ns; } }
    bool commanded_on(uint64_t t_ns) const override;
    // IAdc
    bool next(AdcFrame& f) override;
    float lsb(Ch ch) const override { return float(fs[ch] / double(1 << (adc_bits - 1))); }
    // IFault
    bool asserted(uint64_t t_ns) const override { return inject_fault_us >= 0 && t_ns >= uint64_t(inject_fault_us * 1e3); }

private:
    double interp(const std::vector<double>& y, double ts);
    std::vector<double> t_, vge_, vce_, ic_, id_, vsw_;
    double bus_V_ = 0;
    double rec_edges_s_[4] = {0, 0, 0, 0};
    bool have_rec_plan_ = false;
    PulsePlan plan_{};
    bool armed_ = false, off_forced_ = false;
    uint64_t forced_at_ns_ = 0, n_ = 0;
    size_t j_ = 0;   // interpolation cursor (monotonic sampling)
};

}  // namespace igbt

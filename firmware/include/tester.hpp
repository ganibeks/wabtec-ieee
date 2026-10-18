// Portable tester core: double-pulse sequencing, on-line feature extraction, desaturation supervision.
// No heap, no exceptions, no I/O: compiles freestanding for Cortex-M4F and natively for the host simulator.
#pragma once
#include "hal.hpp"

namespace igbt {

struct Config {
    float bus_expected_V   = 48.0f;   // test-plan DC-link voltage
    float bus_tol_frac     = 0.05f;   // pre-check tolerance (test-plan setting, not a device limit)
    float gate_on_V        = 15.0f;   // Wabtec slides 5/8
    float gate_off_V       = -15.0f;
    float gate_tol_V       = 1.0f;
    float desat_thr_V      = 9.0f;    // ASSUMED typical gate-driver DESAT threshold
    float desat_blank_us   = 5.0f;    // ASSUMED blanking after each turn-on command
};

class Tester {
public:
    Tester(IGate& gate, IAdc& adc, IFault& fault, IReport& rep) : gate_(gate), adc_(adc), fault_(fault), rep_(rep) {}
    // Returns true when the sequence completed without a fault trip.
    bool run_double_pulse(const PulsePlan& plan, const Config& cfg);

private:
    IGate& gate_;
    IAdc& adc_;
    IFault& fault_;
    IReport& rep_;
};

}  // namespace igbt

// STM32G474 real-board backend — SKELETON. NOT COMPILED, NOT RUN, NOT VALIDATED in this project.
// Requires STM32CubeG4 (HAL + CMSIS), arm-none-eabi toolchain and a NUCLEO-G474RE plus an isolated
// gate-driver board with DESAT protection. It shows how the portable core maps onto the peripherals.
//
// Peripheral plan
//   HRTIM Timer A, output TA1 : double-pulse gate command (184 ps resolution); edges from PulsePlan
//   HRTIM FAULT1 input        : gate-driver /FAULT (DESAT) pin and COMP1 output -> hardware turn-off of TA1
//                               within the HRTIM fault path (no CPU involved). Firmware only reports it.
//   COMP1 + DAC3              : optional on-board Vce supervision threshold (backup to the driver DESAT)
//   ADC1..ADC5 (dual/regular) : VGE, VCE, VCE_CLAMP, VSW, VBUS, IC, ID; triggered by HRTIM ADC trigger,
//                               DMA circular buffer; 12-bit (up to 4 MS/s per ADC)
//   USB FS (CDC)              : same line protocol as src/sim/main_sim.cpp
// Safety note: the 10 us protection required by Wabtec slides 5/8 must be met by the driver DESAT path and the
// HRTIM fault input in hardware. The firmware never sits in that loop.
#if defined(STM32G474xx)
#include "stm32g4xx_hal.h"
#include "hal.hpp"

namespace igbt {

class Stm32Board : public IGate, public IAdc, public IFault {
public:
    explicit Stm32Board(HRTIM_HandleTypeDef* hrtim, ADC_HandleTypeDef* adc) : hrtim_(hrtim), adc_(adc) {}

    bool arm(const PulsePlan& plan) override {
        // TODO(hw): program HRTIM Timer A compare units for edge_ns[0..3] (set/reset events on TA1),
        //           single-shot (non-retriggerable) mode, enable FAULT1 on TA1, enable ADC trigger.
        plan_ = plan;
        return false;   // refuses until implemented and bench-validated
    }
    void force_off(uint64_t) override {
        // TODO(hw): software forced reset of TA1 output + disable outputs (HAL_HRTIM_WaveformOutputStop).
    }
    bool commanded_on(uint64_t t_ns) const override {
        int n = 0;
        for (uint32_t e : plan_.edge_ns) n += (t_ns >= e);
        return n % 2;
    }
    bool next(AdcFrame&) override {
        // TODO(hw): pop the next simultaneous frame from the DMA ring buffer; timestamp from the HRTIM ADC trigger count.
        return false;
    }
    float lsb(Ch) const override {
        // TODO(hw): calibrated volts/amps per code for each analogue front-end channel.
        return 0.0f;
    }
    bool asserted(uint64_t) const override {
        // TODO(hw): read HRTIM fault status flag (FLT1) — latched by hardware.
        return false;
    }

private:
    HRTIM_HandleTypeDef* hrtim_;
    ADC_HandleTypeDef* adc_;
    PulsePlan plan_{};
};

}  // namespace igbt
#endif

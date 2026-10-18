// Hardware abstraction for the IGBT bench tester firmware (target: STM32G474, Cortex-M4F).
// The tester core depends only on these interfaces. Two implementations exist:
//   src/sim/   - host "virtual board": replays a MATLAB/Simscape record through a modelled ADC (runs on a PC)
//   src/stm32/ - real-board skeleton (HRTIM / ADC+DMA / COMP break input); NOT built or run in this project
#pragma once
#include <stdint.h>
#include <stddef.h>

namespace igbt {

// Simultaneously sampled analogue channels of the tester front end.
enum Ch : uint8_t {
    VGE = 0,    // gate-emitter voltage
    VCE,        // collector-emitter, full-range divider
    VCE_CLAMP,  // collector-emitter through an on-state clamp (accurate low-voltage Vce(sat) channel)
    VSW,        // switch node (freewheel diode anode) to ground
    VBUS,       // DC-link voltage (diode cathode)
    IC,         // collector current sensor
    ID,         // freewheel diode current sensor
    NUM_CH
};

struct AdcFrame {
    uint64_t t_ns;            // sample time since sequence start
    int16_t code[NUM_CH];     // signed (bipolar) ADC codes
};

// Double pulse: ON at edge[0], OFF at edge[1], ON at edge[2], OFF at edge[3]; acquisition ends at stop.
struct PulsePlan {
    uint32_t edge_ns[4];
    uint32_t stop_ns;
};

class IGate {                 // gate-drive command output (HRTIM channel on the real board)
public:
    virtual bool arm(const PulsePlan& plan) = 0;        // false = plan rejected (reason via IReport)
    virtual void force_off(uint64_t t_ns) = 0;          // immediate turn-off command (fault path)
    virtual bool commanded_on(uint64_t t_ns) const = 0;
protected:
    ~IGate() = default;
};

class IAdc {                  // synchronous multi-channel ADC (ADC1..5 + DMA on the real board)
public:
    virtual bool next(AdcFrame& f) = 0;                 // false = end of acquisition
    virtual float lsb(Ch ch) const = 0;                 // engineering units per code
protected:
    ~IAdc() = default;
};

class IFault {                // gate-driver FAULT / DESAT output (COMP or GPIO -> HRTIM fault input)
public:
    virtual bool asserted(uint64_t t_ns) const = 0;
protected:
    ~IFault() = default;
};

class IReport {               // results sink (USB-CDC line protocol on the real board, stdout on the host)
public:
    virtual void event(const char* name, double t_us) = 0;
    virtual void meas(const char* key, double value, const char* unit, const char* note) = 0;
    virtual void status(const char* key, const char* value) = 0;
protected:
    ~IReport() = default;
};

}  // namespace igbt

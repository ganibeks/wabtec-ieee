// Host build of the tester firmware: line protocol on stdin/stdout, virtual board instead of hardware.
// The same text protocol is intended for the USB-CDC port of the real STM32G474 board.
//
//   PING                                   -> {"type":"pong",...}
//   LOAD <csv> <bus_V>                     (sim only) attach a MATLAB record; run with cwd = run folder
//   RECPLAN <e1_us> <e2_us> <e3_us> <e4_us> (sim only) pulse plan the record was generated with
//   PLAN <e1_us> <e2_us> <e3_us> <e4_us> <stop_us>
//   CFG <key> <value>                      bus_expected_V gate_on_V gate_off_V desat_thr_V desat_blank_us
//                                          adc_rate_hz fs_<CH> clamp_V inject_fault_us
//   RUN                                    execute double pulse, stream results, end with {"type":"done"}
//   QUIT
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

#include "sim_board.hpp"
#include "tester.hpp"

using namespace igbt;

namespace {

void jstr(const char* s) {   // minimal JSON string escaping
    std::putchar('"');
    for (; *s; ++s) {
        if (*s == '"' || *s == '\\') std::putchar('\\');
        if ((unsigned char)*s >= 0x20) std::putchar(*s);
    }
    std::putchar('"');
}

void jnum(double v) {
    if (v != v || v > 1e300 || v < -1e300) std::fputs("null", stdout);
    else std::printf("%.9g", v);
}

class StdoutReport : public IReport {
public:
    void event(const char* name, double t_us) override {
        std::fputs("{\"type\":\"event\",\"name\":", stdout); jstr(name);
        std::fputs(",\"t_us\":", stdout); jnum(t_us); std::fputs("}\n", stdout);
    }
    void meas(const char* key, double value, const char* unit, const char* note) override {
        std::fputs("{\"type\":\"meas\",\"key\":", stdout); jstr(key);
        std::fputs(",\"value\":", stdout); jnum(value);
        std::fputs(",\"unit\":", stdout); jstr(unit);
        std::fputs(",\"note\":", stdout); jstr(note); std::fputs("}\n", stdout);
    }
    void status(const char* key, const char* value) override {
        std::fputs("{\"type\":\"status\",\"key\":", stdout); jstr(key);
        std::fputs(",\"value\":", stdout); jstr(value); std::fputs("}\n", stdout);
    }
};

void reply_error(const std::string& m) {
    std::fputs("{\"type\":\"error\",\"message\":", stdout); jstr(m.c_str()); std::fputs("}\n", stdout);
}

}  // namespace

int main() {
    SimBoard board;
    StdoutReport rep;
    Config cfg;
    PulsePlan plan{};
    bool have_plan = false;
    char line[2048];
    while (std::fgets(line, sizeof line, stdin)) {
        char cmd[32] = {0};
        if (std::sscanf(line, "%31s", cmd) != 1) continue;
        const char* args = line + std::strlen(cmd);
        if (!std::strcmp(cmd, "PING")) {
            std::printf("{\"type\":\"pong\",\"firmware\":\"igbt-tester 0.1.0\",\"target\":\"SIM-HOST (virtual STM32G474)\","
                        "\"adc_bits\":%d,\"adc_rate_hz\":%.0f}\n", board.adc_bits, board.adc_rate_hz);
        } else if (!std::strcmp(cmd, "LOAD")) {
            char path[1024]; double bus;
            if (std::sscanf(args, "%1023s %lf", path, &bus) != 2) { reply_error("LOAD <csv> <bus_V>"); }
            else {
                std::string err;
                if (board.load_csv(path, bus, err))
                    std::printf("{\"type\":\"ok\",\"cmd\":\"LOAD\",\"rows\":%zu,\"end_us\":%.6f}\n", board.record_rows(), board.record_end_s() * 1e6);
                else reply_error(err);
            }
        } else if (!std::strcmp(cmd, "RECPLAN")) {
            double e[4];
            if (std::sscanf(args, "%lf %lf %lf %lf", e, e + 1, e + 2, e + 3) != 4) reply_error("RECPLAN e1 e2 e3 e4 (us)");
            else { for (double& x : e) x *= 1e-6; board.set_record_plan(e); std::puts("{\"type\":\"ok\",\"cmd\":\"RECPLAN\"}"); }
        } else if (!std::strcmp(cmd, "PLAN")) {
            double e[5];
            if (std::sscanf(args, "%lf %lf %lf %lf %lf", e, e + 1, e + 2, e + 3, e + 4) != 5) reply_error("PLAN e1 e2 e3 e4 stop (us)");
            else {
                for (int k = 0; k < 4; ++k) plan.edge_ns[k] = uint32_t(e[k] * 1e3 + 0.5);
                plan.stop_ns = uint32_t(e[4] * 1e3 + 0.5);
                have_plan = true; std::puts("{\"type\":\"ok\",\"cmd\":\"PLAN\"}");
            }
        } else if (!std::strcmp(cmd, "CFG")) {
            char key[64]; double v;
            if (std::sscanf(args, "%63s %lf", key, &v) != 2) { reply_error("CFG <key> <value>"); continue; }
            static const char* chn[NUM_CH] = {"VGE", "VCE", "VCE_CLAMP", "VSW", "VBUS", "IC", "ID"};
            bool ok = true;
            if (!std::strcmp(key, "bus_expected_V")) cfg.bus_expected_V = float(v);
            else if (!std::strcmp(key, "gate_on_V")) cfg.gate_on_V = float(v);
            else if (!std::strcmp(key, "gate_off_V")) cfg.gate_off_V = float(v);
            else if (!std::strcmp(key, "desat_thr_V")) cfg.desat_thr_V = float(v);
            else if (!std::strcmp(key, "desat_blank_us")) cfg.desat_blank_us = float(v);
            else if (!std::strcmp(key, "adc_rate_hz") && v >= 1e3 && v <= 4e6) board.adc_rate_hz = v;
            else if (!std::strcmp(key, "clamp_V")) board.clamp_V = v;
            else if (!std::strcmp(key, "inject_fault_us")) board.inject_fault_us = v;
            else if (!std::strncmp(key, "fs_", 3)) {
                ok = false;
                for (int k = 0; k < NUM_CH; ++k) if (!std::strcmp(key + 3, chn[k]) && v > 0) { board.fs[k] = v; ok = true; }
            } else ok = false;
            if (ok) std::printf("{\"type\":\"ok\",\"cmd\":\"CFG\",\"key\":\"%s\"}\n", key);
            else reply_error(std::string("unknown or out-of-range CFG key ") + key);
        } else if (!std::strcmp(cmd, "RUN")) {
            if (!have_plan) { reply_error("no PLAN"); std::puts("{\"type\":\"done\",\"ok\":false}"); }
            else {
                Tester tester(board, board, board, rep);
                const bool ok = tester.run_double_pulse(plan, cfg);
                if (!ok && !board.last_error.empty()) { reply_error(board.last_error); board.last_error.clear(); }
                std::printf("{\"type\":\"done\",\"ok\":%s}\n", ok ? "true" : "false");
            }
        } else if (!std::strcmp(cmd, "QUIT")) {
            break;
        } else {
            reply_error(std::string("unknown command ") + cmd);
        }
        std::fflush(stdout);
    }
    return 0;
}

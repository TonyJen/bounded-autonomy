// sensors.h — DHT temp/humidity (≤1 Hz, NaN → null), PIR motion edge,
// LDR light. SPEC §2.1 + electrical notes.
#pragma once
#include <Arduino.h>

struct SensorReadings {
  float temp_c;       // valid only when temp_ok
  float humidity_pct; // valid only when humidity_ok
  bool  temp_ok;
  bool  humidity_ok;
  int   light;        // raw ADC 0–4095, higher = brighter
  bool  motion;       // PIR level this cycle
};

void sensors_init();
void sensors_tick();                    // call every loop(); self-throttled
const SensorReadings& sensors_current();

// Event triggers since the last call: "motion" on PIR rising edge,
// "temp_threshold" on crossing 30 °C upward, "" when nothing fired.
// Only vocabulary triggers are ever produced (gateway validates).
String sensors_poll_event();

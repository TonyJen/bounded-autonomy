// actuators.h — one entry point for every command the gateway can send.
// Validation and clamps live HERE as well as in the gateway (defense in
// depth, SPEC §5 / thesis §3.8): the device never trusts the wire either.
#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>

struct ActuatorState {
  bool fan;
  int  servo_deg;
  uint8_t led_r, led_g, led_b;
  bool buzzer;
  String oled[2];
};

void actuators_init();
const ActuatorState& actuators_state();

// Execute one command envelope's action+args. Returns ok; on failure
// *err* is set and nothing physical happens beyond safe clamps.
bool actuators_execute(const char* action, JsonVariantConst args,
                       String* err);

// Degraded safe state: fan off, LED amber, OLED "OFFLINE" (SPEC §11).
void actuators_safe_state();

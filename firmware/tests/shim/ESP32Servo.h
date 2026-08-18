// Host-test shim for ESP32Servo: records attach/write/detach so tests can
// assert the clamp and the detach-after-move behavior (SPEC §2 notes).
#pragma once

extern int servo_attach_count;
extern int servo_last_deg;
extern int servo_detach_count;

class Servo {
public:
  void attach(int /*pin*/) { servo_attach_count++; }
  void write(int deg) { servo_last_deg = deg; }
  void detach() { servo_detach_count++; }
};

// bounded_autonomy.ino — main loop. SENSE → report → ACT, nothing more:
// the device cannot parse a prompt and holds no cloud key (thesis §3.1).
//
// Cadence: heartbeat every HEARTBEAT_S, events immediately, command poll
// every POLL_MS. Watchdog: no gateway contact for OFFLINE_AFTER_S →
// safe state (SPEC §11).
#include "config.h"
#include "sensors.h"
#include "actuators.h"
#include "net.h"

static unsigned long last_heartbeat_ms = 0;
static unsigned long last_poll_ms = 0;
static bool offline = false;

void setup() {
  Serial.begin(115200);
  sensors_init();
  actuators_init();
  net_init();
  Serial.println("[ba] boot " DEVICE_ID);
}

void loop() {
  sensors_tick();

  if (!net_ensure_wifi()) {
    delay(50);
    return;
  }

  // events fire immediately; heartbeats on cadence
  String event = sensors_poll_event();
  if (!event.isEmpty()) {
    if (net_send_sense("event", event.c_str(), sensors_current())) {
      Serial.println("[ba] event sent: " + event);
    }
  } else if (millis() - last_heartbeat_ms >= (unsigned long)HEARTBEAT_S * 1000) {
    last_heartbeat_ms = millis();
    if (net_send_sense("heartbeat", "periodic", sensors_current())) {
      Serial.println("[ba] heartbeat ack");
    }
  }

  if (millis() - last_poll_ms >= POLL_MS) {
    last_poll_ms = millis();
    net_poll_commands();
  }
  net_service_push();

  // offline watchdog (SPEC §11): fail quiet, keep retrying
  bool is_offline = net_seconds_since_contact() > OFFLINE_AFTER_S;
  if (is_offline != offline) {
    offline = is_offline;
    if (offline) {
      actuators_safe_state();
      Serial.println("[ba] gateway lost — safe state");
    } else {
      Serial.println("[ba] gateway contact restored");
    }
  }

  delay(POLL_MS / 4);  // responsive PIR edges without busy-spinning
}

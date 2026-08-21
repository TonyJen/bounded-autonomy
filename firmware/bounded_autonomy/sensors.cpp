// sensors.cpp — see header. DHT11 max 1 Hz sampling: reads are cached,
// never polled faster (SPEC §2 electrical notes).
#include "sensors.h"
#include "config.h"
#include <DHT.h>

#define PIN_DHT   4
#define PIN_PIR   5
#define PIN_LDR   34   // input-only, no pull-up — correct for the divider

#define DHT_MIN_INTERVAL_MS 1100   // DHT11: 1 Hz max, with margin
#define TEMP_EVENT_C        30.0   // crossing this upward fires an event

static DHT dht(PIN_DHT, DHT_TYPE);
static SensorReadings cur = {NAN, NAN, false, false, 0, false};
// Start "one interval in the past" so the FIRST tick samples immediately
// (unsigned wraparound idiom) — otherwise a fast boot+heartbeat ships
// stale invalid readings.
static unsigned long last_dht_ms = (unsigned long)-DHT_MIN_INTERVAL_MS;
static bool prev_motion = false;
static bool prev_hot = false;
static String pending_event = "";

void sensors_init() {
  dht.begin();
  pinMode(PIN_PIR, INPUT);
  pinMode(PIN_LDR, INPUT);
}

void sensors_tick() {
  unsigned long now = millis();
  if (now - last_dht_ms >= DHT_MIN_INTERVAL_MS) {
    last_dht_ms = now;
    float t = dht.readTemperature();
    float h = dht.readHumidity();
    // NaN is a failed read: report null, never a guessed number.
    cur.temp_ok = !isnan(t);
    cur.humidity_ok = !isnan(h);
    if (cur.temp_ok) cur.temp_c = t;
    if (cur.humidity_ok) cur.humidity_pct = h;
  }
  cur.light = analogRead(PIN_LDR);
  cur.motion = digitalRead(PIN_PIR) == HIGH;

  if (cur.motion && !prev_motion) pending_event = "motion";
  bool hot = cur.temp_ok && cur.temp_c >= TEMP_EVENT_C;
  if (hot && !prev_hot) pending_event = "temp_threshold";
  prev_motion = cur.motion;
  prev_hot = hot;
}

const SensorReadings& sensors_current() { return cur; }

String sensors_poll_event() {
  String e = pending_event;
  pending_event = "";
  return e;
}

// net.h — WiFi + the SPEC §2 device protocol: POST /sense, poll
// /commands, ack, and the push receiver. Gateway time is authoritative;
// the device never embeds wall-clock timestamps (SPEC §2.5) — it also
// cannot evaluate ttl_s, so commands are executed on receipt and the
// gateway's queue owns expiry.
#pragma once
#include <Arduino.h>
#include "sensors.h"

void net_init();
bool net_ensure_wifi();                 // reconnect with backoff

// POST one snapshot. type: "heartbeat"|"event". Returns true on HTTP 200
// (and counts as gateway contact for the watchdog).
bool net_send_sense(const char* type, const char* trigger,
                    const SensorReadings& s);

// Poll + execute + ack pending commands. Returns count executed.
int net_poll_commands();

// Service the push receiver (POST /command on :8080). Call every loop.
void net_service_push();

// Seconds since the last successful gateway exchange (for the watchdog).
unsigned long net_seconds_since_contact();

// Host-test shim for the DHT sensor library. Values and read counts are
// test-controllable; NaN simulates a failed read.
#pragma once
#include "Arduino.h"

#define DHT11 11
#define DHT22 22

extern float dht_temp;        // set to NAN for a failed read
extern float dht_hum;
extern int dht_temp_reads;    // how often the firmware actually sampled
extern int dht_hum_reads;

class DHT {
public:
  DHT(int /*pin*/, int /*type*/) {}
  void begin() {}
  float readTemperature() { dht_temp_reads++; return dht_temp; }
  float readHumidity() { dht_hum_reads++; return dht_hum; }
};

// Host-test shim for WiFi: always-connected STA, a WiFiServer whose
// available() yields no client by default (push path not exercised in
// host tests), and a WiFiClient with just enough stream surface.
#pragma once
#include "Arduino.h"

#define WL_CONNECTED 3
#define WIFI_STA 1

class WiFiClient {
public:
  explicit operator bool() const { return valid_; }
  void setValid(bool v) { valid_ = v; }
  void setTimeout(int) {}
  String readStringUntil(char) { return ""; }
  String readString() { return ""; }
  void print(const char*) {}
  void print(const String&) {}
  void stop() {}
private:
  bool valid_ = false;
};

class WiFiServer {
public:
  explicit WiFiServer(int) {}
  void begin() {}
  WiFiClient available() { return WiFiClient(); }
};

extern int wifi_status;

class WiFiClass {
public:
  void mode(int) {}
  void begin(const char*, const char*) {}
  int status() { return wifi_status; }
  void disconnect() {}
};
extern WiFiClass WiFi;

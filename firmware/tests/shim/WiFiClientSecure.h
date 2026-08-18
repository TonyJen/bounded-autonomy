// Host-test shim for WiFiClientSecure (emulation TLS profile).
#pragma once
#include "WiFi.h"

class WiFiClientSecure : public WiFiClient {
public:
  void setInsecure() {}
};

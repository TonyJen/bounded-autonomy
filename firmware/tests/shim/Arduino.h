// Host-test shim for the Arduino core API — just enough surface for the
// firmware modules to compile and run under a desktop compiler, with all
// hardware state fake-able and observable from tests.
#pragma once
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cmath>
#include <string>
#include <vector>
#include <map>

// ---- String: Arduino String over std::string --------------------------
class String : public std::string {
public:
  using std::string::string;
  String(const std::string& o) : std::string(o) {}
  String(int v) : std::string(std::to_string(v)) {}
  String(long v) : std::string(std::to_string(v)) {}
  String(unsigned long v) : std::string(std::to_string(v)) {}
  const char* c_str() const { return data(); }
  bool isEmpty() const { return empty(); }
  bool startsWith(const char* p) const { return rfind(p, 0) == 0; }
  String substring(int from) const { return String(substr(from)); }
  String substring(int from, int to) const { return String(substr(from, to - from)); }
  void trim() {
    auto b = find_first_not_of(" \t\r\n");
    auto e = find_last_not_of(" \t\r\n");
    assign(b == npos ? "" : substr(b, e - b + 1));
  }
  void remove(int idx) { if (idx >= 0 && (size_t)idx < size()) resize(idx); }
  // ArduinoJson's primary Writer forwards to these on the destination.
  size_t write(uint8_t c) { push_back((char)c); return 1; }
  size_t write(const uint8_t* s, size_t n) { append((const char*)s, n); return n; }
};
inline String operator+(const String& a, const char* b) { String r(a); r += b; return r; }
inline String operator+(const String& a, const String& b) { String r(a); r += b; return r; }

// ---- pins / time --------------------------------------------------------
#define INPUT 0
#define OUTPUT 1
#define LOW 0
#define HIGH 1
#define constrain(amt, low, high) ((amt) < (low) ? (low) : ((amt) > (high) ? (high) : (amt)))

using std::isnan;

unsigned long millis();
void delay(unsigned long ms);

void pinMode(int pin, int mode);
void digitalWrite(int pin, int val);
int  digitalRead(int pin);
void analogWrite(int pin, int val);
int  analogRead(int pin);

// test controls (defined in shim.cpp)
extern unsigned long fake_millis;
void advance_millis(unsigned long ms);
extern int pin_digital_write[64];
extern int pin_analog_write[64];
extern int pin_digital_read[64];
extern int pin_analog_read[64];
void shim_reset_pins();

struct SerialStub {
  template <typename T> void println(const T&) {}
  template <typename T> void print(const T&) {}
};
extern SerialStub Serial;

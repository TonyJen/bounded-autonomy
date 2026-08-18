// Fake hardware + network state for the host shims.
#include "Arduino.h"
#include "DHT.h"
#include "ESP32Servo.h"
#include "U8g2lib.h"
#include "HTTPClient.h"

unsigned long fake_millis = 0;
int pin_digital_write[64] = {0};
int pin_analog_write[64] = {0};
int pin_digital_read[64] = {0};
int pin_analog_read[64] = {0};
SerialStub Serial;

unsigned long millis() { return fake_millis; }
void delay(unsigned long ms) { fake_millis += ms; }
void advance_millis(unsigned long ms) { fake_millis += ms; }

void pinMode(int, int) {}
void digitalWrite(int pin, int val) { pin_digital_write[pin] = val; }
int  digitalRead(int pin) { return pin_digital_read[pin]; }
void analogWrite(int pin, int val) { pin_analog_write[pin] = val; }
int  analogRead(int pin) { return pin_analog_read[pin]; }

void shim_reset_pins() {
  for (int i = 0; i < 64; i++) {
    pin_digital_write[i] = pin_analog_write[i] = 0;
    pin_digital_read[i] = pin_analog_read[i] = 0;
  }
}

float dht_temp = 22.0f;
float dht_hum = 45.0f;
int dht_temp_reads = 0;
int dht_hum_reads = 0;

int servo_attach_count = 0;
int servo_last_deg = -1;
int servo_detach_count = 0;

std::vector<std::string> oled_draws;

int wifi_status = WL_CONNECTED;
WiFiClass WiFi;

// ---- HTTP stub registry -------------------------------------------------
static std::map<std::string, HttpStub> stubs;
std::vector<HttpRequest> http_requests;

void http_reset() {
  stubs.clear();
  http_requests.clear();
}

void http_stub(const char* url_substr, int code, const char* body) {
  stubs[url_substr] = {code, body};
}

static const HttpStub* find_stub(const std::string& url) {
  auto exact = stubs.find(url);
  if (exact != stubs.end()) return &exact->second;
  const HttpStub* best = nullptr;
  size_t best_len = 0;
  for (const auto& kv : stubs) {
    if (url.find(kv.first) != std::string::npos && kv.first.size() > best_len) {
      best = &kv.second;
      best_len = kv.first.size();
    }
  }
  return best;
}

int HTTPClient::request(const char* method, const char* body) {
  http_requests.push_back({method, url_.c_str(), body, token_});
  const HttpStub* s = find_stub(url_.c_str());
  if (!s) { stream_.str(""); stream_.clear(); return -1; }
  stream_.str(s->body);
  stream_.clear();
  return s->code;
}

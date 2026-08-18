// net.cpp — see header. Poll is the reliable path everywhere; the push
// receiver is for LAN hardware (and is simply unreachable under free-tier
// Wokwi, where the device sits behind the tunnel's egress IP).
#include "net.h"
#include "actuators.h"
#include "config.h"
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

#define PUSH_PORT 8080
#define HTTP_TIMEOUT_MS 10000
#define WIFI_RETRY_BACKOFF_MS 5000

static WiFiServer server(PUSH_PORT);
static unsigned long last_contact_ms = 0;
static unsigned long last_wifi_attempt_ms = 0;
static unsigned long seq = 0;
static long last_cmd_row = 0;   // poll cursor ("after")

static void note_contact() { last_contact_ms = millis(); }

unsigned long net_seconds_since_contact() {
  if (last_contact_ms == 0) return 1UL << 30;  // never contacted
  return (millis() - last_contact_ms) / 1000;
}

void net_init() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  server.begin();
}

bool net_ensure_wifi() {
  if (WiFi.status() == WL_CONNECTED) return true;
  unsigned long now = millis();
  if (now - last_wifi_attempt_ms < WIFI_RETRY_BACKOFF_MS) return false;
  last_wifi_attempt_ms = now;
  WiFi.disconnect();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  return false;
}

static void begin_client(HTTPClient& http, WiFiClient& plain,
                         WiFiClientSecure& tls, const String& url) {
#if USE_TLS
  tls.setInsecure();  // emulation only — see config.h
  http.begin(tls, url);
#else
  http.begin(plain, url);
#endif
  http.setTimeout(HTTP_TIMEOUT_MS);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Token", DEVICE_TOKEN);
}

bool net_send_sense(const char* type, const char* trigger,
                    const SensorReadings& s) {
  const ActuatorState& a = actuators_state();
  JsonDocument doc;
  doc["device_id"] = DEVICE_ID;
  doc["type"] = type;
  doc["trigger"] = trigger;
  doc["seq"] = ++seq;
  doc["uptime_s"] = millis() / 1000;
  JsonObject sensors = doc["sensors"].to<JsonObject>();
  if (s.temp_ok) sensors["temp_c"] = s.temp_c; else sensors["temp_c"] = nullptr;
  if (s.humidity_ok) sensors["humidity_pct"] = s.humidity_pct;
  else sensors["humidity_pct"] = nullptr;
  sensors["light"] = s.light;
  sensors["motion"] = s.motion;
  JsonObject act = doc["actuators"].to<JsonObject>();
  act["fan"] = a.fan;
  act["servo_deg"] = a.servo_deg;
  JsonObject led = act["led"].to<JsonObject>();
  led["r"] = a.led_r; led["g"] = a.led_g; led["b"] = a.led_b;
  act["buzzer"] = a.buzzer;
  JsonArray oled = act["oled"].to<JsonArray>();
  oled.add(a.oled[0]); oled.add(a.oled[1]);

  String body;
  serializeJson(doc, body);

  WiFiClient plain;
  WiFiClientSecure tls;
  HTTPClient http;
  begin_client(http, plain, tls, String(GATEWAY_URL) + "/sense");
  int code = http.POST(body);
  http.end();
  if (code == 200) { note_contact(); return true; }
  return false;
}

// Shared by poll and push: parse one envelope, execute, return the error
// string ("" on success).
static String handle_command(JsonObjectConst cmd) {
  const char* action = cmd["action"] | "";
  JsonVariantConst args = cmd["args"];
  String err;
  bool ok = actuators_execute(action, args, &err);
  return ok ? "" : err;
}

static void ack(const char* cmd_id, const String& err) {
  JsonDocument doc;
  if (err.isEmpty()) doc["ok"] = true;
  else { doc["ok"] = false; doc["error"] = err; }
  String body;
  serializeJson(doc, body);
  WiFiClient plain;
  WiFiClientSecure tls;
  HTTPClient http;
  begin_client(http, plain, tls,
               String(GATEWAY_URL) + "/commands/" + cmd_id + "/ack");
  int code = http.POST(body);
  http.end();
  if (code == 200) note_contact();
}

int net_poll_commands() {
  WiFiClient plain;
  WiFiClientSecure tls;
  HTTPClient http;
  begin_client(http, plain, tls,
               String(GATEWAY_URL) + "/commands?device_id=" + DEVICE_ID +
               "&after=" + String(last_cmd_row));
  int code = http.GET();
  if (code != 200) { http.end(); return 0; }
  note_contact();
  JsonDocument doc;
  DeserializationError jerr = deserializeJson(doc, http.getStream());
  http.end();
  if (jerr) return 0;

  int executed = 0;
  for (JsonObjectConst cmd : doc["commands"].as<JsonArray>()) {
    long row = cmd["id"] | last_cmd_row;
    const char* cmd_id = cmd["cmd_id"] | "";
    String err = handle_command(cmd);
    ack(cmd_id, err);
    if (row > last_cmd_row) last_cmd_row = row;
    executed++;
  }
  return executed;
}

void net_service_push() {
  WiFiClient client = server.available();
  if (!client) return;
  client.setTimeout(2000);
  String head = client.readStringUntil('\r');  // request line
  bool is_command = head.startsWith("POST /command");
  String token = "";
  while (true) {  // headers
    String line = client.readStringUntil('\n');
    if (line == "\r" || line.isEmpty()) break;
    if (line.startsWith("X-Device-Token: ")) {
      token = line.substring(16);
      token.trim();
    }
  }
  String body = client.readString();
  bool authorized = (token == DEVICE_TOKEN);
  String err = "unauthorized";
  if (is_command && authorized) {
    JsonDocument doc;
    if (!deserializeJson(doc, body)) {
      err = handle_command(doc.as<JsonObjectConst>());
      // best-effort ack; poll path dedupes by cmd_id
      ack(doc["cmd_id"] | "", err);
    } else {
      err = "bad json";
    }
  }
  client.print("HTTP/1.1 ");
  client.print(err.isEmpty() ? "200 OK" : "400 Bad Request");
  client.print("\r\nContent-Type: application/json\r\n\r\n{\"ok\":");
  client.print(err.isEmpty() ? "true" : "false");
  client.print("}");
  client.stop();
  if (err.isEmpty()) note_contact();
}

// Host unit tests for the Grok Guardian firmware modules, compiled with a
// desktop C++ compiler against the shim in shim/. These characterize the
// firmware's contract with the gateway: snapshot shape, event triggers,
// command clamps, ack behavior, poll cursor.
//
// Run: firmware/tests/run_tests.ps1
#include "Arduino.h"
#include "DHT.h"
#include "ESP32Servo.h"
#include "U8g2lib.h"
#include "HTTPClient.h"

#include "sensors.h"
#include "actuators.h"
#include "net.h"
#include "config.h"

static int checks = 0, failures = 0;
#define CHECK(cond) do { checks++; if (!(cond)) { failures++; \
  std::printf("FAIL %d: %s\n", __LINE__, #cond); } } while (0)

static JsonDocument parse(const std::string& s) {
  JsonDocument doc;
  deserializeJson(doc, s);
  return doc;
}

// ---------------------------------------------------------------- sensors
static void test_sensors() {
  sensors_init();

  // valid read flows through
  dht_temp = 22.5f; dht_hum = 41.0f;
  sensors_tick();
  CHECK(sensors_current().temp_ok);
  CHECK(sensors_current().temp_c == 22.5f);

  // throttling: a second tick inside the window must NOT re-sample
  int reads = dht_temp_reads;
  dht_temp = 30.5f;
  advance_millis(500);
  sensors_tick();
  CHECK(dht_temp_reads == reads);                 // no new sample taken
  CHECK(sensors_current().temp_c == 22.5f);       // cached value served

  // after the DHT11-safe interval, the new sample lands
  advance_millis(1200);
  sensors_tick();
  CHECK(sensors_current().temp_c == 30.5f);

  // NaN is a failed read -> invalid, never a guessed number
  dht_temp = NAN;
  advance_millis(1200);
  sensors_tick();
  CHECK(!sensors_current().temp_ok);

  // PIR rising edge fires exactly one "motion" event
  dht_temp = 25.0f;
  pin_digital_read[5] = HIGH;
  advance_millis(1200);
  sensors_tick();
  CHECK(sensors_poll_event() == "motion");
  CHECK(sensors_poll_event() == "");              // latched, not repeated
  pin_digital_read[5] = LOW;                      // re-arm
  advance_millis(1200); sensors_tick();
  CHECK(sensors_poll_event() == "");

  // temperature crossing 30 °C upward fires once, then holds
  advance_millis(1200); sensors_tick();           // 25 °C, no motion
  dht_temp = 31.0f;
  advance_millis(1200); sensors_tick();
  CHECK(sensors_poll_event() == "temp_threshold");
  dht_temp = 32.0f;
  advance_millis(1200); sensors_tick();
  CHECK(sensors_poll_event() == "");              // no chatter while hot
}

// -------------------------------------------------------------- actuators
static void test_actuators() {
  actuators_init();
  String err;

  // fan
  {
    JsonDocument a; deserializeJson(a, R"({"on":true})");
    CHECK(actuators_execute("set_fan", a.as<JsonVariantConst>(), &err));
    CHECK(pin_digital_write[19] == HIGH);
    CHECK(actuators_state().fan);
  }
  {
    JsonDocument a; deserializeJson(a, R"({"on":false})");
    CHECK(actuators_execute("set_fan", a.as<JsonVariantConst>(), &err));
    CHECK(pin_digital_write[19] == LOW);
  }

  // servo clamps to 0–90 and detaches after the move
  {
    JsonDocument a; deserializeJson(a, R"({"angle":200})");
    int detaches = servo_detach_count;
    CHECK(actuators_execute("set_servo", a.as<JsonVariantConst>(), &err));
    CHECK(servo_last_deg == 90);
    CHECK(actuators_state().servo_deg == 90);
    CHECK(servo_detach_count == detaches + 1);
  }
  {
    JsonDocument a; deserializeJson(a, R"({"angle":-10})");
    CHECK(actuators_execute("set_servo", a.as<JsonVariantConst>(), &err));
    CHECK(servo_last_deg == 0);
  }

  // LED colors; unknown color is an error, not a guess
  {
    JsonDocument a; deserializeJson(a, R"({"color":"amber"})");
    CHECK(actuators_execute("set_led", a.as<JsonVariantConst>(), &err));
    CHECK(pin_analog_write[25] == 255 && pin_analog_write[26] == 128);
  }
  {
    JsonDocument a; deserializeJson(a, R"({"color":"chartreuse"})");
    CHECK(!actuators_execute("set_led", a.as<JsonVariantConst>(), &err));
    CHECK(err == "unknown color");
  }

  // buzzer rejects unknown patterns without making noise
  {
    JsonDocument a; deserializeJson(a, R"({"pattern":"marathon"})");
    CHECK(!actuators_execute("buzzer", a.as<JsonVariantConst>(), &err));
    CHECK(pin_digital_write[23] == LOW);
  }

  // OLED lines truncate to 16 chars, mirroring the gateway guardrail
  {
    JsonDocument a; deserializeJson(a,
        R"({"line1":"this line is far too long for the oled","line2":"ok"})");
    CHECK(actuators_execute("display_text", a.as<JsonVariantConst>(), &err));
    CHECK(actuators_state().oled[0].length() == 16);
    CHECK(actuators_state().oled[1] == "ok");
  }

  // log_observation is a no-op on the device; unknown actions error
  {
    JsonDocument a; deserializeJson(a, R"({"note":"hi"})");
    CHECK(actuators_execute("log_observation", a.as<JsonVariantConst>(), &err));
  }
  {
    JsonDocument a; deserializeJson(a, R"({})");
    CHECK(!actuators_execute("launch_rocket", a.as<JsonVariantConst>(), &err));
    CHECK(err == "unknown action");
  }

  // safe state: fan off, amber, OFFLINE on the display
  actuators_safe_state();
  CHECK(pin_digital_write[19] == LOW);
  CHECK(pin_analog_write[25] == 255 && pin_analog_write[26] == 128);
  CHECK(actuators_state().oled[0] == "OFFLINE");
}

// ---------------------------------------------------------------------- net
static void test_net() {
  net_init();
  http_reset();
  shim_reset_pins();
  actuators_init();

  const String base = GATEWAY_URL;
  http_stub((base + "/sense").c_str(), 200, R"({"accepted":true})");
  http_stub((base + "/commands?device_id=" + DEVICE_ID + "&after=0").c_str(),
            200, R"({"commands":[
              {"id":5,"cmd_id":"c5","action":"set_fan","args":{"on":true}},
              {"id":7,"cmd_id":"c7","action":"set_servo","args":{"angle":45}}]})");
  http_stub((base + "/commands?device_id=" + DEVICE_ID + "&after=7").c_str(),
            200, R"({"commands":[]})");
  http_stub("/ack", 200, "{}");

  // snapshot: nulls for failed reads, bool motion, seq increments
  SensorReadings s = {NAN, 41.0f, false, true, 612, false};
  CHECK(net_send_sense("heartbeat", "periodic", s));
  CHECK(net_send_sense("event", "motion", s));
  CHECK(http_requests.size() == 2);
  {
    JsonDocument body = parse(http_requests[0].body);
    CHECK(body["device_id"] == DEVICE_ID);
    CHECK(body["type"] == "heartbeat");
    CHECK(body["trigger"] == "periodic");
    CHECK(body["seq"] == 1);
    CHECK(body["sensors"]["temp_c"].isNull());    // failed read -> null
    CHECK(body["sensors"]["humidity_pct"] == 41.0f);
    CHECK(body["sensors"]["light"] == 612);
    CHECK(body["sensors"]["motion"] == false);
    CHECK(http_requests[0].token == DEVICE_TOKEN);
    JsonDocument body2 = parse(http_requests[1].body);
    CHECK(body2["seq"] == 2);                     // gap detection input
    CHECK(body2["trigger"] == "motion");
  }

  // poll: both commands executed and acked, cursor advanced
  size_t before = http_requests.size();
  CHECK(net_poll_commands() == 2);
  CHECK(pin_digital_write[19] == HIGH);           // set_fan executed
  CHECK(servo_last_deg == 45);                    // set_servo executed
  CHECK(http_requests.size() == before + 3);      // 1 GET + 2 acks
  {
    const HttpRequest& ack1 = http_requests[before + 1];
    const HttpRequest& ack2 = http_requests[before + 2];
    CHECK(ack1.url.find("/commands/c5/ack") != std::string::npos);
    CHECK(parse(ack1.body)["ok"] == true);
    CHECK(ack2.url.find("/commands/c7/ack") != std::string::npos);
    CHECK(parse(ack2.body)["ok"] == true);
  }

  // second poll uses the advanced cursor and finds nothing
  before = http_requests.size();
  CHECK(net_poll_commands() == 0);
  CHECK(http_requests[before].url.find("after=7") != std::string::npos);

  // malformed poll response: no execution, no ack, no crash
  http_stub((base + "/commands?device_id=" + DEVICE_ID + "&after=7").c_str(),
            200, "not json{");
  before = http_requests.size();
  CHECK(net_poll_commands() == 0);
  CHECK(http_requests.size() == before + 1);      // the GET only

  // watchdog clock: contact just happened, so we're "online"
  CHECK(net_seconds_since_contact() < 5);
}

int main() {
  test_sensors();
  test_actuators();
  test_net();
  std::printf("%d checks, %d failures\n", checks, failures);
  return failures ? 1 : 0;
}

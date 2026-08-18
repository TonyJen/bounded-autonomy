// actuators.cpp — see header. Physical clamps mirror the gateway's
// guardrails so a fault in either layer alone cannot exceed a budget.
#include "actuators.h"
#include <ESP32Servo.h>
#include <U8g2lib.h>

#define PIN_SERVO  18
#define PIN_FAN    19
#define PIN_BUZZER 23
#define PIN_LED_R  25
#define PIN_LED_G  26
#define PIN_LED_B  27

// Kit boards vary (SPEC library table): SSD1306 or SH1106, pick at bench.
static U8G2_SSD1306_128X64_NONAME_F_HW_I2C oled(
    U8G2_R0, /* reset=*/ U8X8_PIN_NONE);

static Servo servo;
static ActuatorState st = {false, 0, 0, 0, 0, false, {"GrokGuardian", "boot"}};

static void led(uint8_t r, uint8_t g, uint8_t b) {
  st.led_r = r; st.led_g = g; st.led_b = b;
  analogWrite(PIN_LED_R, r);
  analogWrite(PIN_LED_G, g);
  analogWrite(PIN_LED_B, b);
}

static void oled_show() {
  oled.clearBuffer();
  oled.setFont(u8g2_font_6x12_tr);
  oled.drawStr(0, 16, st.oled[0].c_str());
  oled.drawStr(0, 36, st.oled[1].c_str());
  oled.sendBuffer();
}

void actuators_init() {
  pinMode(PIN_FAN, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_LED_R, OUTPUT);
  pinMode(PIN_LED_G, OUTPUT);
  pinMode(PIN_LED_B, OUTPUT);
  digitalWrite(PIN_FAN, LOW);
  digitalWrite(PIN_BUZZER, LOW);
  led(0, 0, 0);
  oled.begin();
  oled_show();
}

const ActuatorState& actuators_state() { return st; }

static bool set_led(JsonVariantConst args, String* err) {
  const char* color = args["color"] | "";
  if      (!strcmp(color, "off"))   led(0, 0, 0);
  else if (!strcmp(color, "red"))   led(255, 0, 0);
  else if (!strcmp(color, "green")) led(0, 255, 0);
  else if (!strcmp(color, "blue"))  led(0, 0, 255);
  else if (!strcmp(color, "white")) led(255, 255, 255);
  else if (!strcmp(color, "amber")) led(255, 128, 0);
  else { *err = "unknown color"; return false; }
  return true;
}

static bool buzzer(JsonVariantConst args, String* err) {
  const char* pattern = args["pattern"] | "short";
  st.buzzer = true;
  if (!strcmp(pattern, "short")) {
    digitalWrite(PIN_BUZZER, HIGH); delay(100);
  } else if (!strcmp(pattern, "double")) {
    for (int i = 0; i < 2; i++) {
      digitalWrite(PIN_BUZZER, HIGH); delay(100);
      digitalWrite(PIN_BUZZER, LOW);  delay(100);
    }
  } else if (!strcmp(pattern, "siren")) {
    // Bounded by the gateway to 3 s within a 10 s/hr budget; the 3 s cap
    // is duplicated here so the wire alone can never extend it.
    digitalWrite(PIN_BUZZER, HIGH); delay(3000);
  } else {
    st.buzzer = false;
    *err = "unknown pattern"; return false;
  }
  digitalWrite(PIN_BUZZER, LOW);
  st.buzzer = false;
  return true;
}

bool actuators_execute(const char* action, JsonVariantConst args,
                       String* err) {
  if (!strcmp(action, "set_fan")) {
    st.fan = args["on"] | false;
    digitalWrite(PIN_FAN, st.fan ? HIGH : LOW);
    return true;
  }
  if (!strcmp(action, "set_servo")) {
    int deg = constrain(args["angle"] | 0, 0, 90);  // clamp, don't reject
    st.servo_deg = deg;
    servo.attach(PIN_SERVO);
    servo.write(deg);
    delay(400);          // let it travel, then stop holding (SPEC §2:
    servo.detach();      // detach kills SG90 jitter and idle current)
    return true;
  }
  if (!strcmp(action, "set_led")) return set_led(args, err);
  if (!strcmp(action, "buzzer"))  return buzzer(args, err);
  if (!strcmp(action, "display_text")) {
    st.oled[0] = (const char*)(args["line1"] | "");
    st.oled[0].remove(16);
    st.oled[1] = (const char*)(args["line2"] | "");
    st.oled[1].remove(16);
    oled_show();
    return true;
  }
  if (!strcmp(action, "log_observation")) return true;  // gateway-side record
  *err = "unknown action";
  return false;
}

void actuators_safe_state() {
  st.fan = false;
  digitalWrite(PIN_FAN, LOW);
  led(255, 128, 0);  // amber
  st.oled[0] = "OFFLINE";
  st.oled[1] = "retrying...";
  oled_show();
}

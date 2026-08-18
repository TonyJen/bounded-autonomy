// Host-test shim for U8g2: captures drawn strings for assertions.
#pragma once
#include <vector>
#include <string>

#define U8G2_R0 0
#define U8X8_PIN_NONE (-1)
#define u8g2_font_6x12_tr nullptr

extern std::vector<std::string> oled_draws;

class U8G2_SSD1306_128X64_NONAME_F_HW_I2C {
public:
  template <typename A, typename B> U8G2_SSD1306_128X64_NONAME_F_HW_I2C(A, B) {}
  void begin() {}
  void clearBuffer() { oled_draws.clear(); }
  void setFont(const void*) {}
  void drawStr(int, int, const char* s) { oled_draws.emplace_back(s); }
  void sendBuffer() {}
};

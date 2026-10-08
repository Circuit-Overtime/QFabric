#include <Arduino_LED_Matrix.h>
#include <Arduino_RouterBridge.h>

Arduino_LED_Matrix qf_matrix;

constexpr size_t QF_MATRIX_ROWS = 8;
constexpr size_t QF_MATRIX_COLUMNS = 13;
constexpr size_t QF_MATRIX_PIXELS = QF_MATRIX_ROWS * QF_MATRIX_COLUMNS;

uint8_t qf_frame[QF_MATRIX_PIXELS] = {};

String qf_stage1_echo(String payload) {
  return payload;
}

uint32_t qf_stage1_micros() {
  return micros();
}

uint32_t qf_stage1_matrix_draw(uint32_t seed) {
  for (size_t index = 0; index < QF_MATRIX_PIXELS; ++index) {
    qf_frame[index] = static_cast<uint8_t>((seed + index) & 0x07U);
  }

  const uint32_t started = micros();
  qf_matrix.draw(qf_frame);
  return micros() - started;
}

void setup() {
  qf_matrix.begin();
  qf_matrix.setGrayscaleBits(3);
  qf_matrix.clear();

  if (!Bridge.begin()) {
    while (true) {
      delay(1000);
    }
  }

  Bridge.provide("qf_stage1_echo", qf_stage1_echo);
  Bridge.provide("qf_stage1_micros", qf_stage1_micros);
  Bridge.provide_safe("qf_stage1_matrix_draw", qf_stage1_matrix_draw);
}

void loop() {
  delay(1);
}


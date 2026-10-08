#include <Arduino_LED_Matrix.h>
#include <Arduino_RouterBridge.h>

Arduino_LED_Matrix qf_matrix;

constexpr size_t QF_MATRIX_ROWS = 8;
constexpr size_t QF_MATRIX_COLUMNS = 13;
constexpr size_t QF_MATRIX_PIXELS = QF_MATRIX_ROWS * QF_MATRIX_COLUMNS;

uint8_t qf_frame[QF_MATRIX_PIXELS] = {};

enum class QfReverseState : uint8_t {
  idle = 0,
  pending = 1,
  running = 2,
  ready = 3,
  error = 4,
};

QfReverseState qf_reverse_state = QfReverseState::idle;
uint32_t qf_reverse_token = 0;
uint32_t qf_reverse_duration_us = 0;

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

bool qf_stage1_reverse_start(uint32_t token) {
  if (qf_reverse_state != QfReverseState::idle) {
    return false;
  }

  qf_reverse_token = token;
  qf_reverse_duration_us = 0;
  qf_reverse_state = QfReverseState::pending;
  return true;
}

int32_t qf_stage1_reverse_result(uint32_t token) {
  if (token != qf_reverse_token) {
    return -3;
  }
  if (qf_reverse_state == QfReverseState::pending ||
      qf_reverse_state == QfReverseState::running) {
    return -1;
  }
  if (qf_reverse_state == QfReverseState::error) {
    qf_reverse_state = QfReverseState::idle;
    return -2;
  }
  if (qf_reverse_state != QfReverseState::ready) {
    return -4;
  }

  const uint32_t duration_us = qf_reverse_duration_us;
  qf_reverse_state = QfReverseState::idle;
  return static_cast<int32_t>(duration_us);
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
  Bridge.provide_safe("qf_stage1_reverse_start", qf_stage1_reverse_start);
  Bridge.provide_safe("qf_stage1_reverse_result", qf_stage1_reverse_result);
}

void loop() {
  if (qf_reverse_state == QfReverseState::pending) {
    qf_reverse_state = QfReverseState::running;
    uint32_t echoed_token = 0;
    const uint32_t started = micros();
    const bool succeeded =
        Bridge.call("qf_stage1_linux_echo", qf_reverse_token).result(echoed_token);
    qf_reverse_duration_us = micros() - started;
    qf_reverse_state = succeeded && echoed_token == qf_reverse_token
                           ? QfReverseState::ready
                           : QfReverseState::error;
  }

  delay(1);
}

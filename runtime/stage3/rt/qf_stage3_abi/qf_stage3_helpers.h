#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

#include "generated/qfabric_abi.hpp"

namespace abi = qfabric::abi;

extern std::array<std::uint8_t, 128> qf_stage3_buffer;

template <typename Value, typename Encoder>
bool qf_encode_frame(const abi::Metadata& metadata, const Value& value, Encoder encoder,
                     std::size_t& size) {
  std::size_t payload_size = 0;
  const auto payload_status =
      encoder(value, qf_stage3_buffer.data() + abi::kHeaderSize,
              qf_stage3_buffer.size() - abi::kHeaderSize, payload_size);
  if (payload_status != abi::Status::Ok) return false;
  std::size_t header_size = 0;
  const auto header_status = abi::encode_header(
      metadata, static_cast<std::uint16_t>(payload_size), qf_stage3_buffer.data(),
      abi::kHeaderSize, header_size);
  size = header_size + payload_size;
  return header_status == abi::Status::Ok && header_size == abi::kHeaderSize;
}

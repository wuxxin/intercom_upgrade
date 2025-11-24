#pragma once
#include <vector>
#include <cstdint>
#include <string>
#include <map>

// Dummy sound for testing/validation when sox is not available
static const std::vector<uint8_t> ding_dong_raw = {
  0x00, 0x00, 0x00, 0x00
};

static const std::vector<uint8_t>* get_sound(const std::string& name) {
    if (name == "ding_dong") return &ding_dong_raw;
    return nullptr;
}

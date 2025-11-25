#!/bin/bash

empty_sounds='
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
'
sounds_header="
#pragma once
#include <vector>
#include <cstdint>
#include <string>
#include <map>
"

echo "$sounds_header" >sounds.h

# Store names for map generation
names=()

if [ $# -eq 0 ]; then
    echo "Warning: no files specified, will create empty sound.h"
    echo "Usage: $0 soundfiles"
    echo "will create sounds.h from converted soundfiles"
    echo "$empty_sounds" >sounds.h
fi

for file in "$@"; do
    # Clean filename without extension (ding dong.mp3 -> ding_dong)
    name=$(basename "$file" | sed 's/\.[^.]*$//;s/[^a-zA-Z0-9]/_/g')
    echo "Processing $file -> ${name}_raw"
    names+=("$name")
    # Convert to RAW (16kHz, 16bit, Mono)
    sox "$file" --type raw --rate 16000 --channels 1 --encoding signed-integer --bits 16 temp.raw
    # Write C++ Vector Header
    echo "static const std::vector<uint8_t> ${name}_raw = {" >>sounds.h
    # Insert Hex Data, strip output of xxd:
    # sed '1d' removes first line.
    # sed '$d' removes last line (length).
    # sed '$d' removes line before last is "};".
    xxd -i temp.raw | sed '1d;$d' | sed '$d' >>sounds.h
    echo "};" >>sounds.h
    rm temp.raw
done

# Generate lookup function
echo "
static const std::vector<uint8_t>* get_sound(const std::string& name) {
" >>sounds.h

for name in "${names[@]}"; do
    echo "    if (name == \"$name\") return &${name}_raw;" >>sounds.h
done

echo "    return nullptr;
}" >>sounds.h

echo "Done. Created sounds.h"

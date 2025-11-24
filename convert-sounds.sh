#!/bin/bash

echo "#pragma once
#include <vector>
#include <cstdint>
#include <string>
#include <map>
" > sounds.h

# Store names for map generation
names=()

for file in "$@"; do
    # Dateiname ohne Endung bereinigen (ding dong.mp3 -> ding_dong)
    name=$(basename "$file" | sed 's/\.[^.]*$//;s/[^a-zA-Z0-9]/_/g')
    echo "Processing $file -> ${name}_raw"
    names+=("$name")

    # 1. Konvertieren zu RAW (16kHz, 16bit, Mono)
    sox "$file" --type raw --rate 16000 --channels 1 --encoding signed-integer --bits 16 temp.raw

    # 2. C++ Vektor Header schreiben
    echo "static const std::vector<uint8_t> ${name}_raw = {" >> sounds.h

    # 3. Hex-Daten einfügen
    # xxd -i creates:
    # unsigned char name[] = {
    #   0x00, ...
    # };
    # unsigned int name_len = ...;
    # We want just the hex values.
    # sed '1d' removes first line.
    # sed '$d' removes last line (length).
    # The line before last is "};". We need to remove that too.
    xxd -i temp.raw | sed '1d;$d' | sed '$d' >> sounds.h

    # 4. Abschluss
    echo "};" >> sounds.h
    rm temp.raw
done

# Generate lookup function
echo "
static const std::vector<uint8_t>* get_sound(const std::string& name) {
" >> sounds.h

for name in "${names[@]}"; do
    echo "    if (name == \"$name\") return &${name}_raw;" >> sounds.h
done

echo "    return nullptr;
}" >> sounds.h

echo "Done. Created sounds.h"

# -*- coding: utf-8 -*-
"""ESPHome Wiring Diagram Generator

This script parses an ESPHome YAML configuration file,
extracts explicit and implicit hardware wiring information,
and generates an SVG wiring diagram and output its as SVG, html, and a two page pdf
including the detailed wiring table on the second page.

"""

import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import svgwrite
import yaml
from weasyprint import HTML

# Color map for wires.
COLOR_MAP = {
    "red": "#FF4136",  # Red
    "black": "#444444",  # Dark Gray
    "green": "#2ECC40",  # Green
    "green_white": "url(#pattern-green-stripe)",  # Pattern
    "blue": "#0074D9",  # Blue
    "blue_white": "url(#pattern-blue-stripe)",  # Pattern
    "orange": "#FF851B",  # Orange
    "orange_white": "url(#pattern-orange-stripe)",  # Pattern
    "grey": "#888888",  # Medium gray
    "brown": "#A0522D",  # Sienna
    "pink": "#FF69B4",  # Hot Pink
    "yellow": "#FFDC00",  # Yellow
    "default": "#AAAAAA",  # Light Gray
    "i2c_sda": "#FF00FF",  # Magenta
    "i2c_scl": "#FFD700",  # Gold
    "gpio_in": "#39CCCC",  # Teal
    "gpio_out": "#F012BE",  # Pink
}

# Layout and styling
PIN_V_SPACING = 20
COMPONENT_WIDTH = 180
COMPONENT_PADDING_X = 150
COMPONENT_PADDING_Y = 40
BUS_V_SPACING = 50
CANVAS_PADDING = 60
PIN_DOT_RADIUS = 3
PIN_LABEL_OFFSET = 7
WIRE_THICKNESS = 3

LEGEND_WIDTH = 350
LEGEND_PADDING = 10
LEGEND_TITLE_HEIGHT = 15
LEGEND_ROW_HEIGHT = 15

WIRING_LEGEND_WIDTH = 400

CSS_STYLE = """
            .component {
                fill: #f9f9f9;
                stroke: #333;
                stroke-width: 1px;
                rx: 5px;
            }
            .component-bus {
                stroke-width: 4px;
            }
            .comp-title {
                font-family: Arial, sans-serif;
                font-size: 14px;
                font-weight: bold;
            }
            .comp-description {
                font-family: Arial, sans-serif;
                font-size: 10px;
                font-style: italic;
                fill: #555;
            }
            .pin-label {
                font-family: Arial, sans-serif;
                font-size: 11px;
                dominant-baseline: middle;
                fill: black; /* Ensure pin labels are visible over wires */

            }
            .pin-dot {
                fill: #666;
                stroke: #333;
                stroke-width: 1px;
            }
            .wire {
                fill: none;
                stroke-opacity: 0.8;
                stroke-linecap: round;
            }
            .legend-box {
                fill: #F7F7F7;
                stroke: #333;
                stroke-width: 1px;
                rx: 5px;
            }
            .legend-title {
                font-family: Arial, sans-serif;
                font-size: 14px;
                font-weight: bold;
                text-anchor: middle;
            }
            .legend-comp-title {
                 font-family: Arial, sans-serif;
                font-size: 12px;
                font-weight: bold;
            }
             .legend-pin-text {
                font-family: Arial, sans-serif;
                font-size: 12px;
            }
             .legend-wiring-text {
                font-family: Arial, sans-serif;
                font-size: 10px;
            }
        """

"""## Test YAML content
This is a simplified content used if intercom.yaml is not found.

"""

DUMMY_INTERCOM_YAML = """
# ESPHome Configuration - Simplified Dummy Content

substitutions:
  esp32_board: adafruit_feather_esp32_v2
  esphome_name: "minimal_test"
  project_version: "1.0.0"
  esphome_friendly_name: "Minimal Test"
  domain: ".local"
  wifi_ssid: ""
  wifi_password: ""
  ota_password: ""

  hardware:
    partlist:
      - name: esp32
        type: adafruit_feather_esp32_v2
      - name: rail_3V3
        type: bus
      - name: rail_GND
        type: bus
      - name: bme280_i2c_0x76
        type: bme280
    wiring:
      esp32.3V3:
        connect: rail_3V3.BUS
        color: red
      esp32.GND:
        connect: rail_GND.BUS
        color: black

      bme280_i2c_0x76.VIN:
        connect: rail_3V3.BUS
        color: red
      bme280_i2c_0x76.GND:
        connect: rail_GND.BUS
        color: black

    modules:
      bus:
        description: Connection Bus
        pins:
          - name: BUS

      bme280:
        description: BME280 Temperature / Humidity / Pressure Sensor
        pins:
          - name: VIN
          - name: GND
          - name: SCL
          - name: SDA

      adafruit_feather_esp32_v2:
        description: Adafruit ESP32 Feather V2
        pins:
          - name: RST
          - name: 3V3
          - name: NC_L3
          - name: GND
          - name: GPIO26
          - name: GPIO25
          - name: GPIO34
          - name: GPIO39
          - name: GPIO36
          - name: GPIO4
          - name: GPIO5
          - name: GPIO19
          - name: GPIO21
          - name: GPIO7
          - name: GPIO8
          - name: GPIO37
          - name: NC_R1
            side: right
          - name: NC_R2
            side: right
          - name: NC_R3
            side: right
          - name: NC_R4
            side: right
          - name: VBAT
            side: right
          - name: EN
            side: right
          - name: USB
            side: right
          - name: GPIO13
            side: right
          - name: GPIO12
            side: right
          - name: GPIO27
            side: right
          - name: GPIO33
            side: right
          - name: GPIO15
            side: right
          - name: GPIO32
            side: right
          - name: GPIO14
            side: right
          - name: GPIO20
            side: right
          - name: GPIO22
            side: right

esp32:
  board: ${esp32_board}
  framework:
    type: esp-idf

wifi:
  ssid: ${wifi_ssid}
  password: ${wifi_password}
  domain: ${domain}

ota:
  - platform: esphome
    password: ${ota_password}

i2c:
  sda: GPIO22 # Pin SDA/22 Feather V2
  scl: GPIO20 # Pin SCL/20 Feather V2
  scan: true
  id: i2c_bus

sensor:
  - platform: bme280_i2c
    temperature:
      name: "Air Temperature"
    pressure:
      name: "Air Pressure"
    humidity:
      name: "Air Moisture"
    address: 0x76
    update_interval: 60s
"""

"""## CORE CLASSES

"""


class Pin:
    """Represents a single pin on a component."""

    def __init__(
        self,
        name: str,
        component: "Component",
        side: str = "left",
        pos: int = 1,
        description: str = "",
    ):
        self.name = name
        self.component = component
        self.side = side
        self.pos = pos
        self.description = description
        self.coords: Tuple[int, int] = (0, 0)
        self.is_bus_pin = False

    def __repr__(self):
        return f"Pin({self.component.instance_name}.{self.name})"


class Component:
    """Represents an instance of a hardware module."""

    def __init__(self, instance_name: str, module_type: str, description: str = ""):
        self.instance_name = instance_name
        self.module_type = module_type
        self.description = description
        self.pins: Dict[str, Pin] = {}
        self.x: int = 0
        self.y: int = 0
        self.width: int = COMPONENT_WIDTH
        self.height: int = 0
        self.is_bus = module_type == "bus"

    def add_pin(self, name: str, side: str, pos: int, description: str):
        pin = Pin(name, self, side, pos, description)
        self.pins[name] = pin
        if self.is_bus:
            pin.is_bus_pin = True

    def calculate_dimensions(self):
        """Calculates the height of the component based on its pins."""
        if self.is_bus:
            self.height = 5
            self.width = 1000  # Will be set by layout
        else:
            left_pins = sum(1 for p in self.pins.values() if p.side == "left")
            right_pins = sum(1 for p in self.pins.values() if p.side == "right")
            # Adjust height for description text
            description_lines = len(self.description.splitlines())
            self.height = (
                max(left_pins, right_pins) + 1 + description_lines * 0.5
            ) * PIN_V_SPACING

    def set_position(self, x: int, y: int):
        """Sets the component's top-left position and calculates all pin coordinates."""
        self.x = x
        self.y = y

        if self.is_bus:
            self.pins["BUS"].coords = (self.x, self.y)
            return

        # Assign coordinates to each pin
        left_pos = 1
        right_pos = 1
        # Offset pin positions to make space for description
        pin_y_offset = len(self.description.splitlines()) * PIN_V_SPACING * 0.5
        for pin in sorted(self.pins.values(), key=lambda p: p.pos):
            pin_y = (
                self.y + pin_y_offset + (left_pos * PIN_V_SPACING)
                if pin.side == "left"
                else self.y + pin_y_offset + (right_pos * PIN_V_SPACING)
            )
            pin_x = self.x if pin.side == "left" else self.x + self.width
            pin.coords = (pin_x, pin_y)

            if pin.side == "left":
                left_pos += 1
            else:
                right_pos += 1

    def __repr__(self):
        return f"Component({self.instance_name} [{self.module_type}])"


class Wire:
    """Represents a single connection between two pins."""

    def __init__(
        self, start_pin: Pin, end_pin: Pin, color: str = "default", description: str = ""
    ):
        self.start_pin = start_pin
        self.end_pin = end_pin
        self.color = color
        self.description = description

    def __repr__(self):
        return f"Wire({self.start_pin} -> {self.end_pin}, color={self.color})"


class WiringDiagram:
    """Orchestrator for parsing, layout, and drawing the SVG."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.hardware = config.get("substitutions", {}).get("hardware", {})
        self.modules: Dict[str, Dict] = {}
        self.components: Dict[str, Component] = {}
        self.wires: List[Wire] = []
        self.legend_data: Dict[str, List[Tuple[str, str]]] = {}
        self.wiring_legend_data: List[
            Tuple[str, str, str]
        ] = []  # To store wiring legend data
        self.filtered_legend_data: Dict[
            str, List[Tuple[str, str]]
        ] = {}  # To store legend data for drawing

        self.dwg: Optional[svgwrite.Drawing] = None
        self.main_diagram_width: int = 0
        self.main_diagram_height: int = 0

        self.legend_x: int = 0
        self.legend_y: int = 0
        self.legend_width: int = LEGEND_WIDTH
        self.legend_height: int = 0

    def _get_color(self, color_name: Optional[str]) -> str:
        """Gets a hex color or pattern URL from a name, with fallback."""
        if color_name is None:
            return COLOR_MAP["default"]
        return COLOR_MAP.get(color_name, COLOR_MAP["default"])

    def _find_pin(self, full_pin_name: str) -> Optional[Pin]:
        """Finds a Pin object from a 'component.pin' string."""
        if "." not in full_pin_name:
            print(
                f"Warning: Invalid pin name format '{full_pin_name}'. Skipping.",
                file=sys.stderr,
            )
            return None

        comp_name, pin_name = full_pin_name.split(".", 1)

        component = self.components.get(comp_name)
        if not component:
            print(
                f"Warning: Component '{comp_name}' not found in partlist. Skipping wire.",
                file=sys.stderr,
            )
            return None

        pin = component.pins.get(pin_name)
        if not pin:
            print(
                f"Warning: Pin '{pin_name}' not found on component '{comp_name}'. Skipping wire.",
                file=sys.stderr,
            )
            return None

        return pin

    def _add_wire(
        self,
        start_pin_name: str,
        end_pin_name: str,
        color: str = "default",
        desc: str = "",
    ):
        """Helper to create and add a wire."""
        start_pin = self._find_pin(start_pin_name)
        end_pin = self._find_pin(end_pin_name)

        if start_pin and end_pin:
            # Ensure buses are always the end_pin
            if start_pin.is_bus_pin and not end_pin.is_bus_pin:
                start_pin, end_pin = end_pin, start_pin

            self.wires.append(Wire(start_pin, end_pin, color, desc))
            # Add wiring data for the legend (even if not drawn in SVG)
            self.wiring_legend_data.append((start_pin_name, color, end_pin_name))

    def parse_modules(self):
        """Parses the 'hardware.modules' section."""
        self.modules = self.hardware.get("modules", {})
        if not self.modules:
            raise ValueError("Error: 'substitutions.hardware.modules' not found in YAML.")

    def parse_partlist(self):
        """Parses 'hardware.partlist' to create Component instances."""
        partlist = self.hardware.get("partlist", [])
        if not partlist:
            raise ValueError(
                "Error: 'substitutions.hardware.partlist' not found in YAML."
            )

        for part in partlist:
            instance_name = part.get("name")
            module_type = part.get("type")

            if not instance_name or not module_type:
                print(
                    f"Warning: Skipping invalid partlist entry: {part}", file=sys.stderr
                )
                continue

            module_def = self.modules.get(module_type)
            if not module_def:
                print(
                    f"Warning: Module type '{module_type}' for '{instance_name}' not found in modules. Skipping.",
                    file=sys.stderr,
                )
                continue

            comp = Component(
                instance_name, module_type, module_def.get("description", "")
            )

            pos_left, pos_right = 1, 1
            for i, pin_def in enumerate(module_def.get("pins", [])):
                pin_name = pin_def.get("name")
                pin_side = pin_def.get("side", "left")
                pin_desc = pin_def.get("description", "")

                if pin_side == "left":
                    pos = pos_left
                    pos_left += 1
                else:
                    pos = pos_right
                    pos_right += 1

                comp.add_pin(pin_name, pin_side, pos, pin_desc)

                # Collect pin descriptions for the legend (even if not drawn in SVG)
                if pin_desc:
                    if instance_name not in self.legend_data:
                        self.legend_data[instance_name] = []
                    self.legend_data[instance_name].append((pin_name, pin_desc))

            comp.calculate_dimensions()
            self.components[instance_name] = comp

    def parse_explicit_wiring(self):
        """Parses 'hardware.wiring' section."""
        wiring = self.hardware.get("wiring", {})
        for start_pin_name, details in wiring.items():
            if "connect" in details:
                end_pin_name = details["connect"]
                color = details.get("color", "default")
                desc = details.get("description", "")
                self._add_wire(start_pin_name, end_pin_name, color, desc)

    def parse_implicit_wiring(self):
        """Parses ESPHome sections (i2c, switch, etc.) for GPIO connections."""

        # Find the main ESP32 component
        esp32_comp_name = None
        for name, comp in self.components.items():
            if "esp32" in comp.module_type:
                esp32_comp_name = name
                break

        if not esp32_comp_name:
            print(
                "Warning: No ESP32 component found in partlist. Cannot parse implicit wiring.",
                file=sys.stderr,
            )
            return

        # 1. I2C
        i2c_conns = self.config.get("i2c", {})
        if isinstance(i2c_conns, dict):  # Single I2C bus
            i2c_conns = [i2c_conns]

        for i2c in i2c_conns:
            sda_pin = i2c.get("sda")
            scl_pin = i2c.get("scl")

            # Find all sensors on this bus
            sensors = self.config.get("sensor", [])
            for sensor in sensors:
                platform = sensor.get("platform", "")
                if "i2c" in platform:
                    # Find the component matching this sensor
                    # This assumes bme280 platform sensor has an id matching a partlist name.
                    # A better way is to match by address '0x76'
                    sensor_comp_name = None
                    if sensor.get("address") == 0x76:  # From YAML
                        sensor_comp_name = "bme280_i2c_0x76"  # From partlist

                    if sensor_comp_name:
                        if sda_pin:
                            self._add_wire(
                                f"{esp32_comp_name}.{sda_pin}",
                                f"{sensor_comp_name}.SDA",
                                "i2c_sda",
                                "I2C SDA",
                            )
                        if scl_pin:
                            self._add_wire(
                                f"{esp32_comp_name}.{scl_pin}",
                                f"{sensor_comp_name}.SCL",
                                "i2c_scl",
                                "I2C SCL",
                            )

        # 2. Switches
        switches = self.config.get("switch", [])
        for switch in switches:
            if switch.get("platform") == "gpio":
                pin = switch.get("pin")
                comp_id = switch.get("id")
                if pin and comp_id and comp_id in self.components:
                    # 'IN' is the standard name for a relay input pin
                    self._add_wire(
                        f"{esp32_comp_name}.{pin}",
                        f"{comp_id}.IN",
                        "gpio_out",
                        f"Switch '{comp_id}' Control",
                    )

        # 3. Binary Sensors
        binary_sensors = self.config.get("binary_sensor", [])
        for sensor in binary_sensors:
            if sensor.get("platform") == "gpio":
                pin_def = sensor.get("pin", {})
                pin = pin_def.get("number") if isinstance(pin_def, dict) else pin_def
                comp_id = sensor.get("id")
                if pin and comp_id and comp_id in self.components:
                    # 'OUT' is the standard name for an optocoupler output
                    self._add_wire(
                        f"{esp32_comp_name}.{pin}",
                        f"{comp_id}.OUT",
                        "gpio_in",
                        f"Sensor '{comp_id}' Input",
                    )

    def layout_components(self):
        """Arranges components on the canvas."""

        # Hardcoded layout based on analysis of intercom.yaml
        # This provides a much cleaner diagram than a fully auto-layout.
        layout_grid = [
            ["esp32", "max98357a"],
            [
                "switch_door_opener",
                "bell_ringing",
                "switch_silence_buzzer",
                "bme280_i2c_0x76",
                "speaker",
            ],
            ["Intercom"],
            ["Intercom_Cable"],
        ]

        # Place power buses
        bus_y = BUS_V_SPACING
        self.components["rail_3V3"].set_position(CANVAS_PADDING, bus_y)
        bus_y += 20  # Small gap
        self.components["rail_GND"].set_position(CANVAS_PADDING, bus_y)

        current_y = bus_y + BUS_V_SPACING
        current_x = CANVAS_PADDING

        max_col_y = 0

        for col in layout_grid:
            col_y = current_y
            max_w = 0
            for comp_name in col:
                if comp_name in self.components:
                    comp = self.components[comp_name]
                    comp.set_position(current_x, col_y)
                    col_y += comp.height + COMPONENT_PADDING_Y
                    max_w = max(max_w, comp.width)

            current_x += max_w + COMPONENT_PADDING_X
            max_col_y = max(max_col_y, col_y)

        # Calculate the required width and height for the main diagram based on component positions
        max_comp_x = 0
        max_comp_y = 0
        for comp in self.components.values():
            max_comp_x = max(max_comp_x, comp.x + comp.width)
            max_comp_y = max(max_comp_y, comp.y + comp.height)

        self.main_diagram_width = max_comp_x + CANVAS_PADDING  # Add right padding
        self.main_diagram_height = max_comp_y + CANVAS_PADDING  # Add bottom padding

        # Set bus widths (based on main diagram width)
        for comp in self.components.values():
            if comp.is_bus:
                comp.width = self.main_diagram_width - (
                    CANVAS_PADDING * 2
                )  # Adjust for both left and right padding

        # --- Layout the filtered pin legend ---
        # Filter legend data for only "Intercom" and "Intercom_Cable"
        self.filtered_legend_data = {
            name: data
            for name, data in self.legend_data.items()
            if name in ["Intercom", "Intercom_Cable"]
        }

        # Calculate filtered legend height
        filtered_legend_height = LEGEND_TITLE_HEIGHT + LEGEND_PADDING * 2
        for comp_name, pin_list in self.filtered_legend_data.items():
            filtered_legend_height += (
                len(pin_list) * LEGEND_ROW_HEIGHT
            ) + LEGEND_ROW_HEIGHT  # Add space for component title in legend

        self.legend_height = filtered_legend_height  # Update instance variable

        # Position legend - below Intercom and Intercom_Cable, horizontally centered
        intercom_comp = self.components.get("Intercom")
        intercom_cable_comp = self.components.get("Intercom_Cable")

        if intercom_comp and intercom_cable_comp:
            # Use the maximum bottom position of the two components
            align_bottom_y = max(
                intercom_comp.y + intercom_comp.height,
                intercom_cable_comp.y + intercom_cable_comp.height,
            )
            self.legend_y = align_bottom_y + COMPONENT_PADDING_Y

            # Center legend horizontally between the left of Intercom and the right of Intercom_Cable
            min_x = min(intercom_comp.x, intercom_cable_comp.x)
            max_x_width = max(
                intercom_comp.x + intercom_comp.width,
                intercom_cable_comp.x + intercom_cable_comp.width,
            )
            center_x = (min_x + max_x_width) / 2
            self.legend_x = int(center_x - self.legend_width / 2)
        else:
            # Fallback position if components are not found
            self.legend_x = CANVAS_PADDING
            self.legend_y = self.main_diagram_height + COMPONENT_PADDING_Y

        # Adjust main diagram height to include the legend
        self.main_diagram_height = max(
            self.main_diagram_height, self.legend_y + self.legend_height + CANVAS_PADDING
        )

    def _draw_definitions(self):
        """Adds SVG definitions like markers and styles."""
        # CSS Styles
        style = CSS_STYLE
        self.dwg.add(self.dwg.style(style))

        # Patterns for striped wires
        def add_stripe_pattern(id, color):
            pattern = self.dwg.pattern(
                id=id, patternUnits="userSpaceOnUse", width=8, height=8
            )
            pattern.add(self.dwg.rect(insert=(0, 0), size=(8, 8), fill="white"))
            pattern.add(
                self.dwg.line(start=(0, 0), end=(8, 8), stroke=color, stroke_width=2)
            )
            pattern.add(
                self.dwg.line(start=(8, 0), end=(0, 8), stroke=color, stroke_width=2)
            )
            self.dwg.defs.add(pattern)

        add_stripe_pattern("pattern-green-stripe", COLOR_MAP.get("green", "#2ECC40"))
        add_stripe_pattern("pattern-blue-stripe", COLOR_MAP.get("blue", "#0074D9"))
        add_stripe_pattern("pattern-orange-stripe", COLOR_MAP.get("orange", "#FF851B"))

    def draw_components(self):
        """Draws all components and pins."""
        g = self.dwg.g(id="components")

        for comp in self.components.values():
            if comp.is_bus:
                color = (
                    self._get_color("red")
                    if "3V3" in comp.instance_name
                    else self._get_color("black")
                )
                g.add(
                    self.dwg.line(
                        start=(comp.x, comp.y),
                        end=(comp.x + comp.width, comp.y),
                        stroke=color,
                        stroke_width=WIRE_THICKNESS,
                        class_="component-bus",
                    )
                )
                g.add(
                    self.dwg.text(
                        comp.instance_name,
                        insert=(comp.x - PIN_LABEL_OFFSET, comp.y),
                        text_anchor="end",
                        class_="pin-label",
                    )
                )
            else:
                # Component Box
                g.add(
                    self.dwg.rect(
                        insert=(comp.x, comp.y),
                        size=(comp.width, comp.height),
                        class_="component",
                    )
                )
                # Component Title
                # Add top padding to the title
                title_y = comp.y + PIN_V_SPACING * 1.2  # Increased vertical spacing
                g.add(
                    self.dwg.text(
                        comp.instance_name,
                        insert=(comp.x + comp.width / 2, title_y),
                        text_anchor="middle",
                        class_="comp-title",
                    )
                )
                # Component Description (Multiline)
                if comp.description:
                    desc_lines = comp.description.splitlines()
                    # Basic word wrapping (can be improved for more complex cases)
                    wrapped_lines = []
                    for line in desc_lines:
                        words = line.split()
                        current_line = ""
                        for word in words:
                            # Adjusted wrapping limit based on empirical testing (increased padding from 5 to 8)
                            if len(current_line) + len(word) + 1 <= (comp.width // 8):
                                current_line += word + " "
                            else:
                                wrapped_lines.append(current_line.strip())
                                current_line = word + " "
                        if current_line.strip():
                            wrapped_lines.append(current_line.strip())

                    # Calculate starting vertical position for descriptions (2 lines of space below title)
                    desc_start_y = (
                        title_y + PIN_V_SPACING * 0.7
                    )  # Added padding from the title

                    for i, line in enumerate(wrapped_lines):
                        g.add(
                            self.dwg.text(
                                line,
                                insert=(
                                    comp.x + comp.width / 2,
                                    desc_start_y + i * PIN_V_SPACING * 0.6,
                                ),  # Increased vertical spacing multiplier
                                text_anchor="middle",
                                class_="comp-description",
                            )
                        )

                # Pins
                for pin in comp.pins.values():
                    g.add(
                        self.dwg.circle(
                            center=pin.coords, r=PIN_DOT_RADIUS, class_="pin-dot"
                        )
                    )

                    is_left = pin.side == "left"
                    anchor = "end" if is_left else "start"
                    offset = -PIN_LABEL_OFFSET if is_left else PIN_LABEL_OFFSET

                    g.add(
                        self.dwg.text(
                            pin.name,
                            insert=(pin.coords[0] + offset, pin.coords[1]),
                            text_anchor=anchor,
                            class_="pin-label",
                        )
                    )

        self.dwg.add(g)

    def draw_wires(self):
        """Draws all wires as smooth curves."""
        g = self.dwg.g(id="wires")

        for wire in self.wires:
            p1 = wire.start_pin.coords
            p2 = wire.end_pin.coords
            s_side = wire.start_pin.side
            e_side = wire.end_pin.side
            color = self._get_color(wire.color)

            # Handle bus connections
            if wire.end_pin.is_bus_pin:
                bus_y = wire.end_pin.coords[1]
                path_d = f"M {p1[0]} {p1[1]} V {bus_y}"
                g.add(
                    self.dwg.path(
                        d=path_d, stroke=color, stroke_width=WIRE_THICKNESS, class_="wire"
                    )
                )
                # Add tap-off dot
                g.add(
                    self.dwg.circle(
                        center=(p1[0], bus_y), r=PIN_DOT_RADIUS + 1, fill=color
                    )
                )
                continue

            # Logic for smooth Bezier curves
            x1, y1 = p1
            x2, y2 = p2

            # Find a midpoint for the curve
            mid_x = 0
            if s_side == "left" and e_side == "left":
                mid_x = min(x1, x2) - COMPONENT_PADDING_X / 2
            elif s_side == "right" and e_side == "right":
                mid_x = max(x1, x2) + COMPONENT_PADDING_X / 2
            else:  # Connecting left-to-right or right-to-left
                mid_x = (x1 + x2) / 2

            # Cubic Bezier path: M(start) C(control1), (control2), (end)
            # This creates a smooth "S" or "C" shape
            path_d = f"M {x1} {y1} C {mid_x} {y1}, {mid_x} {y2}, {x2} {y2}"

            g.add(
                self.dwg.path(
                    d=path_d, stroke=color, stroke_width=WIRE_THICKNESS, class_="wire"
                )
            )

        self.dwg.add(g)

    def draw_legend(self):
        """Draws the filtered pin legend box with pin descriptions."""
        g = self.dwg.g(id="pin-legend")

        # Legend Box
        g.add(
            self.dwg.rect(
                insert=(self.legend_x, self.legend_y),
                size=(self.legend_width, self.legend_height),
                class_="legend-box",
            )
        )

        current_y = self.legend_y + LEGEND_PADDING

        # Use filtered_legend_data
        for comp_name, pin_list in self.filtered_legend_data.items():
            # Component Title in Legend
            current_y += LEGEND_ROW_HEIGHT
            g.add(
                self.dwg.text(
                    comp_name,
                    insert=(self.legend_x + LEGEND_PADDING, current_y),
                    class_="legend-comp-title",
                )
            )

            # Pin descriptions in legend
            for pin_name, pin_desc in pin_list:
                current_y += LEGEND_ROW_HEIGHT
                g.add(
                    self.dwg.text(
                        f"{pin_name}: {pin_desc}",
                        insert=(self.legend_x + LEGEND_PADDING, current_y),
                        class_="legend-pin-text",
                    )
                )

        self.dwg.add(g)

    def generate_main_svg(self) -> str:
        """Parses data, lays out components, and generates the main SVG string."""
        print("Parsing modules...")
        self.parse_modules()
        print("Parsing partlist...")
        self.parse_partlist()
        print("Parsing explicit wiring...")
        self.parse_explicit_wiring()
        print("Parsing implicit wiring...")
        self.parse_implicit_wiring()
        print("Laying out components and legend...")
        self.layout_components()  # This now also calculates legend position and size

        print("Generating main diagram SVG...")
        self.dwg = svgwrite.Drawing(
            "wiring_diagram.svg",  # Name the main SVG file
            size=("100%", "100%"),  # For notebook zooming
        )
        # Add white background
        self.dwg.add(self.dwg.rect(insert=(0, 0), size=("100%", "100%"), fill="white"))

        # Set the viewBox based on calculated dimensions and padding
        self.dwg.viewbox(
            minx=0, miny=0, width=self.main_diagram_width, height=self.main_diagram_height
        )

        self._draw_definitions()  # Add definitions

        print("Drawing wires...")
        self.draw_wires()
        print("Drawing components...")  # Draw components after wires
        self.draw_components()
        print("Drawing filtered pin legend...")
        self.draw_legend()  # Draw the filtered pin legend
        print("Main SVG generation complete.")
        return self.dwg.tostring()

    def generate_wiring_markdown(self) -> str:
        """Generates the wiring data as a Markdown table string."""
        # Ensure data is parsed before generating markdown
        if not self.wiring_legend_data:
            print("Warning: Wiring data not parsed yet. Parsing data...", file=sys.stderr)
            self.parse_explicit_wiring()  # Re-parse if needed
            self.parse_implicit_wiring()  # Re-parse if needed

        markdown_table_string = "| From | Color | To |\n"
        markdown_table_string += "|---|---|---|\n"
        for from_pin, color, to_pin in self.wiring_legend_data:
            markdown_table_string += f"| {from_pin} | {color} | {to_pin} |\n"

        return markdown_table_string

    def markdown_to_html_table(self, markdown_string: str) -> str:
        """Converts a Markdown table string to an HTML table string."""
        # Basic conversion for the expected table format
        lines = markdown_string.strip().split("\n")
        if len(lines) < 2 or not lines[1].startswith("|---"):
            print(
                "Warning: Input does not appear to be a Markdown table. Returning as is.",
                file=sys.stderr,
            )
            return markdown_string

        html_lines = []
        html_lines.append("<table>")

        # Header row
        header_cells = [cell.strip() for cell in lines[0].strip("|").split("|")]
        html_lines.append("  <thead>")
        html_lines.append("    <tr>")
        for cell in header_cells:
            html_lines.append(f"      <th>{cell}</th>")
        html_lines.append("    </tr>")
        html_lines.append("  </thead>")

        # Body rows
        html_lines.append("  <tbody>")
        for line in lines[2:]:  # Skip the header and separator lines
            body_cells = [cell.strip() for cell in line.strip("|").split("|")]
            html_lines.append("    <tr>")
            for cell in body_cells:
                html_lines.append(f"      <td>{cell}</td>")
            html_lines.append("    </tr>")
        html_lines.append("  </tbody>")

        html_lines.append("</table>")

        return "\n".join(html_lines)


"""## Load Config


"""

# Load and parse the YAML configuration

config_file_path = "intercom.yaml"
try:
    with open(config_file_path, "r") as f:
        config = yaml.safe_load(f)
    print(f"Configuration loaded from {config_file_path}")
except FileNotFoundError:
    print(f"Error: Configuration file not found at {config_file_path}", file=sys.stderr)
    config = None
except yaml.YAMLError as e:
    print(f"Error parsing YAML file {config_file_path}: {e}", file=sys.stderr)
    config = None

if config is None:
    config = yaml.safe_load(DUMMY_INTERCOM_YAML)
    print("Configuration loaded from DUMMY_INTERCOM_YAML.")

# Check if config was loaded successfully
if config is None:
    print("Error: Failed to load configuration.", file=sys.stderr)

"""## Instantiate the WiringDiagram"""

# Assuming `config` is already defined from the YAML loading cell
# Ensure the WiringDiagram class is defined in a previous cell (e.g., cell 725ea93d)
if "WiringDiagram" not in globals():
    print(
        "Error: 'WiringDiagram' class definition not found. Please run the cell containing the class definition first.",
        file=sys.stderr,
    )
else:
    diagram = WiringDiagram(config)

    # Generate and save the main SVG
    print("Generating and saving SVG...")
    main_svg_string = diagram.generate_main_svg()
    main_svg_file = "wiring_diagram.svg"
    with open(main_svg_file, "w") as f:
        f.write(main_svg_string)

    print(f"SVG file for diagram saved to {main_svg_file}")

    # Generate and save the main HTML
    print("Generating and saving HTML...")
    main_html_file = "wiring_diagram.html"
    html_content = f"""<!DOCTYPE html>
    <html>
    <head>
      <title>Wiring Diagram</title>
      <style>
          body {{ margin: 0; padding: 0; }}
          svg {{ display: block; }}
      </style>
    </head>
    <body>
      {main_svg_string}
    </body>
    </html>
    """
    with open(main_html_file, "w") as f:
        f.write(html_content)
    print(f"HTML file for diagram saved to {main_html_file}")

    # Generate the wiring data Markdown table
    print("\nGenerating wiring data Markdown table...")
    wiring_markdown_table = diagram.generate_wiring_markdown()
    print("Wiring data Markdown table generated.")
    # Convert Markdown table to HTML table
    wiring_table_html = diagram.markdown_to_html_table(wiring_markdown_table)
    print("Wiring data Markdown table converted to HTML.")
    # print(wiring_table_html)

    # The markdown table string is now available in the wiring_markdown_table variable
    # It will be used in a later step to create the second page of the PDF.
    # The HTML table string is now available in the wiring_table_html variable.

"""## Create the first html page (svg) for the PDF


"""

# Construct the full HTML content for the first page
first_page_html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Wiring Diagram Page 1</title>
    <style>
        @page {{
            size: A4 landscape;
            margin-top: 1.5cm; /* Added small top margin for balance */
            margin-bottom: 1.5cm; /* Added small bottom margin for balance */
            margin-left: 1.5cm; /* Specified left margin */
            margin-right: 1.5cm; /* Added a right margin for balance */
            /* Removed page numbering */
        }}
        body {{
            margin: 0;
            padding: 0;
        }}
        svg {{
            display: block;
            width: 100%; /* Make SVG fill the width of the page */
            height: auto; /* Maintain aspect ratio */
        }}
    </style>
</head>
<body>
    {main_svg_string}
</body>
</html>
"""

print("HTML content for the first page generated.")
# The variable first_page_html_content now holds the complete HTML for the first page.

"""## Create the second html page (markdown) for the PDF

### Subtask:
Construct the full HTML content for the second page of the PDF, embedding the rendered Markdown HTML snippet and ensuring it's set up for a landscape A4 page with the specified right margin (2.5cm on even pages) and positioned on half the page.

"""

# Construct the full HTML content for the second page
second_page_html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Wiring Diagram Page 2</title>
    <style>
        @page :nth(2) {{
            size: A4 landscape;
            margin-top: 1.0cm;
            margin-bottom: 1.0cm;
            margin-left: 2.5cm; /* Added a left margin for balance */
            margin-right: 2.5cm; /* Specified right margin for even pages */
             /* Removed page numbering */
        }}
         @page :not(:nth(2)) {{
            size: A4 landscape;
            margin-top: 1.0cm;
            margin-bottom: 1.0cm;
            margin-left: 2.5cm; /* Specified left margin for odd pages */
            margin-right: 2.5cm; /* Added a right margin for balance */
             /* Removed page numbering */
        }}
        body {{
            margin: 0;
            padding: 0;
        }}
        .half-page-container {{
            width: 50%; /* Occupy half the page width */
            /* Additional styling for the container if needed, e.g., padding, border */
        }}
        table {{
            border-collapse: collapse;
            width: 100%; /* Make table fill the container width */
            font-size: 10pt; /* Reduce font size to fit more content */
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 5px; /* Reduce padding */
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
        }}
    </style>
</head>
<body>
    <div class="half-page-container">
        {wiring_table_html}
    </div>
</body>
</html>
"""

print("HTML content for the second page generated.")
# The variable second_page_html_content now holds the complete HTML for the second page.

"""## Combine the HTML content for both pages

"""

# Add a page break after the first page content
combined_html_content = f"""{first_page_html_content}
<div style="page-break-after: always;"></div>
{second_page_html_content}
"""

# Define the output PDF file path
output_pdf_file = "wiring_diagram.pdf"

# Use WeasyPrint to generate the PDF
# Pass the combined HTML string to the HTML object
try:
    HTML(string=combined_html_content).write_pdf(output_pdf_file)
    print(f"PDF file generated successfully: {output_pdf_file}")
except Exception as e:
    print(f"Error generating PDF: {e}", file=sys.stderr)
    # Indicate failure if PDF generation fails
    conversion_success = False

# Check if the PDF file was actually created
conversion_success = os.path.exists(output_pdf_file)

if conversion_success:
    # Display the generated PDF if in a suitable environment (like Colab/Jupyter)
    # This part is optional and depends on the environment
    print("PDF conversion status: Success")
else:
    print("PDF conversion status: Failure")

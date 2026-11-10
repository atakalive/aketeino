# aketeino

English | [日本語](README_ja.md)

A **3-channel servo shutter** firmware for the Arduino Nano R4 (RA4M1).
It drives up to three servos independently over serial commands to perform
open/close shutter actions. The project is managed with [PlatformIO](https://platformio.org/).

## Features

- Independent control of **3 servo channels**
- Open / close angles **configurable at runtime over serial**
- Simple single-character serial command protocol (115200 baud)
- Bundled **test GUI** — a single HTML file with no dependencies (Web Serial)

## Requirements

- Arduino Nano R4 (RA4M1 / `nano_r4`)
- Up to 3 servo motors
- PlatformIO (`pio` CLI, or PlatformIO IDE / VS Code extension)
- For the GUI: Chrome or Edge (a browser with Web Serial API support)

## Bill of Materials (BOM)

| # | Part | Qty | Notes |
| - | ---- | --- | ----- |
| 1 | Arduino Nano R4 (RA4M1 / `nano_r4`) | 1 | Main board |
| 2 | Servo motor (3-wire, PWM controlled) | 1–3 | One per shutter channel. Developed with SG90 |
| 3 | Jumper wires / wiring | as needed | For signal, power, and GND |
| 4 | External 5V servo power supply (optional) | 0–1 | Recommended when driving 2 or more servos, especially 3. Also use it when one servo on USB power is short of current. Connect its GND to the board's GND |
| 5 | Electrolytic capacitor (optional) | 0–1 | Connect across the servo power and GND, close to the servos, to suppress idle servo jitter. Around 470–1000µF, rated 10 V or higher |

## Wiring

Connect the servo signal lines to the following pins (all PWM-capable).

| Channel | Signal pin |
| ------- | ---------- |
| CH1     | D3         |
| CH2     | D5         |
| CH3     | D6         |

Connect each servo's three wires as follows.

| Servo wire | Connect to |
| ---------- | ---------- |
| Signal (orange, yellow, white, etc.) | The pin in the table above (D3 / D5 / D6) |
| Power (red) | 1 servo: the board's +5V pin (USB power is fine; see the notes below) / 2 or more servos (especially 3): + of an external 5V supply (recommended) |
| GND (brown, black, etc.) | The board's GND. When using an external supply, also connect the external supply's − to the board's GND |

- Over USB power, at most 500 mA is available, including what the board itself draws. This is the USB 2.0
  limit; some PC ports and hubs supply less.
- A servo draws a large current when it starts moving, under a heavy load, or when it is blocked (stalled).
  Even with one servo, if you see signs of insufficient current (the board resets, or the servo moves
  erratically), use an external 5V supply.
- Choose an external 5V supply that can deliver at least the sum of the stall currents of all connected
  servos (see each datasheet). For a servo whose stall current is unknown, use a generous estimate.
- **Do not connect the external 5V supply's + to the board's +5V pin** (connect it only to the servos' red wires).
- **Suppressing servo jitter**: even while idle (holding position with no command), a servo
  can twitch due to power-rail noise or voltage fluctuation. Connecting an electrolytic
  capacitor (around 470–1000µF, rated 10 V or higher) across the servo power and GND
  (the board's +5V pin or the external 5V supply's +, close to the servos) to stabilize
  the supply suppresses this jitter. Mind the capacitor polarity (+/−).
- See [simple-pinout.png](simple-pinout.png) for the full pinout. This diagram is the Nano R4 pinout by Arduino
  (source: [Arduino Docs](https://github.com/arduino/docs-content/blob/dab66ecbd6ad52cd742da6c19c5b6330a7f2caae/content/hardware/nano/boards/nano-r4/tutorials/01.user-manual/assets/simple-pinout.png), license: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)).

## Build / Upload / Monitor

```bash
# Build
pio run

# Upload (with the board connected)
pio run --target upload

# Serial monitor
pio device monitor -b 115200
```

## Serial Commands

115200 baud. One line = one command, terminated by a newline (`\n` / `\r`).

### Syntax

```text
<cmd>[ch1-3][ <angle>]
```

- `cmd` … command character (see table below)
- `ch` … channel `1`–`3`. **Defaults to CH1 when omitted.**
- `angle` … angle `0`–`180`. **A space before the angle is required.**

### Command list

| cmd | Meaning |
| --- | ------- |
| `o` | Open (move to the configured **open angle**) |
| `c` | Close (move to the configured **close angle**) |
| `O [angle]` | **Set the open angle** and move (without an angle, just moves to the current open angle) |
| `C [angle]` | **Set the close angle** and move (without an angle, just moves to the current close angle) |
| `a` / `A` `<angle>` | Move to an arbitrary angle (angle required; otherwise `ERR: angle required`) |
| `q` / `Q` | Query the current angle |

- Defaults: **open = 90° / close = 0°**
- Angle range is 0–180 (out-of-range values are clamped; non-numeric values are treated as 0)
- On startup each channel is initialized to **closed (0°)**

### Examples

| Input | Action |
| ----- | ------ |
| `o2` | Open CH2 |
| `O1 120` | Set CH1 open angle to 120° and move |
| `A2 90` | Move CH2 to 90° |
| `C3 10` | Set CH3 close angle to 10° and move |
| `q2` | Query CH2's current angle |

### Responses

- On success: a **bare number** (the current angle, or the angle that was set)
- On error: `ERR: ...`
- On unknown command: `UNKNOWN CMD: ...`

## ⚠️ The Case-Sensitivity Trap

The open/close commands **behave differently in lowercase vs uppercase**. Don't mix them up.

- `o` / `c` (lowercase) … **move only** (to the configured open/close angle)
- `O` / `C` (uppercase) … **set the angle, then move**
- However, `a` / `A` and `q` / `Q` are **identical regardless of case**

## Startup Behavior

On power-up or reset, immediately after `attach()`-ing each servo in `setup()`, the firmware
**writes the closed position (0°)** (to suppress the jump to `attach()`'s default 1500µs = 90°).
As a result, all channels move toward closed the moment the board starts.

After startup, the following banner is printed to serial:

```text
READY (3ch servo shutter)
cmd: <o|c|O|C|a|q>[ch1-3][ angle]  e.g. o2 / O1 / A2 90 / C3 10 / q2
```

## Limitations & Notes

- A line is **at most 16 characters** (excess is truncated).
- The channel is **a single digit only**. Inputs like `o12`, where the character right after the
  command/channel is neither a space nor end-of-line, result in `ERR`.
- An argument mistakenly appended to `o` / `c` / `q` is **ignored**.
- Responses **do not include a channel identifier**. The GUI (below) maps each response line back
  to the channel that was sent, in FIFO (send) order.
- Open/close angles are **held in RAM only**. After a reset or power cycle they return to the
  defaults (open 90° / close 0°).
- `q` / `Q` returns the **last commanded angle**, not a measured servo position.

## Test GUI

Open [gui/index.html](gui/index.html) in **Chrome / Edge** to drive each channel with buttons
for testing (uses the Web Serial API). Most of the GUI text is in Japanese (there is no English version).

1. First try opening the HTML directly via `file://`.
2. If that doesn't work, start a simple server from the project root and open `http://localhost:8000/gui/`:
   ```bash
   python -m http.server
   ```
3. **Close any other serial monitor** (such as `pio device monitor`) before clicking Connect
   (the COM port is held exclusively by one process).
4. On Connect, the board may reset and print the READY banner.

## Project Structure

```text
aketeino/
├── src/main.cpp       … Main firmware (3ch servo shutter)
├── gui/index.html     … Host-side test GUI (Web Serial, single HTML, no dependencies)
├── platformio.ini     … PlatformIO config (env: nano_r4)
├── simple-pinout.png  … Nano R4 pinout diagram (by Arduino, CC BY-SA 4.0)
├── CLAUDE.md          … Development rules for Claude Code
└── LICENSE            … MIT License
```

## License

[MIT License](LICENSE)

However, `simple-pinout.png` is a work by Arduino, provided under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
It is not covered by the MIT License.

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
| 2 | Servo motor (3-wire, PWM controlled) | 1–3 | One per shutter channel |
| 3 | Jumper wires / wiring | as needed | For signal, power, and GND |
| 4 | External servo power supply (optional) | 0–1 | Use when servo current draw is high. Share GND with the board |
| 5 | Electrolytic capacitor (optional) | 0–1 | Connect across Vin and GND to suppress idle servo jitter. Around 470–1000µF |

## Wiring

Connect the servo signal lines to the following pins (all PWM-capable).

| Channel | Signal pin |
| ------- | ---------- |
| CH1     | D3         |
| CH2     | D5         |
| CH3     | D6         |

- When driving multiple servos at once, the board's supply may be insufficient — provide a separate 5V supply.
- **Suppressing servo jitter**: even while idle (holding position with no command), a servo
  can twitch due to power-rail noise or voltage fluctuation. Connecting an electrolytic
  capacitor (around 470–1000µF) across Vin and GND to stabilize the supply suppresses this
  jitter. Mind the capacitor polarity (+/−).
- See [simple-pinout.png](simple-pinout.png) for the full pinout.

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

## Test GUI

Open [gui/index.html](gui/index.html) in **Chrome / Edge** to drive each channel with buttons
for testing (uses the Web Serial API).

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
└── simple-pinout.png  … Nano R4 pinout diagram
```

## License

[MIT License](LICENSE)

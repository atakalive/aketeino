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
- **CLI** for terminals, scripts, and LLM agents such as Claude Code

## Requirements

- Arduino Nano R4 (RA4M1 / `nano_r4`)
- Up to 3 servo motors
- PlatformIO (`pio` CLI, or PlatformIO IDE / VS Code extension)
- For the GUI: Chrome or Edge (a browser with Web Serial API support)
- For the CLI: Python 3.9+ and pyserial (or uv)

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
| `s` / `S` | Query the status: current angle, open angle, and close angle |

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
| `s2` | Query CH2's status (e.g. `90 90 0`) |

### Responses

- On success: a **bare number** (the current angle, or the angle that was set)
- `s` / `S` on success: **three numbers separated by single spaces** — `<current angle> <open angle> <close angle>` (e.g. `90 90 0`)
- On error: `ERR: ...`
- On unknown command: `UNKNOWN CMD: ...`

## ⚠️ The Case-Sensitivity Trap

The open/close commands **behave differently in lowercase vs uppercase**. Don't mix them up.

- `o` / `c` (lowercase) … **move only** (to the configured open/close angle)
- `O` / `C` (uppercase) … **set the angle, then move**
- However, `a` / `A`, `q` / `Q`, and `s` / `S` are **identical regardless of case**

## Startup Behavior

On power-up or reset, immediately after `attach()`-ing each servo in `setup()`, the firmware
**writes the closed position (0°)** (to suppress the jump to `attach()`'s default 1500µs = 90°).
As a result, all channels move toward closed the moment the board starts.

After startup, the following banner is printed to serial:

```text
READY (3ch servo shutter)
cmd: <o|c|O|C|a|q|s>[ch1-3][ angle]  e.g. o2 / O1 / A2 90 / C3 10 / q2 / s2
```

## Limitations & Notes

- A line is **at most 16 characters** (excess is truncated).
- The channel is **a single digit only**. Inputs like `o12`, where the character right after the
  command/channel is neither a space nor end-of-line, result in `ERR`.
- An argument mistakenly appended to `o` / `c` / `q` / `s` is **ignored**.
- Responses **do not include a channel identifier**. The GUI (below) maps each response line back
  to the channel that was sent, in FIFO (send) order.
- Open/close angles are **held in RAM only**. After a reset or power cycle they return to the
  defaults (open 90° / close 0°).
- The current angle returned by `q` / `Q` and `s` / `S` is the **last commanded angle**, not a measured servo position.

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

## CLI

[cli/aketeino.py](cli/aketeino.py) drives the board from a terminal. Each call opens the port, sends
the command(s), waits for each reply, prints the result, and exits, so scripts and LLM agents such as
Claude Code can operate the shutter and read its state with ordinary shell commands.

It needs Python 3.9+ and [pyserial](https://pypi.org/project/pyserial/) (`python -m pip install pyserial`).
With [uv](https://docs.astral.sh/uv/), `uv run cli/aketeino.py ...` installs pyserial automatically.

```bash
python cli/aketeino.py ports            # list serial ports (the Nano R4 is marked [Nano R4])
python cli/aketeino.py status           # angle, open/close angles and state of every channel
python cli/aketeino.py open 2           # open CH2
python cli/aketeino.py close all        # close CH1, CH2 and CH3
python cli/aketeino.py move 1 45        # move CH1 to 45°
python cli/aketeino.py set-open 1 120   # set CH1's open angle to 120° and move there
python cli/aketeino.py set-close 3 10   # set CH3's close angle to 10° and move there
python cli/aketeino.py raw q1 "A2 90"   # send firmware command lines as-is
python cli/aketeino.py --help           # full usage, exit codes and notes
```

| CLI | Firmware command sent |
| --- | --------------------- |
| `open <ch>...` | `o` |
| `close <ch>...` | `c` |
| `move <ch> <angle>` | `A <angle>` |
| `set-open <ch> <angle>` | `O <angle>` |
| `set-close <ch> <angle>` | `C <angle>` |
| `status [<ch>...]` | `s` (all channels when `ch` is omitted) |
| `raw <line>...` | the line as-is (1–16 printable ASCII characters) |

- Channels are `1`, `2`, `3` or `all`; angles are integers 0–180. Anything else is rejected before
  anything is sent (the firmware itself would clamp it or treat it as 0 silently).
- Output is one line per result, e.g. `CH2: 90`. `status` prints:
  ```text
  port: COM5
  CH1: 90 (open) open=90 close=0
  CH2: 0 (closed) open=90 close=0
  CH3: 45 (other) open=120 close=10
  ```
  The state is `open` when the angle equals the open angle, `closed` when it equals the close angle,
  and `other` otherwise. The angles are the last commanded ones, not measured servo positions.
- `--json` prints `{"port": "COM5", "results": [...]}`. On failure it prints the results so far plus
  `"error": {"code": ..., "message": ...}`.
- Requests run in order and stop at the first failure. Errors go to stderr with a hint on what to do.
- Port: `--port COM5`, else the `AKETEINO_PORT` environment variable, else the only connected Nano R4
  (USB VID 2341 / PID 0074). If none or more than one is found, pass `--port`.
- **Close the GUI and `pio device monitor` before using the CLI** (the COM port is held exclusively by
  one process). The CLI cannot open a port that another program holds.
- `status` needs firmware with the `s` command. With older firmware it tells you to upload
  (`pio run --target upload`).

| Exit code | Meaning |
| --------- | ------- |
| 0 | Success |
| 1 | The board replied `ERR` / `UNKNOWN CMD`, or an unexpected reply |
| 2 | Bad arguments (nothing was sent) |
| 3 | Port not found, cannot be opened, or lost (e.g. the board reset) |
| 4 | No reply in time (`--timeout`, default 2 s) |

The tests run without a board: `python -m unittest discover -s cli -v`.

## Project Structure

```text
aketeino/
├── src/main.cpp       … Main firmware (3ch servo shutter)
├── gui/index.html     … Host-side test GUI (Web Serial, single HTML, no dependencies)
├── cli/               … Host-side CLI (aketeino.py, pyserial) and its tests
├── platformio.ini     … PlatformIO config (env: nano_r4)
├── simple-pinout.png  … Nano R4 pinout diagram (by Arduino, CC BY-SA 4.0)
├── CLAUDE.md          … Development rules for Claude Code
└── LICENSE            … MIT License
```

## License

[MIT License](LICENSE)

However, `simple-pinout.png` is a work by Arduino, provided under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
It is not covered by the MIT License.

#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyserial>=3.5"]
# ///
"""aketeino 3ch サーボシャッターを USB シリアルで操作する CLI。

LLM(Claude Code など)が Bash から呼び、標準出力と終了コードで結果を読めるようにする。
応答にチャネルが含まれないため、1 行送るごとに応答 1 行を待つ同期方式にしている。
ファームの文法は src/main.cpp の processCommand を参照。
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from typing import NamedTuple

try:
    import serial
    from serial.tools import list_ports as _list_ports
except ImportError:  # --help は pyserial が無くても見られるようにする
    serial = None
    _list_ports = None

BAUD = 115200          # 固定。1200 で開くとボードがブートローダに入る
NANO_R4_VID = 0x2341
NANO_R4_PID = 0x0074
MAX_LINE = 16          # ファームは 1 行 16 文字を超えた分を黙って捨てる
CHANNELS = (1, 2, 3)
READ_POLL = 0.05       # read() 1 回で待つ秒数
SETTLE_SECONDS = 0.1   # 開いてから DTR がボードに届くまで待つ(届く前の受信はファームが壊す)

EXIT_OK = 0
EXIT_DEVICE = 1
EXIT_USAGE = 2         # argparse の既定と同じ
EXIT_PORT = 3
EXIT_TIMEOUT = 4

_INT_LINE = re.compile(r"-?[0-9]+(?:\s+-?[0-9]+)*")
_ANGLE = re.compile(r"[0-9]+")

EPILOG = f"""\
examples:
  %(prog)s status               all channels: angle, open/close angles, state
  %(prog)s open 2               open CH2
  %(prog)s close all            close CH1, CH2 and CH3
  %(prog)s move 1 45            move CH1 to 45 degrees
  %(prog)s set-open 1 120       set CH1's open angle to 120 and move there
  %(prog)s status 1 --json      machine-readable output
  %(prog)s raw q1 "A2 90"       send firmware command lines as-is

channels: 1, 2, 3 or all.  angles: integers 0-180.

port: --port, else the AKETEINO_PORT environment variable, else the only
connected Nano R4 (USB VID {NANO_R4_VID:04X} / PID {NANO_R4_PID:04X}).
Close the GUI (gui/index.html) and `pio device monitor` first: only one
program can use the port at a time.

exit codes:
  0  success
  1  the board replied ERR / UNKNOWN CMD, or an unexpected reply
  2  bad arguments (nothing was sent)
  3  port not found, cannot be opened, or lost (e.g. the board reset)
  4  no reply in time

notes:
  These commands move real servos.
  Angles are the last commanded values, not measured servo positions.
  After a reset or power cycle every channel is at 0 with open=90 close=0.
  Requests run in order and stop at the first failure.
"""


class CliError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class Request(NamedTuple):
    line: str            # ボードへ送る 1 行(改行なし)
    ch: int | None    # raw は None


# ---- 引数の検証(ここで弾いたものは何も送らない) ----

def channel_arg(text: str) -> list:
    if text.lower() == "all":
        return list(CHANNELS)
    if text in ("1", "2", "3"):
        return [int(text)]
    raise argparse.ArgumentTypeError(f"invalid channel {text!r} (use 1, 2, 3 or all)")


def angle_arg(text: str) -> int:
    # ファームは範囲外を黙ってクランプし、数字でなければ 0 にするので、ここで弾く
    if _ANGLE.fullmatch(text) and int(text) <= 180:
        return int(text)
    raise argparse.ArgumentTypeError(f"invalid angle {text!r} (use an integer 0-180)")


def raw_line_arg(text: str) -> str:
    if 1 <= len(text) <= MAX_LINE and all(" " <= c <= "~" for c in text):
        return text
    raise argparse.ArgumentTypeError(
        f"invalid raw line {text!r} (1-{MAX_LINE} printable ASCII characters, no newline)")


def timeout_arg(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        value = math.nan
    if math.isfinite(value) and value > 0:
        return value
    raise argparse.ArgumentTypeError(f"invalid timeout {text!r} (use a positive number of seconds)")


CH_HELP = "channel: 1, 2, 3 or all"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Control the aketeino 3-channel servo shutter (Arduino Nano R4) over USB serial.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # 共通オプションはサブコマンドの前でも後でも書けるようにする。
    # サブコマンド側は SUPPRESS にして、書かなかったときに前の値を上書きしない
    parser.add_argument("--port", default=None,
                        help="serial port (e.g. COM5, /dev/ttyACM0)")
    parser.add_argument("--timeout", type=timeout_arg, default=2.0,
                        help="seconds to wait for each reply (default: 2)")
    parser.add_argument("--json", action="store_true", help="print JSON")

    json_opt = argparse.ArgumentParser(add_help=False)
    json_opt.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="print JSON")
    conn_opts = argparse.ArgumentParser(add_help=False, parents=[json_opt])
    conn_opts.add_argument("--port", default=argparse.SUPPRESS, help="serial port")
    conn_opts.add_argument("--timeout", type=timeout_arg, default=argparse.SUPPRESS,
                           help="seconds to wait for each reply")

    sub = parser.add_subparsers(dest="command", metavar="COMMAND", required=True)

    sub.add_parser("ports", parents=[json_opt],
                   help="list serial ports; the Nano R4 is marked [Nano R4]")

    p = sub.add_parser("open", parents=[conn_opts], help="move channels to their open angle")
    p.add_argument("channels", nargs="+", type=channel_arg, metavar="CH", help=CH_HELP)
    p = sub.add_parser("close", parents=[conn_opts], help="move channels to their close angle")
    p.add_argument("channels", nargs="+", type=channel_arg, metavar="CH", help=CH_HELP)

    for name, text in (
        ("move", "move a channel to ANGLE (the open/close angles stay as they are)"),
        ("set-open", "set a channel's open angle to ANGLE and move there"),
        ("set-close", "set a channel's close angle to ANGLE and move there"),
    ):
        p = sub.add_parser(name, parents=[conn_opts], help=text, description=text)
        p.add_argument("channel", type=channel_arg, metavar="CH", help=CH_HELP)
        p.add_argument("angle", type=angle_arg, metavar="ANGLE", help="integer 0-180")

    status_text = (
        "show each channel's angle, open/close angles and state (all channels if CH is omitted). "
        "state is open if angle == open angle, closed if angle == close angle, otherwise other. "
        "Angles are the last commanded values, not measured servo positions.")
    p = sub.add_parser("status", parents=[conn_opts], help="show angles and state of channels",
                       description=status_text)
    p.add_argument("channels", nargs="*", type=channel_arg, metavar="CH", help=CH_HELP)

    raw_text = ("send firmware command lines as-is and print each reply "
                "(see README 'Serial Commands'). Quote a line that has a space.")
    p = sub.add_parser("raw", parents=[conn_opts], help="send firmware command lines as-is",
                       description=raw_text)
    p.add_argument("lines", nargs="+", type=raw_line_arg, metavar="LINE",
                   help=f"firmware command line: 1-{MAX_LINE} printable ASCII characters")
    return parser


def _unique(groups) -> list:
    """チャネルの並びを、順を保って重なりを 1 回にまとめる。"""
    chs = []
    for group in groups:
        for ch in group:
            if ch not in chs:
                chs.append(ch)
    return chs


def build_requests(args) -> list:
    cmd = args.command
    if cmd == "raw":
        return [Request(line, None) for line in args.lines]
    if cmd == "status":
        return [Request(f"s{ch}", ch) for ch in (_unique(args.channels) or list(CHANNELS))]
    if cmd in ("open", "close"):
        letter = "o" if cmd == "open" else "c"
        return [Request(f"{letter}{ch}", ch) for ch in _unique(args.channels)]
    letter = {"move": "A", "set-open": "O", "set-close": "C"}[cmd]
    return [Request(f"{letter}{ch} {args.angle}", ch) for ch in _unique([args.channel])]


# ---- ポート ----

def _require_pyserial():
    if serial is None:
        raise CliError(EXIT_PORT, "pyserial is not installed. Run `python -m pip install pyserial`, "
                                  "or run this script with `uv run cli/aketeino.py ...`.")


def default_open_serial(port: str, timeout: float):
    _require_pyserial()
    # DTR は pyserial の既定どおり立てる(ボードは DTR が無いと送受信を捨てる)。
    # exclusive は Windows では既定どおり、Linux/macOS では CLI 同士の混線を防ぐ
    return serial.Serial(port, BAUD, timeout=READ_POLL, write_timeout=timeout, exclusive=True)


def default_list_ports() -> list:
    _require_pyserial()
    return list(_list_ports.comports())


def is_nano_r4(info) -> bool:
    return info.vid == NANO_R4_VID and info.pid == NANO_R4_PID


def resolve_port(port, environ, list_ports) -> str:
    if port:
        return port
    env = environ.get("AKETEINO_PORT", "").strip()
    if env:
        return env
    infos = list_ports()
    found = sorted(info.device for info in infos if is_nano_r4(info))
    if len(found) == 1:
        return found[0]
    if not found:
        others = ", ".join(sorted(info.device for info in infos)) or "none"
        raise CliError(EXIT_PORT,
                       f"no Arduino Nano R4 found (USB VID {NANO_R4_VID:04X} / PID {NANO_R4_PID:04X}; "
                       f"ports present: {others}). Connect the board, or pass --port.")
    raise CliError(EXIT_PORT, f"more than one Nano R4 found ({', '.join(found)}). "
                              "Choose one with --port or AKETEINO_PORT.")


# ---- 送受信 ----

def _is_write_timeout(exc: BaseException) -> bool:
    return serial is not None and isinstance(exc, serial.SerialTimeoutException)


class Board:
    def __init__(self, ser, timeout: float):
        self.ser = ser
        self.timeout = timeout
        self._buf = bytearray()

    def ask(self, line: str) -> str:
        """1 行送り、応答の 1 行(数値の行か ERR/UNKNOWN の行)を返す。起動バナーなどは読み飛ばす。"""
        self.ser.write(line.encode("ascii") + b"\n")
        deadline = time.monotonic() + self.timeout
        while True:
            reply = self._next_line(deadline)
            if reply is None:
                raise CliError(EXIT_TIMEOUT,
                               f"no reply to {line!r} within {self.timeout:g} s. Check that the board "
                               "runs the aketeino firmware (pio run --target upload) and that the port is right.")
            if _INT_LINE.fullmatch(reply) or reply.startswith(("ERR:", "UNKNOWN")):
                return reply

    def _next_line(self, deadline: float) -> str | None:
        while True:
            nl = self._buf.find(b"\n")
            if nl >= 0:
                text = bytes(self._buf[:nl]).decode("ascii", "replace").strip()
                del self._buf[:nl + 1]
                if text:
                    return text
                continue
            if time.monotonic() >= deadline:
                return None
            chunk = self.ser.read(max(1, self.ser.in_waiting))
            if chunk:
                self._buf += chunk


def interpret(req: Request, reply: str) -> dict:
    if reply.startswith(("ERR:", "UNKNOWN")):
        message = f"the board rejected {req.line!r}: {reply}"
        if req.line[0] in "sS" and reply.startswith("UNKNOWN CMD"):
            message += (" -- the firmware on the board is older than this CLI and has no 's' command. "
                        "Upload the current firmware with `pio run --target upload`.")
        raise CliError(EXIT_DEVICE, message)
    if req.ch is None:
        return {"sent": req.line, "reply": reply}
    nums = [int(x) for x in reply.split()]
    is_status = req.line[0] == "s"
    expected = 3 if is_status else 1
    if len(nums) != expected:
        raise CliError(EXIT_DEVICE, f"unexpected reply to {req.line!r}: {reply!r} "
                                    f"(expected {expected} number{'s' if expected > 1 else ''})")
    if not is_status:
        return {"ch": req.ch, "sent": req.line, "angle": nums[0]}
    angle, open_angle, close_angle = nums
    if angle == open_angle:
        state = "open"
    elif angle == close_angle:
        state = "closed"
    else:
        state = "other"
    return {"ch": req.ch, "sent": req.line, "angle": angle,
            "open": open_angle, "close": close_angle, "state": state}


def format_result(item: dict) -> str:
    if "ch" not in item:
        return f"{item['sent']}: {item['reply']}"
    if "state" in item:
        return (f"CH{item['ch']}: {item['angle']} ({item['state']}) "
                f"open={item['open']} close={item['close']}")
    return f"CH{item['ch']}: {item['angle']}"


# ---- サブコマンド ----

def run_ports(args, list_ports, out) -> int:
    infos = sorted(list_ports(), key=lambda info: info.device)
    if args.json:
        ports = [{"device": info.device, "description": info.description, "hwid": info.hwid,
                  "nano_r4": is_nano_r4(info)} for info in infos]
        print(json.dumps({"ports": ports}, ensure_ascii=False), file=out)
        return EXIT_OK
    if not infos:
        print("no serial ports found", file=out)
    for info in infos:
        mark = "  [Nano R4]" if is_nano_r4(info) else ""
        print(f"{info.device}  {info.description}{mark}", file=out)
    return EXIT_OK


def run_requests(args, requests, result, open_serial, list_ports, environ, out) -> None:
    port = resolve_port(args.port, environ, list_ports)
    result["port"] = port
    try:
        ser = open_serial(port, args.timeout)
    except OSError as exc:
        raise CliError(EXIT_PORT, f"cannot open {port}: {exc}. If the GUI (gui/index.html) or "
                                  "`pio device monitor` is connected, close it and retry (only one program "
                                  "can use the port at a time). List ports with the `ports` command.") from exc
    req = None
    try:
        time.sleep(SETTLE_SECONDS)
        ser.reset_input_buffer()
        if args.command == "status" and not args.json:
            print(f"port: {port}", file=out, flush=True)
        board = Board(ser, args.timeout)
        for req in requests:
            reply = board.ask(req.line)
            item = interpret(req, reply)
            result["results"].append(item)
            if not args.json:
                print(format_result(item), file=out, flush=True)
    except OSError as exc:
        if _is_write_timeout(exc):
            raise CliError(EXIT_TIMEOUT, f"the board did not accept {req.line!r} within "
                                         f"{args.timeout:g} s: {exc}") from exc
        raise CliError(EXIT_PORT, f"lost the connection to {port}: {exc}. The board may have "
                                  "reset (for example a servo drew too much current); its open/close "
                                  "angles are then back to open=90 close=0. See the power notes in "
                                  "the README wiring section.") from exc
    finally:
        try:
            ser.close()
        except OSError:
            pass


def main(argv=None, *, open_serial=None, list_ports=None, environ=None, out=None, err=None) -> int:
    open_serial = open_serial or default_open_serial
    list_ports = list_ports or default_list_ports
    environ = os.environ if environ is None else environ
    out = out or sys.stdout
    err = err or sys.stderr

    args = build_parser().parse_args(argv)
    if args.command == "ports":
        try:
            return run_ports(args, list_ports, out)
        except CliError as exc:
            print(f"error: {exc.message}", file=err)
            if args.json:
                print(json.dumps({"ports": [], "error": {"code": exc.code, "message": exc.message}}), file=out)
            return exc.code

    requests = build_requests(args)
    result = {"port": None, "results": []}
    try:
        run_requests(args, requests, result, open_serial, list_ports, environ, out)
    except CliError as exc:
        print(f"error: {exc.message}", file=err)
        if args.json:
            result["error"] = {"code": exc.code, "message": exc.message}
            print(json.dumps(result, ensure_ascii=False), file=out)
        return exc.code
    if args.json:
        print(json.dumps(result, ensure_ascii=False), file=out)
    return EXIT_OK


if __name__ == "__main__":
    # Windows でパイプにつなぐと cp932 になり、ポートの説明などが化けるため UTF-8 にする
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    sys.exit(main())

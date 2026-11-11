"""cli/aketeino.py のテスト(実機なし)。

実行: python -m unittest discover -s cli -v
"""

import io
import json
import re
import time
import unittest
from contextlib import redirect_stderr
from types import SimpleNamespace
from unittest import mock

import aketeino
import serial

BANNER = (b"READY (3ch servo shutter)\r\n"
          b"cmd: <o|c|O|C|a|q|s>[ch1-3][ angle]  e.g. o2 / O1 / A2 90 / C3 10 / q2 / s2\r\n")


class FakeBoard:
    """src/main.cpp の loop / processCommand を真似た偽のボード(pyserial の Serial の代わり)。"""

    def __init__(self, knows_s=True, banner_before_reply=False, silent=False, override=None,
                 read_error=None, write_error=None):
        self.angle_open = [90, 90, 90]
        self.angle_closed = [0, 0, 0]
        self.current = [0, 0, 0]
        self.knows_s = knows_s
        self.banner_before_reply = banner_before_reply
        self.silent = silent
        self.override = override or {}    # 受けた行 -> 返す行(ファームと違う応答を作る)
        self.read_error = read_error
        self.write_error = write_error
        self.lines = []                   # ボードが受けた行
        self.closed = False
        self._cmd = ""
        self._tx = bytearray(b"stale\r\n")  # 開く前の受信の残り(reset_input_buffer で消えるはず)

    # ---- pyserial の Serial と同じ口 ----
    @property
    def in_waiting(self):
        return len(self._tx)

    def reset_input_buffer(self):
        self._tx.clear()

    def write(self, data):
        if self.write_error:
            raise self.write_error
        for b in data.decode("latin-1"):
            if b in "\r\n":
                if self._cmd:
                    self._process_line(self._cmd)
                    self._cmd = ""
            elif len(self._cmd) < 16:
                self._cmd += b
        return len(data)

    def read(self, size=1):
        if self.read_error:
            raise self.read_error
        if not self._tx:
            time.sleep(0.001)
            return b""
        chunk = bytes(self._tx[:size])
        del self._tx[:size]
        return chunk

    def close(self):
        self.closed = True

    # ---- ファームの真似 ----
    def _process_line(self, cmd):
        self.lines.append(cmd)
        if self.banner_before_reply:
            self._tx += BANNER
            self.banner_before_reply = False
        if self.silent:
            return
        reply = self.override.get(cmd)
        if reply is None:
            reply = self._process_command(cmd)
        self._tx += reply.encode("ascii") + b"\r\n"

    @staticmethod
    def _parse_angle(s):
        m = re.match(r"\s*([-+]?\d+)", s)    # String::toInt と同じく先頭の数字だけ読む
        val = int(m.group(1)) if m else 0
        return max(0, min(180, val))

    def _process_command(self, cmd):
        c0 = cmd[0]
        ch = 0
        pos = 1
        if len(cmd) > pos and "1" <= cmd[pos] <= "3":
            ch = int(cmd[pos]) - 1
            pos += 1
        arg = ""
        if len(cmd) > pos:
            if cmd[pos] != " ":
                return f"ERR: use <cmd>[1-3] [angle]: {cmd}"
            arg = cmd[pos + 1:].strip()
        if c0 == "o":
            self.current[ch] = self.angle_open[ch]
            return str(self.current[ch])
        if c0 in "OC":
            table = self.angle_open if c0 == "O" else self.angle_closed
            if arg:
                table[ch] = self._parse_angle(arg)
            self.current[ch] = table[ch]
            return str(self.current[ch])
        if c0 == "c":
            self.current[ch] = self.angle_closed[ch]
            return str(self.current[ch])
        if c0 in "aA":
            if not arg:
                return f"ERR: angle required: {cmd}"
            self.current[ch] = self._parse_angle(arg)
            return str(self.current[ch])
        if c0 in "qQ":
            return str(self.current[ch])
        if c0 in "sS" and self.knows_s:
            return f"{self.current[ch]} {self.angle_open[ch]} {self.angle_closed[ch]}"
        return f"UNKNOWN CMD: {cmd}"


def port_info(device, vid=None, pid=None, description="n/a"):
    return SimpleNamespace(device=device, vid=vid, pid=pid, description=description, hwid="")


NANO = port_info("COM5", aketeino.NANO_R4_VID, aketeino.NANO_R4_PID, "USB Serial Device (COM5)")
OTHER = port_info("COM1", description="通信ポート (COM1)")


class CliTestCase(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(aketeino, "SETTLE_SECONDS", 0)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.board = FakeBoard()
        self.opened = []
        self.ports = [OTHER, NANO]
        self.environ = {}

    def open_serial(self, port, timeout):
        self.opened.append(port)
        return self.board

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        code = aketeino.main(list(argv), open_serial=self.open_serial, list_ports=lambda: self.ports,
                             environ=self.environ, out=out, err=err)
        return code, out.getvalue(), err.getvalue()

    def assert_usage_error(self, *argv):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
            self.run_cli(*argv)
        self.assertEqual(cm.exception.code, aketeino.EXIT_USAGE)
        self.assertEqual(self.opened, [], "nothing must be sent on bad arguments")


class TestCommands(CliTestCase):
    def test_open_close(self):
        code, out, _ = self.run_cli("open", "2")
        self.assertEqual((code, out), (0, "CH2: 90\n"))
        code, out, _ = self.run_cli("close", "2")
        self.assertEqual((code, out), (0, "CH2: 0\n"))
        self.assertEqual(self.board.lines, ["o2", "c2"])
        self.assertTrue(self.board.closed)

    def test_all_expands_and_removes_duplicates_in_order(self):
        code, out, _ = self.run_cli("close", "2", "all", "1")
        self.assertEqual(code, 0)
        self.assertEqual(self.board.lines, ["c2", "c1", "c3"])
        self.assertEqual(out, "CH2: 0\nCH1: 0\nCH3: 0\n")

    def test_move_and_set_angles(self):
        self.assertEqual(self.run_cli("move", "1", "45")[:2], (0, "CH1: 45\n"))
        self.assertEqual(self.run_cli("set-open", "3", "120")[:2], (0, "CH3: 120\n"))
        self.assertEqual(self.run_cli("set-close", "2", "10")[:2], (0, "CH2: 10\n"))
        self.assertEqual(self.run_cli("move", "all", "0")[0], 0)
        self.assertEqual(self.board.lines, ["A1 45", "O3 120", "C2 10", "A1 0", "A2 0", "A3 0"])
        self.assertEqual(self.board.angle_open, [90, 90, 120])
        self.assertEqual(self.board.angle_closed, [0, 10, 0])

    def test_status_text(self):
        self.board.current = [90, 0, 45]
        self.board.angle_open = [90, 90, 120]
        self.board.angle_closed = [0, 0, 10]
        code, out, _ = self.run_cli("status")
        self.assertEqual(code, 0)
        self.assertEqual(self.board.lines, ["s1", "s2", "s3"])
        self.assertEqual(out, "port: COM5\n"
                              "CH1: 90 (open) open=90 close=0\n"
                              "CH2: 0 (closed) open=90 close=0\n"
                              "CH3: 45 (other) open=120 close=10\n")

    def test_status_open_wins_when_open_equals_close(self):
        self.board.angle_open[1] = self.board.angle_closed[1] = self.board.current[1] = 30
        code, out, _ = self.run_cli("status", "2")
        self.assertEqual((code, out), (0, "port: COM5\nCH2: 30 (open) open=30 close=30\n"))

    def test_status_json(self):
        code, out, _ = self.run_cli("status", "1", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), {
            "port": "COM5",
            "results": [{"ch": 1, "sent": "s1", "angle": 0, "open": 90, "close": 0, "state": "closed"}],
        })

    def test_json_option_before_and_after_command(self):
        for argv in (("--json", "open", "1"), ("open", "1", "--json")):
            code, out, _ = self.run_cli(*argv)
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["results"], [{"ch": 1, "sent": "o1", "angle": 90}])

    def test_raw(self):
        code, out, _ = self.run_cli("raw", "q2", "A2 90", "s2")
        self.assertEqual(code, 0)
        self.assertEqual(out, "q2: 0\nA2 90: 90\ns2: 90 90 0\n")
        code, out, _ = self.run_cli("raw", "q2", "--json")
        self.assertEqual(json.loads(out)["results"], [{"sent": "q2", "reply": "90"}])

    def test_banner_and_stale_input_are_skipped(self):
        self.board.banner_before_reply = True
        code, out, _ = self.run_cli("open", "1")
        self.assertEqual((code, out), (0, "CH1: 90\n"))

    def test_help_lists_exit_codes(self):
        out = io.StringIO()
        with mock.patch("sys.stdout", out), self.assertRaises(SystemExit) as cm:
            aketeino.main(["--help"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("exit codes:", out.getvalue())
        self.assertIn("set-open", out.getvalue())


class TestValidation(CliTestCase):
    def test_bad_angles(self):
        for angle in ("-5", "181", "200", "90.0", "+90", "abc", "", "１８０"):
            with self.subTest(angle=angle):
                self.assert_usage_error("move", "1", angle)

    def test_bad_channels(self):
        for ch in ("0", "4", "x", "12"):
            with self.subTest(ch=ch):
                self.assert_usage_error("open", ch)

    def test_missing_arguments(self):
        self.assert_usage_error("open")
        self.assert_usage_error("move", "1")
        self.assert_usage_error("raw")
        self.assert_usage_error()

    def test_bad_raw_lines(self):
        for line in ("", "x" * 17, "a\nb", "o1\r", "é1"):
            with self.subTest(line=line):
                self.assert_usage_error("raw", line)

    def test_raw_line_of_16_characters_is_allowed(self):
        code, _, err = self.run_cli("raw", "A1 " + "0" * 13)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.board.lines, ["A1 " + "0" * 13])

    def test_bad_timeout(self):
        for value in ("0", "-1", "abc", "nan", "inf"):
            with self.subTest(value=value):
                self.assert_usage_error("--timeout", value, "status")


class TestDeviceErrors(CliTestCase):
    def test_err_reply(self):
        code, out, err = self.run_cli("raw", "a1")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("ERR: angle required: a1", err)

    def test_unknown_reply(self):
        code, _, err = self.run_cli("raw", "x")
        self.assertEqual(code, 1)
        self.assertIn("UNKNOWN CMD: x", err)

    def test_old_firmware_without_s(self):
        self.board.knows_s = False
        code, out, err = self.run_cli("status")
        self.assertEqual(code, 1)
        self.assertEqual(out, "port: COM5\n")
        self.assertIn("pio run --target upload", err)
        self.assertEqual(self.board.lines, ["s1"])

    def test_unexpected_number_count(self):
        self.board.override = {"o1": "1 2", "s1": "90"}
        self.assertEqual(self.run_cli("open", "1")[0], 1)
        code, _, err = self.run_cli("status", "1")
        self.assertEqual(code, 1)
        self.assertIn("expected 3 numbers", err)

    def test_stops_at_first_failure_and_keeps_partial_results(self):
        self.board.override = {"o2": "ERR: boom"}
        code, out, _ = self.run_cli("open", "all")
        self.assertEqual((code, out), (1, "CH1: 90\n"))
        self.assertEqual(self.board.lines, ["o1", "o2"])

        self.board.lines.clear()
        code, out, _ = self.run_cli("open", "all", "--json")
        data = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual(data["results"], [{"ch": 1, "sent": "o1", "angle": 90}])
        self.assertEqual(data["error"]["code"], 1)
        self.assertIn("ERR: boom", data["error"]["message"])

    def test_timeout(self):
        self.board.silent = True
        start = time.monotonic()
        code, out, err = self.run_cli("--timeout", "0.2", "open", "1", "--json")
        self.assertLess(time.monotonic() - start, 2)
        self.assertEqual(code, aketeino.EXIT_TIMEOUT)
        self.assertIn("no reply", err)
        self.assertEqual(json.loads(out)["error"]["code"], aketeino.EXIT_TIMEOUT)

    def test_timeout_is_not_extended_by_banner_lines(self):
        self.board.silent = True
        self.board.banner_before_reply = True
        code, _, _ = self.run_cli("open", "1", "--timeout", "0.2")
        self.assertEqual(code, aketeino.EXIT_TIMEOUT)


class TestPortErrors(CliTestCase):
    def test_write_timeout(self):
        self.board.write_error = serial.SerialTimeoutException("Write timeout")
        code, _, err = self.run_cli("open", "1")
        self.assertEqual(code, aketeino.EXIT_TIMEOUT)
        self.assertIn("did not accept", err)
        self.assertTrue(self.board.closed)

    def test_port_lost_while_reading(self):
        self.board.read_error = serial.SerialException("ClearCommError failed")
        code, _, err = self.run_cli("status")
        self.assertEqual(code, aketeino.EXIT_PORT)
        self.assertIn("lost the connection", err)
        self.assertIn("open=90 close=0", err)
        self.assertTrue(self.board.closed)

    def test_cannot_open(self):
        def busy(port, timeout):
            raise serial.SerialException(f"could not open port '{port}': PermissionError(13)")
        out, err = io.StringIO(), io.StringIO()
        code = aketeino.main(["status", "--json"], open_serial=busy, list_ports=lambda: self.ports,
                             environ={}, out=out, err=err)
        self.assertEqual(code, aketeino.EXIT_PORT)
        self.assertIn("pio device monitor", err.getvalue())
        self.assertEqual(json.loads(out.getvalue())["port"], "COM5")


class TestPortSelection(CliTestCase):
    def test_option_wins_over_environment(self):
        self.environ = {"AKETEINO_PORT": "COM8"}
        self.run_cli("--port", "COM9", "open", "1")
        self.run_cli("open", "1", "--port", "COM7")
        self.assertEqual(self.opened, ["COM9", "COM7"])

    def test_environment_wins_over_detection(self):
        self.environ = {"AKETEINO_PORT": "COM8"}
        self.run_cli("open", "1")
        self.assertEqual(self.opened, ["COM8"])

    def test_detects_single_nano_r4(self):
        self.run_cli("open", "1")
        self.assertEqual(self.opened, ["COM5"])

    def test_no_nano_r4(self):
        self.ports = [OTHER]
        code, _, err = self.run_cli("open", "1")
        self.assertEqual(code, aketeino.EXIT_PORT)
        self.assertIn("no Arduino Nano R4 found", err)
        self.assertIn("COM1", err)
        self.assertEqual(self.opened, [])

    def test_two_nano_r4(self):
        self.ports = [NANO, port_info("COM6", aketeino.NANO_R4_VID, aketeino.NANO_R4_PID)]
        code, _, err = self.run_cli("open", "1")
        self.assertEqual(code, aketeino.EXIT_PORT)
        self.assertIn("COM5, COM6", err)
        self.assertEqual(self.opened, [])


class TestPorts(CliTestCase):
    def test_text(self):
        code, out, _ = self.run_cli("ports")
        self.assertEqual(code, 0)
        self.assertEqual(out, "COM1  通信ポート (COM1)\nCOM5  USB Serial Device (COM5)  [Nano R4]\n")

    def test_json(self):
        code, out, _ = self.run_cli("ports", "--json")
        self.assertEqual(code, 0)
        ports = json.loads(out)["ports"]
        self.assertEqual([(p["device"], p["nano_r4"]) for p in ports], [("COM1", False), ("COM5", True)])

    def test_none(self):
        self.ports = []
        self.assertEqual(self.run_cli("ports")[:2], (0, "no serial ports found\n"))


if __name__ == "__main__":
    unittest.main()

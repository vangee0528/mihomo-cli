import errno
import fcntl
import http.server
import json
import os
from pathlib import Path
import pty
import re
import select
import struct
import subprocess
import termios
import threading
import time
import unittest
import urllib.parse


CLI = Path(__file__).resolve().parents[1] / "mihomo-cli"
GROUP = "🚀 节点选择"
HK = '🇭🇰 香港 "01"'
NODES = ["DIRECT", HK, "故障节点"]
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


class MockController(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self):
        super().__init__(("127.0.0.1", 0), MockHandler)
        self.calls = []
        self.group_status = 200
        self.group_body = {"DIRECT": 42, HK: 135}
        self.single_status = 200
        self.single_body = {"delay": 17}


class MockHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = urllib.parse.unquote(parsed.path)
        self.server.calls.append({
            "method": "GET", "path": path,
            "query": urllib.parse.parse_qs(parsed.query),
            "authorization": self.headers.get("Authorization"),
        })
        status = 200
        if path == "/version":
            body = {"version": "test-kernel", "meta": True}
        elif path == "/configs":
            body = {"mode": "rule", "mixed-port": 7890}
        elif path == "/connections":
            body = {"connections": [], "uploadTotal": 0, "downloadTotal": 0}
        elif path == "/proxies":
            proxies = {
                name: {"type": "Direct" if name == "DIRECT" else "Trojan",
                       "history": [{"delay": delay}]}
                for name, delay in zip(NODES, [21, 72, 77])
            }
            proxies[GROUP] = {"type": "Selector", "all": NODES, "now": HK}
            body = {"proxies": proxies}
        elif path == "/group/{}/delay".format(GROUP):
            status, body = self.server.group_status, self.server.group_body
        elif path.startswith("/proxies/") and path.endswith("/delay"):
            status, body = self.server.single_status, self.server.single_body
        else:
            status, body = 404, {"message": "unknown test endpoint"}
        encoded = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def reject_mutation(self):
        self.server.calls.append({"method": self.command, "path": self.path})
        self.send_response(405)
        self.end_headers()

    do_POST = reject_mutation
    do_PUT = reject_mutation
    do_PATCH = reject_mutation
    do_DELETE = reject_mutation


class CliTests(unittest.TestCase):
    def setUp(self):
        self.server = MockController()
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.env = dict(os.environ)
        for name in list(self.env):
            if name.startswith("MIHOMO_"):
                self.env.pop(name)
        self.env.update({
            "MIHOMO_API": "http://127.0.0.1:{}".format(self.server.server_port),
            "TERM": "xterm-256color",
        })

    def tearDown(self):
        self.assertTrue(all(call["method"] == "GET" for call in self.server.calls),
                        "tests must not switch nodes, change mode, or close connections")
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=2)

    def run_cli(self, *args, env=None):
        return subprocess.run([str(CLI), *args], env=env or self.env,
                              text=True, capture_output=True, timeout=8)

    def run_function(self, code, *args):
        return subprocess.run(
            ["/usr/bin/bash", "--noprofile", "--norc", "-c",
             'source "$1"; shift; ' + code, "test", str(CLI), *args],
            env=self.env, text=True, capture_output=True, timeout=8,
        )

    def run_tui_key(self, key, expected_status, timeout=6):
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 45, 160, 0, 0))
        process = subprocess.Popen([str(CLI)], stdin=slave, stdout=slave, stderr=slave,
                                   env=self.env, start_new_session=True)
        os.close(slave)
        output = bytearray()

        def read_until(text):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if text.encode() in output:
                    return
                if process.poll() is not None:
                    break
                ready, _, _ = select.select([master], [], [], 0.1)
                if ready:
                    try:
                        chunk = os.read(master, 65536)
                    except OSError as error:
                        if error.errno == errno.EIO:
                            break
                        raise
                    if not chunk:
                        break
                    output.extend(chunk)
            self.fail("TUI did not reach {!r}: {}".format(
                text, ANSI.sub("", output.decode(errors="replace"))))

        try:
            read_until("按 't' 自动测速")
            output.clear()
            os.write(master, key)
            read_until(expected_status)
            frame = bytes(output).split(b"\x1b[H\x1b[2J")[-1]
            os.write(master, b"q")
            self.assertEqual(process.wait(timeout=3), 0)
            return ANSI.sub("", frame.decode(errors="replace")).replace("\r", "")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
            os.close(master)

    def test_source_does_not_start_ui_or_install_cleanup_trap(self):
        result = self.run_function('declare -F delay_for_node; trap -p EXIT')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "delay_for_node")
        self.assertEqual(self.server.calls, [])

    def test_input_eof_exits_without_switching_nodes_or_closing_connections(self):
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 45, 160, 0, 0))
        process = subprocess.Popen(
            ["/usr/bin/bash", "--noprofile", "--norc", "-c",
             'source "$1"; read_key() { return 1; }; tui_main', "test", str(CLI)],
            stdin=slave, stdout=slave, stderr=slave, env=self.env, start_new_session=True,
        )
        os.close(slave)
        try:
            self.assertEqual(process.wait(timeout=4), 0)
            self.assertTrue(self.server.calls)
            self.assertTrue(all(call["method"] == "GET" for call in self.server.calls))
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=3)
            os.close(master)

    def test_delay_lookup_retains_mapping_context_and_unicode(self):
        for name, expected in [("DIRECT", "42"), (HK, "135"), ("missing", "999999")]:
            with self.subTest(name=name):
                result = self.run_function('delay_for_node "$1" "$2"',
                                           json.dumps(self.server.group_body, ensure_ascii=False), name)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), expected)

    def test_zero_delay_is_a_timeout_not_unmeasured(self):
        result = self.run_function('delay_for_node \'{"DIRECT":0}\' DIRECT')
        self.assertEqual(result.stdout.strip(), "999999")

    def test_group_request_encodes_names_and_test_url(self):
        result = self.run_cli("--test-url", "https://example.com/check?a=1&b=2", "test")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [call for call in self.server.calls if call["path"].startswith("/group/")]
        self.assertEqual(calls[0]["path"], "/group/{}/delay".format(GROUP))
        self.assertEqual(calls[0]["query"]["url"], ["https://example.com/check?a=1&b=2"])
        self.assertEqual(calls[0]["query"]["timeout"], ["2500"])

    def test_noninteractive_test_displays_real_delays_and_only_missing_node_times_out(self):
        result = self.run_cli("test")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("42 ms", result.stdout)
        self.assertIn("135 ms", result.stdout)
        self.assertEqual(result.stdout.count("Timeout"), 1)

    def test_batch_tui_displays_real_delays_instead_of_all_timeouts(self):
        frame = self.run_tui_key(b"t", "批量测速完成")
        self.assertRegex(frame, r"DIRECT[^\n]*42 ms")
        self.assertRegex(frame, re.escape(HK) + r"[^\n]*135 ms")
        self.assertRegex(frame, r"故障节点[^\n]*Timeout")
        self.assertEqual(frame.count("Timeout"), 1)

    def test_empty_successful_group_map_can_represent_real_timeouts(self):
        self.server.group_body = {}
        frame = self.run_tui_key(b"t", "批量测速完成")
        self.assertEqual(frame.count("Timeout"), 3)

    def test_group_http_error_is_not_reported_as_node_timeouts(self):
        self.server.group_status = 503
        self.server.group_body = {"message": "TLS handshake failed: x509 certificate error"}
        result = self.run_cli("test")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("HTTP 503", result.stderr)
        self.assertIn("TLS handshake failed", result.stderr)
        self.assertNotIn("Timeout", result.stdout)

    def test_failed_batch_tui_preserves_previous_delays_and_shows_tls_error(self):
        self.server.group_status = 503
        self.server.group_body = {"message": "TLS handshake failed"}
        frame = self.run_tui_key(b"t", "批量测速失败")
        self.assertIn("TLS handshake failed", frame)
        self.assertRegex(frame, r"DIRECT[^\n]*21 ms")
        self.assertRegex(frame, re.escape(HK) + r"[^\n]*72 ms")
        self.assertNotIn("Timeout", frame)

    def test_malformed_batch_tui_preserves_previous_delays(self):
        self.server.group_body = b"<html>unavailable</html>"
        frame = self.run_tui_key(b"t", "批量测速失败")
        self.assertIn("不是有效的节点延迟映射", frame)
        self.assertRegex(frame, r"DIRECT[^\n]*21 ms")
        self.assertNotIn("Timeout", frame)

    def test_invalid_json_or_non_numeric_maps_fail_without_false_timeouts(self):
        for body in [b"invalid json", [], None, {"message": "unexpected API error"}, {"DIRECT": "42"}]:
            with self.subTest(body=body):
                self.server.group_body = body
                result = self.run_cli("test")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("不是有效的节点延迟映射", result.stderr)
                self.assertNotIn("Timeout", result.stdout)

    def test_single_tui_test_displays_valid_delay(self):
        frame = self.run_tui_key(b"p", "延迟: 17 ms")
        self.assertRegex(frame, r"DIRECT[^\n]*17 ms")

    def test_single_tui_http_error_preserves_previous_delay(self):
        self.server.single_status = 504
        self.server.single_body = {"message": "SSL handshake failed"}
        frame = self.run_tui_key(b"p", "测速失败")
        self.assertIn("HTTP 504", frame)
        self.assertIn("SSL handshake failed", frame)
        self.assertRegex(frame, r"DIRECT[^\n]*21 ms")
        self.assertNotIn("Timeout", frame)

    def test_single_response_requires_numeric_delay(self):
        self.server.single_body = {"message": "no delay"}
        result = self.run_function('test_single_delay DIRECT')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("没有有效的 delay", result.stderr)

    def test_curl_handshake_and_certificate_errors_remain_visible(self):
        for code in [35, 60]:
            with self.subTest(code=code):
                script = ('api_req() { printf "curl: SSL certificate handshake failed\\n" >&2; '
                          'printf "\\n000"; return ' + str(code) + '; }; test_single_delay DIRECT')
                result = self.run_function(script)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("curl {}".format(code), result.stderr)
                self.assertIn("SSL certificate handshake failed", result.stderr)
                self.assertNotIn("Timeout", result.stdout)

    def test_request_budget_exceeds_configured_backend_timeout(self):
        result = self.run_function(
            'TIMEOUT_MS=10000; api_req() { '
            '[[ "$*" == *"-m 13"* ]] || return 99; '
            'printf \'{"DIRECT":42}\\n200\'; }; test_group_delay "$1"', GROUP)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"DIRECT": 42})

    def test_loopback_controller_bypasses_broken_proxy_environment(self):
        env = dict(self.env)
        env.update({"http_proxy": "http://127.0.0.1:1", "all_proxy": "http://127.0.0.1:1",
                    "HTTP_PROXY": "http://127.0.0.1:1", "ALL_PROXY": "http://127.0.0.1:1",
                    "NO_PROXY": "", "no_proxy": ""})
        result = self.run_cli("test", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("42 ms", result.stdout)

    def test_secret_header_is_preserved(self):
        env = dict(self.env, MIHOMO_SECRET="test-secret")
        result = self.run_cli("test", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(all(call["authorization"] == "Bearer test-secret" for call in self.server.calls))

    def test_invalid_timeout_or_url_is_rejected_before_delay_request(self):
        for args in [("--timeout", "0"), ("--timeout", "abc"), ("--test-url", "file:///etc/passwd")]:
            with self.subTest(args=args):
                self.server.calls.clear()
                result = self.run_cli(*args, "test")
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(any(call["path"].startswith("/group/") for call in self.server.calls))

    def test_options_require_values(self):
        for flag in ["--timeout", "--test-url"]:
            with self.subTest(flag=flag):
                result = self.run_cli(flag)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("缺少", result.stderr)


if __name__ == "__main__":
    unittest.main()

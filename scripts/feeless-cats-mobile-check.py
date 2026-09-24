#!/usr/bin/env python3
"""Real-browser mobile smoke check for the Feeless Cats collection.

The check intentionally uses Chromium's DevTools Protocol directly so it does
not add a browser-driver dependency to the frontend. It expects the preview to
be serving on PREVIEW_URL, or can be run by
scripts/run-feeless-cats-mobile-check.sh, which starts the preview first.
"""

import base64
import json
import os
import socket
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid


PREVIEW_URL = os.environ.get("PREVIEW_URL", "http://127.0.0.1:5000").rstrip("/")
CDP_PORT = int(os.environ.get("CDP_PORT", "9223"))
CHROMIUM = os.environ.get("CHROMIUM_BIN", "/repl/tools/bin/chromium")
VIEWPORTS = (320, 390)
FILTER_COUNTS = {"all": 25, "spots": 9, "patch": 8, "stripes": 8}


class DevTools:
    def __init__(self, websocket_url):
        parsed = websocket_url.removeprefix("ws://").split("/", 1)
        host, path = parsed
        hostname, port = host.rsplit(":", 1)
        self.socket = socket.create_connection((hostname, int(port)), timeout=10)
        key = base64.b64encode(os.urandom(16)).decode()
        self.socket.sendall(
            (
                f"GET /{path} HTTP/1.1\r\n"
                f"Host: {host}\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                "Sec-WebSocket-Version: 13\r\n\r\n"
            ).encode()
        )
        response = self.socket.recv(4096)
        if b" 101 " not in response:
            raise RuntimeError(f"DevTools websocket handshake failed: {response!r}")
        self.next_id = 0
        self.console_errors = []
        self.navigation_events = []
        self.navigation_failures = []

    def close(self):
        self.socket.close()

    def _send_frame(self, payload):
        payload = payload.encode()
        length = len(payload)
        header = bytearray([0x81])
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        mask = os.urandom(4)
        header.extend(mask)
        header.extend(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self.socket.sendall(header)

    def _receive_frame(self):
        header = self.socket.recv(2)
        if len(header) != 2:
            raise RuntimeError("DevTools websocket closed")
        first, second = header
        opcode = first & 0x0F
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", self.socket.recv(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self.socket.recv(8))[0]
        masked = second & 0x80
        mask = self.socket.recv(4) if masked else None
        payload = bytearray()
        while len(payload) < length:
            chunk = self.socket.recv(length - len(payload))
            if not chunk:
                raise RuntimeError("DevTools websocket closed while reading")
            payload.extend(chunk)
        if mask:
            payload = bytearray(value ^ mask[index % 4] for index, value in enumerate(payload))
        return opcode, bytes(payload)

    def _record_event(self, message):
        method = message.get("method")
        params = message.get("params", {})
        if method == "Runtime.consoleAPICalled" and params.get("type") in {
            "error",
            "assert",
        }:
            values = []
            for argument in params.get("args", []):
                values.append(
                    argument.get("value")
                    or argument.get("description")
                    or argument.get("unserializableValue")
                    or argument.get("type", "unknown")
                )
            self.console_errors.append(" ".join(str(value) for value in values))
        elif method == "Runtime.exceptionThrown":
            details = params.get("exceptionDetails", {})
            text = details.get("text") or details.get("exception", {}).get("description")
            if text:
                self.console_errors.append(f"uncaught exception: {text}")
        elif method == "Page.frameNavigated":
            frame = params.get("frame", {})
            if frame.get("parentId") is None:
                self.navigation_events.append(frame.get("url", ""))

    def command(self, method, params=None):
        self.next_id += 1
        command_id = self.next_id
        self._send_frame(
            json.dumps({"id": command_id, "method": method, "params": params or {}})
        )
        while True:
            opcode, payload = self._receive_frame()
            if opcode == 0x9:
                continue
            if opcode != 0x1:
                continue
            message = json.loads(payload.decode())
            if "method" in message:
                self._record_event(message)
            if message.get("id") == command_id:
                if "error" in message:
                    raise RuntimeError(f"{method} failed: {message['error']}")
                return message.get("result", {})

    def evaluate(self, expression):
        result = self.command(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
        )
        remote = result.get("result", {})
        if remote.get("type") == "object" and "value" not in remote:
            return None
        return remote.get("value")


def browser_target():
    with urllib.request.urlopen(
        f"http://127.0.0.1:{CDP_PORT}/json/list", timeout=10
    ) as response:
        targets = json.load(response)
    pages = [target for target in targets if target.get("type") == "page"]
    if not pages:
        raise RuntimeError("Chromium DevTools has no page target")
    return pages[0]["webSocketDebuggerUrl"]


def connect_target(timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            target = DevTools(browser_target())
            target.command("Page.enable")
            target.command("Runtime.enable")
            return target
        except (OSError, urllib.error.URLError, RuntimeError):
            time.sleep(0.2)
    raise RuntimeError("Chromium page target did not become available")


def wait_for(devtools, expression, description, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if devtools.evaluate(expression):
            return
        time.sleep(0.15)
    raise AssertionError(f"Timed out waiting for {description}: {expression}")


def assert_state(actual, expected, description):
    if actual != expected:
        raise AssertionError(f"{description}: expected {expected!r}, got {actual!r}")


def navigate(devtools, path):
    destination = f"{PREVIEW_URL}{path}"
    result = devtools.command("Page.navigate", {"url": destination})
    if result.get("errorText"):
        devtools.navigation_failures.append(
            f"{path}: Page.navigate returned {result['errorText']}"
        )
        raise AssertionError(devtools.navigation_failures[-1])
    try:
        wait_for(
            devtools,
            f"location.pathname === {json.dumps(path)}",
            f"navigation to {path}",
        )
    except AssertionError as error:
        current = devtools.evaluate("location.href")
        failure = f"{path}: landed at {current!r} ({error})"
        devtools.navigation_failures.append(failure)
        raise AssertionError(failure) from error


def click(devtools, selector, description):
    clicked = devtools.evaluate(
        f"""(() => {{
            const element = document.querySelector({json.dumps(selector)});
            if (!element) return false;
            element.click();
            return true;
        }})()"""
    )
    if not clicked:
        raise AssertionError(f"{description}: selector not found: {selector}")


def run_viewport(devtools, width):
    devtools.command(
        "Emulation.setDeviceMetricsOverride",
        {
            "width": width,
            "height": 900,
            "deviceScaleFactor": 1,
            "mobile": True,
        },
    )

    # Start from the terminal root so the real mobile menu and collapsed
    # FeeCat submenu are both exercised before entering the collection.
    navigate(devtools, "/terminal")
    wait_for(devtools, "!!document.querySelector('[data-testid=\"terminal-menu-toggle\"]')", "mobile terminal menu")
    assert_state(
        devtools.evaluate("!!document.querySelector('[data-testid=\"feecat-subnav\"]')"),
        False,
        f"FeeCat submenu starts collapsed at {width}px",
    )
    click(devtools, '[data-testid="terminal-menu-toggle"]', "open mobile sidebar")
    wait_for(
        devtools,
        "document.querySelector('[data-testid=\"terminal-sidebar\"]')?.classList.contains('sidebar-open')",
        "mobile sidebar to open",
    )
    click(devtools, '[data-testid="nav-feecat-toggle"]', "expand FeeCat submenu")
    wait_for(devtools, "!!document.querySelector('[data-testid=\"feecat-subnav\"]')", "FeeCat submenu to expand")
    click(devtools, '[data-testid="nav-feeless-cats"]', "open Feeless Cats")
    try:
        wait_for(devtools, "location.pathname === '/terminal/feecat/cats'", "Feeless Cats navigation")
        wait_for(devtools, "!!document.querySelector('[data-testid=\"feecats-filter-all\"]')", "Feeless Cats page")
    except AssertionError as error:
        current = devtools.evaluate("location.href")
        failure = f"Feeless Cats link at {width}px: landed at {current!r} ({error})"
        devtools.navigation_failures.append(failure)
        raise AssertionError(failure) from error

    overflow = devtools.evaluate(
        """(() => ({
            viewport: window.innerWidth,
            documentWidth: document.documentElement.scrollWidth,
            bodyWidth: document.body.scrollWidth,
            horizontalOverflow: Math.max(
                document.documentElement.scrollWidth,
                document.body.scrollWidth
            ) > window.innerWidth
        }))()"""
    )
    assert_state(
        overflow["horizontalOverflow"],
        False,
        f"horizontal overflow at {width}px ({overflow})",
    )

    for filter_id, expected_count in FILTER_COUNTS.items():
        click(
            devtools,
            f'[data-testid="feecats-filter-{filter_id}"]',
            f"select {filter_id} fur filter",
        )
        wait_for(
            devtools,
            f"""(() => {{
                const button = document.querySelector('[data-testid="feecats-filter-{filter_id}"]');
                return button?.getAttribute('aria-pressed') === 'true'
                    && document.querySelectorAll('.cat-card').length === {expected_count};
            }})()""",
            f"{filter_id} filter result",
        )

    # Return to All before selecting a named card. This keeps the check
    # deterministic when a fixture is intentionally absent from a filter.
    click(devtools, '[data-testid="feecats-filter-all"]', "reset to All fur filter")
    wait_for(
        devtools,
        "document.querySelectorAll('.cat-card').length === 25",
        "all cats after resetting filter",
    )
    click(devtools, '[data-testid="feecat-card-midnight-patch"]', "select Midnight Patch")
    wait_for(
        devtools,
        """document.querySelector('.cat-preview-panel h2')?.textContent === 'Midnight Patch'
            && document.querySelector('[role="status"]')?.textContent.includes('Midnight Patch selected')""",
        "selected card preview",
    )
    click(devtools, '[data-testid="feecats-select"]', "set featured cat")
    wait_for(
        devtools,
        "document.querySelector('[role=\"status\"]')?.textContent.includes('Midnight Patch is your featured cat')",
        "featured cat confirmation",
    )
    click(devtools, '[data-testid="feecats-random"]', "use Surprise me")
    wait_for(
        devtools,
        """(() => {
            const name = document.querySelector('.cat-preview-panel h2')?.textContent;
            const status = document.querySelector('[role="status"]')?.textContent || '';
            return !!name && name !== 'Midnight Patch' && status.includes('selected');
        })()""",
        "Surprise me to choose a different cat",
    )

    return overflow


def main():
    browser = subprocess.Popen(
        [
            CHROMIUM,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            f"--remote-debugging-port={CDP_PORT}",
            "--remote-debugging-address=127.0.0.1",
            f"--user-data-dir=/tmp/feeless-cats-mobile-{uuid.uuid4().hex}",
            f"{PREVIEW_URL}/terminal",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    devtools = None
    results = []
    try:
        devtools = connect_target(timeout=15)
        for width in VIEWPORTS:
            results.append(run_viewport(devtools, width))
        if devtools.console_errors:
            details = "\n".join(f"  - {error}" for error in devtools.console_errors)
            raise AssertionError(f"browser console errors:\n{details}")
        if devtools.navigation_failures:
            details = "\n".join(f"  - {failure}" for failure in devtools.navigation_failures)
            raise AssertionError(f"navigation failures:\n{details}")
        print(
            "PASS Feeless Cats mobile browser check: "
            + ", ".join(
                f"{result['viewport']}px (document {result['documentWidth']}px, body {result['bodyWidth']}px)"
                for result in results
            )
        )
    except Exception as error:
        print(f"FAIL Feeless Cats mobile browser check: {error}", file=sys.stderr)
        if devtools:
            if devtools.console_errors:
                print("Browser console errors observed:", file=sys.stderr)
                for detail in devtools.console_errors:
                    print(f"  - {detail}", file=sys.stderr)
            if devtools.navigation_failures:
                print("Navigation failures observed:", file=sys.stderr)
                for detail in devtools.navigation_failures:
                    print(f"  - {detail}", file=sys.stderr)
        raise
    finally:
        if devtools:
            devtools.close()
        browser.terminate()
        try:
            browser.wait(timeout=5)
        except subprocess.TimeoutExpired:
            browser.kill()


if __name__ == "__main__":
    main()
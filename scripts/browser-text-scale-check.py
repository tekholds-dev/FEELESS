#!/usr/bin/env python3
"""Browser smoke test for terminal text-scale recovery.

Uses Chromium's built-in DevTools Protocol so the check needs no npm or Python
browser-driver dependency. Run with the preview workflow already serving the
frontend:

  python scripts/browser-text-scale-check.py
"""

import base64
import hashlib
import json
import os
import socket
import struct
import subprocess
import sys
import time
import urllib.request
import uuid


PREVIEW_URL = os.environ.get("PREVIEW_URL", "http://127.0.0.1:5000")
CDP_PORT = int(os.environ.get("CDP_PORT", "9222"))
CHROMIUM = os.environ.get("CHROMIUM_BIN", "/repl/tools/bin/chromium")


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

    def command(self, method, params=None):
        self.next_id += 1
        command_id = self.next_id
        self._send_frame(json.dumps({"id": command_id, "method": method, "params": params or {}}))
        while True:
            opcode, payload = self._receive_frame()
            if opcode == 0x9:
                continue
            if opcode != 0x1:
                continue
            message = json.loads(payload.decode())
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


def wait_for(devtools, expression, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if devtools.evaluate(expression):
            return
        time.sleep(0.25)
    raise AssertionError(f"Timed out waiting for: {expression}")


def browser_target():
    with urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json/new?{PREVIEW_URL}/terminal/settings", timeout=10) as response:
        target = json.load(response)
    return target["webSocketDebuggerUrl"]


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
            f"--user-data-dir=/tmp/feeless-text-scale-{uuid.uuid4().hex}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    devtools = None
    try:
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                devtools = DevTools(browser_target())
                break
            except (OSError, urllib.error.URLError):
                time.sleep(0.2)
        if devtools is None:
            raise RuntimeError("Chromium DevTools endpoint did not start")

        devtools.command("Page.enable")
        devtools.command("Runtime.enable")
        wait_for(devtools, "location.pathname === '/terminal/settings'")
        wait_for(devtools, "document.querySelector('[data-testid=\"config-text-size\"]')")

        malformed = json.dumps(
            {
                "compact": "compact",
                "autoRefresh": "yes",
                "reducedMotion": 1,
                "fontScale": "huge",
                "chartInterval": "10m",
                "defaultEcosystem": "invalid",
            },
            separators=(",", ":"),
        )
        devtools.evaluate(f"localStorage.setItem('feeless-settings', {json.dumps(malformed)})")
        devtools.command("Page.reload", {"ignoreCache": True})
        wait_for(devtools, "document.querySelector('[data-testid=\"config-text-size\"]')")

        settings_state = devtools.evaluate(
            """(() => ({
                path: location.pathname,
                select: document.querySelector('[data-testid="config-text-size"]')?.value,
                stored: JSON.parse(localStorage.getItem('feeless-settings') || '{}')
            }))()"""
        )
        assert settings_state["path"] == "/terminal/settings", settings_state
        assert settings_state["select"] == "normal", settings_state
        assert settings_state["stored"]["fontScale"] == "normal", settings_state

        clicked = devtools.evaluate(
            """(() => {
                const link = document.querySelector('[data-testid="nav-trade"]');
                if (!link) return false;
                link.click();
                return true;
            })()"""
        )
        assert clicked, "Trade navigation link was not rendered"
        wait_for(devtools, "location.pathname === '/terminal/trade'")
        wait_for(devtools, "document.querySelector('[data-testid=\"swap-amount\"]')")

        trade_state = devtools.evaluate(
            """(() => {
                const app = document.querySelector('.terminal-app');
                const amount = document.querySelector('[data-testid="swap-amount"]');
                const output = document.querySelector('[data-testid="swap-output"]');
                return {
                    path: location.pathname,
                    normalClass: app?.classList.contains('text-scale-normal'),
                    amountVisible: !!amount && getComputedStyle(amount).fontSize !== '0px',
                    outputVisible: !!output && getComputedStyle(output).fontSize !== '0px'
                };
            })()"""
        )
        assert trade_state["path"] == "/terminal/trade", trade_state
        assert trade_state["normalClass"], trade_state
        assert trade_state["amountVisible"], trade_state
        assert trade_state["outputVisible"], trade_state

        devtools.command("Page.reload", {"ignoreCache": True})
        wait_for(devtools, "location.pathname === '/terminal/trade'")
        wait_for(devtools, "document.querySelector('[data-testid=\"swap-amount\"]')")
        reloaded_state = devtools.evaluate(
            """(() => ({
                path: location.pathname,
                normalClass: document.querySelector('.terminal-app')?.classList.contains('text-scale-normal'),
                stored: JSON.parse(localStorage.getItem('feeless-settings') || '{}'),
                amountVisible: getComputedStyle(document.querySelector('[data-testid="swap-amount"]')).fontSize !== '0px'
            }))()"""
        )
        assert reloaded_state["normalClass"], reloaded_state
        assert reloaded_state["stored"]["fontScale"] == "normal", reloaded_state
        assert reloaded_state["amountVisible"], reloaded_state
        print("PASS browser text-scale recovery: settings → trade → reload")
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
"""🪟 NEXA CONTROLLER — runs on the Windows PC beside llamafile (owner, 2026-10-21: "the Model Rig's NEXA settings must actually control the
Windows runtime, without me going to that PC"). Python stdlib only; one file.

FIXED PURPOSE. Over HTTP it accepts exactly two things, both behind a shared-secret Bearer token:
  POST /apply   {"ctx": 2048, "parallel": 1}   → restart THE configured llamafile with those numbers, verify through /props + /slots
  POST /restart {}                             → restart it with the last applied numbers (when NEXA hangs)
  GET  /state                                  → what is running (per-slot context, slot count, model) + the last apply
  GET  /health                                 → {"ok": true} (no token; says nothing else)
ctx / parallel must be in the allowlist below (the Model Rig's own options). The executable, the model, the host and the port come ONLY from
nexa_ctl.json beside this file (written once at setup, on this PC) — no path, command, flag or shell text is ever read from a request.
The command is built here, as an argument list (no shell). Only processes whose image name is the configured executable's are stopped.
On start, if llamafile is not running and an apply was saved, it starts llamafile with those numbers (comes back after a reboot / outage).

Config (nexa_ctl.json): {"token": "...", "exe": "C:\\nexa\\llamafile.exe", "model": "C:\\nexa\\Qwen2.5-1.5B-Instruct-Q4_K_M.gguf",
                         "host": "0.0.0.0", "port": 8080, "ctlPort": 8081}
"""
import hmac
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CTX_OK = (2048, 4096, 8192, 12288, 16384, 32768)      # per-slot context (Model Rig options, minus 0 = "auto")
PAR_OK = (1, 2, 3, 4)
TOTAL_MAX = 32768                                     # ctx × slots — llamafile allocates all of it up front
BOOT_SEC = 240                                        # a 1.5B model on an old CPU loads in well under this
HERE = Path(__file__).resolve().parent
CONF = HERE / 'nexa_ctl.json'
STATE = HERE / 'nexa_state.json'
LOG = HERE / 'llamafile.log'


def validate(body):
    """→ (ctx, parallel) or raises ValueError. Only ints from the allowlists; nothing else in the body is read."""
    if not isinstance(body, dict):
        raise ValueError('body must be a JSON object')
    try:
        ctx, par = int(body.get('ctx')), int(body.get('parallel'))
    except (TypeError, ValueError):
        raise ValueError('ctx and parallel must be whole numbers')
    if ctx not in CTX_OK:
        raise ValueError(f'ctx must be one of {list(CTX_OK)}')
    if par not in PAR_OK:
        raise ValueError(f'parallel must be one of {list(PAR_OK)}')
    if ctx * par > TOTAL_MAX:
        raise ValueError(f'ctx × parallel must be ≤ {TOTAL_MAX}')
    return ctx, par


def command(conf, ctx, par):
    """The ONE command this controller runs — an argument list built from the local config + validated numbers."""
    return [str(conf['exe']), '--server', '--host', str(conf.get('host') or '0.0.0.0'), '--port', str(int(conf.get('port') or 8080)),
            '-m', str(conf['model']), '-c', str(ctx * par), '-np', str(par)]


def parse_actual(props, slots):
    """llamafile /props + /slots → {ctx (per slot), slots, model} (None fields when unreadable)."""
    props = props if isinstance(props, dict) else {}
    g = props.get('default_generation_settings') or {}
    n_slots = len(slots) if isinstance(slots, list) else props.get('total_slots')
    ctx = g.get('n_ctx')
    if ctx is None and isinstance(slots, list) and slots:
        ctx = (slots[0] or {}).get('n_ctx')
    model = os.path.basename(str(props.get('model_path') or '')) or None
    return {'ctx': int(ctx) if ctx else None, 'slots': int(n_slots) if n_slots else None, 'model': model}


def matches(actual, ctx, par):
    return bool(actual) and actual.get('ctx') == ctx and actual.get('slots') == par


def authed(header, token):
    return bool(token) and hmac.compare_digest((header or '').encode(), f'Bearer {token}'.encode())


class Runtime:
    """Process side, kept apart so tests can swap it (spawn / kill / fetch)."""
    def __init__(self, conf):
        self.conf = conf
        self.lock = threading.Lock()

    def image(self):
        return os.path.basename(str(self.conf['exe']))

    def kill(self):
        if os.name == 'nt':
            subprocess.run(['taskkill', '/F', '/IM', self.image()], capture_output=True)
        else:
            subprocess.run(['pkill', '-f', str(self.conf['exe'])], capture_output=True)

    def spawn(self, ctx, par):
        log = open(LOG, 'ab')
        kw = {'stdout': log, 'stderr': subprocess.STDOUT, 'stdin': subprocess.DEVNULL, 'cwd': str(Path(self.conf['model']).parent)}
        if os.name == 'nt':
            kw['creationflags'] = 0x00000008 | 0x00000200          # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        return subprocess.Popen(command(self.conf, ctx, par), **kw)

    def fetch(self, path, timeout=4):
        url = f"http://127.0.0.1:{int(self.conf.get('port') or 8080)}{path}"
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode() or 'null')

    def actual(self):
        try:
            return parse_actual(self.fetch('/props'), self.fetch('/slots'))
        except Exception:
            return None

    def wait_down(self, secs=20, step=1.0, sleep=time.sleep, clock=time.time):
        """True once nothing answers on the llamafile port (the old process is really gone)."""
        end = clock() + secs
        while clock() < end:
            if self.actual() is None:
                return True
            sleep(step)
        return self.actual() is None

    def wait_ready(self, ctx, par, boot=BOOT_SEC, step=2.0, sleep=time.sleep, clock=time.time, settle=20):
        """Poll /props + /slots until the runtime reports (ctx, par); a runtime that answers with other numbers is re-read for `settle` s."""
        end = clock() + boot
        seen_at = None
        last = None
        while clock() < end:
            last = self.actual()
            if matches(last, ctx, par):
                return last
            if last and last.get('slots'):
                seen_at = seen_at or clock()
                if clock() - seen_at >= settle:
                    return last
            sleep(step)
        return last


def load_state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def save_state(st):
    STATE.write_text(json.dumps(st))


def apply(rt, ctx, par, sleep=time.sleep, clock=time.time):
    """Restart llamafile with (ctx, par) and verify it. → {ok, verified, wanted, actual, msg}"""
    if not rt.lock.acquire(blocking=False):
        return {'ok': False, 'verified': False, 'msg': 'an apply is already running'}
    try:
        rt.kill()
        if not rt.wait_down(sleep=sleep, clock=clock):
            res = {'ok': False, 'verified': False, 'wanted': {'ctx': ctx, 'slots': par}, 'actual': rt.actual(), 'at': clock(),
                   'msg': 'could not stop the running llamafile — nothing was changed'}
            return res
        rt.spawn(ctx, par)
        got = rt.wait_ready(ctx, par, sleep=sleep, clock=clock)
        ok = matches(got, ctx, par)
        res = {'ok': ok, 'verified': ok, 'wanted': {'ctx': ctx, 'slots': par}, 'actual': got, 'at': clock(),
               'msg': 'running and verified' if ok else ('llamafile did not come up' if not got else 'running, but /props · /slots differ from what was asked')}
        save_state({'ctx': ctx, 'parallel': par, 'last': res})
        return res
    finally:
        rt.lock.release()


def make_handler(rt, token):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, obj):
            body = json.dumps(obj).encode()
            self.send_response(code); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(body))); self.end_headers()
            self.wfile.write(body)

        def _ok(self):
            if authed(self.headers.get('Authorization'), token):
                return True
            self._send(401, {'error': 'missing or wrong token'})
            return False

        def do_GET(self):
            p = self.path.split('?')[0].rstrip('/')
            if p == '/health':
                return self._send(200, {'ok': True})
            if not self._ok():
                return
            if p == '/state':
                return self._send(200, {'actual': rt.actual(), 'saved': load_state(), 'allow': {'ctx': CTX_OK, 'parallel': PAR_OK}})
            self._send(404, {'error': 'unknown'})

        def do_POST(self):
            p = self.path.split('?')[0].rstrip('/')
            if not self._ok():
                return
            n = min(int(self.headers.get('Content-Length') or 0), 4096)
            try:
                body = json.loads(self.rfile.read(n).decode() or '{}')
            except Exception:
                return self._send(400, {'error': 'body must be JSON'})
            if p == '/apply':
                try:
                    ctx, par = validate(body)
                except ValueError as e:
                    return self._send(400, {'error': str(e)})
            elif p == '/restart':
                st = load_state()
                try:
                    ctx, par = validate({'ctx': st.get('ctx'), 'parallel': st.get('parallel')})
                except ValueError:
                    return self._send(409, {'error': 'nothing applied yet — apply settings first'})
            else:
                return self._send(404, {'error': 'unknown'})
            res = apply(rt, ctx, par)
            self._send(200 if res.get('ok') else (409 if 'already' in res.get('msg', '') else 502), res)
    return H


def main():
    conf = json.loads(CONF.read_text())
    for k in ('token', 'exe', 'model'):
        if not conf.get(k):
            sys.exit(f'nexa_ctl.json needs "{k}"')
    rt = Runtime(conf)
    st = load_state()
    if rt.actual() is None and st.get('ctx'):
        try:   # back after a reboot / outage: start llamafile with the last applied numbers
            ctx, par = validate({'ctx': st['ctx'], 'parallel': st['parallel']})
            rt.spawn(ctx, par)
        except ValueError:
            pass
    srv = ThreadingHTTPServer(('0.0.0.0', int(conf.get('ctlPort') or 8081)), make_handler(rt, conf['token']))
    print(f"NEXA controller on :{int(conf.get('ctlPort') or 8081)} — managing {rt.image()}", flush=True)
    srv.serve_forever()


if __name__ == '__main__':
    main()

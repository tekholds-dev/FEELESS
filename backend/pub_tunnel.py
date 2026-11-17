"""🔗 Public https links for a swap's two reference files, with no setup (owner 2026-11-17: OpenRouter answered
"Only HTTPS URLs are allowed" to a clip sent inside the request).

When a swap needs them, a tiny file server starts on 127.0.0.1 that answers ONLY `/<cat>/pub/<32-char token>.mp4|jpg` younger than
2 hours (no listing, nothing else on this machine), and a Cloudflare quick tunnel (`cloudflared`, already on the owner's Mac) gives
it a random https://….trycloudflare.com address. The tunnel closes itself after 2 hours without a swap.
PUBLIC_SITE_URL, when set, is used instead (fc_desk._public_site)."""
import asyncio
import re
import shutil
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LIVE_S = 2 * 3600                                  # a reference link lives 2 hours
NAME = re.compile(r'^/([A-Za-z0-9_-]{1,64})/pub/([A-Za-z0-9_-]{32}\.(mp4|jpg))$')
URL = re.compile(r'https://[a-z0-9-]+\.trycloudflare\.com')
_st = {'srv': None, 'port': 0, 'root': None, 'proc': None, 'url': '', 'used': 0.0, 'lock': None}


def url_in(line):
    """The quick tunnel's address in one line of cloudflared's log, or ''."""
    m = URL.search(str(line or '')); return m.group(0) if m else ''


def connected(line):
    """True when cloudflared's log line says the tunnel reached Cloudflare's edge (it answers from the internet from then on)."""
    return 'Registered tunnel connection' in str(line or '')


def file_for(root, path):
    """The file a request path may get: a token-named reference under <root>/<cat>/pub, younger than 2 hours. Else None."""
    m = NAME.match(str(path or '').split('?', 1)[0])
    if not m:
        return None
    f = Path(root) / m.group(1) / 'pub' / m.group(2)
    try:
        return f if f.is_file() and time.time() - f.stat().st_mtime <= LIVE_S else None
    except OSError:
        return None


class _H(BaseHTTPRequestHandler):
    def _send(self, head_only):
        if self.path == '/ok':
            self.send_response(200); self.send_header('Content-Length', '2'); self.end_headers()
            if not head_only:
                self.wfile.write(b'ok')
            return
        f = file_for(_st['root'], self.path)
        if not f:
            self.send_response(404); self.send_header('Content-Length', '0'); self.end_headers(); return
        data = f.read_bytes()
        self.send_response(200); self.send_header('Content-Type', 'video/mp4' if f.suffix == '.mp4' else 'image/jpeg')
        self.send_header('Content-Length', str(len(data))); self.send_header('Cache-Control', 'no-store'); self.end_headers()
        if not head_only:
            self.wfile.write(data)

    def do_GET(self):   # noqa: N802
        self._send(False)

    def do_HEAD(self):   # noqa: N802
        self._send(True)

    def log_message(self, *_a):
        pass


def serve(root):
    """Start (once) the local file server for `root`; → its port."""
    _st['root'] = str(root)
    if not _st['srv']:
        srv = ThreadingHTTPServer(('127.0.0.1', 0), _H); srv.daemon_threads = True
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        _st['srv'], _st['port'] = srv, srv.server_address[1]
    return _st['port']


def stop():
    p = _st['proc']; _st['proc'], _st['url'] = None, ''
    if p and p.returncode is None:
        try:
            p.terminate()
        except ProcessLookupError:
            pass


async def _idle_close():
    while _st['proc'] is not None:
        await asyncio.sleep(300)
        if time.time() - _st['used'] > LIVE_S + 300:
            stop()


async def ensure(root, start_s=45):
    """→ the tunnel's https address (starting the server and the tunnel if needed). ValueError when it cannot open."""
    _st['used'] = time.time()
    _st['lock'] = _st['lock'] or asyncio.Lock()
    async with _st['lock']:
        port = serve(root)
        p = _st['proc']
        if p and p.returncode is None and _st['url']:
            return _st['url']
        exe = shutil.which('cloudflared') or ('/opt/homebrew/bin/cloudflared' if Path('/opt/homebrew/bin/cloudflared').is_file() else '')
        if not exe:
            raise ValueError('OpenRouter needs a public https link to your clip. Install cloudflared (brew install cloudflared), or set PUBLIC_SITE_URL to your https tunnel')
        # --config /dev/null: the owner's old ~/.cloudflared/config.yml 404s a bare quick tunnel; 127.0.0.1, not localhost (that dials ::1)
        p = await asyncio.create_subprocess_exec(exe, 'tunnel', '--config', '/dev/null', '--no-autoupdate', '--url', f'http://127.0.0.1:{port}',
                                                 stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        # ready = its address is known AND it reached Cloudflare's edge. No test fetch from this Mac: a brand-new trycloudflare name
        # often fails here first, and macOS then remembers that "not found" for a while although the internet already reaches it.
        url, up, end = '', False, time.time() + start_s
        while not (url and up) and time.time() < end:
            try:
                line = await asyncio.wait_for(p.stderr.readline(), max(0.1, end - time.time()))
            except asyncio.TimeoutError:
                break
            if not line:
                break
            s = line.decode('utf-8', 'replace'); url = url or url_in(s); up = up or connected(s)
        if not (url and up):
            p.terminate(); raise ValueError('the private link for your clip did not open (Cloudflare). Try again in a minute')

        async def _drain():   # keep reading its log so the pipe never fills and stalls it
            while await p.stderr.readline():
                pass
        asyncio.create_task(_drain())
        _st['proc'], _st['url'] = p, url
        await asyncio.sleep(3)   # its DNS name settles at the edge
        asyncio.create_task(_idle_close())
        return url


def warm(root):
    """Open the link ahead of a swap (the swap panel opened), so the swap itself does not wait. Errors wait for the swap to say them."""
    async def _go():
        try:
            await ensure(root)
        except Exception:   # noqa: BLE001 — the swap reports it with the words the owner sees
            pass
    asyncio.get_running_loop().create_task(_go())

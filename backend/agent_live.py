"""🔴 GO LIVE AS YOUR CHARACTER (owner 2026-11-04): the owner's browser sends the character's picture and voice, never the camera, and ffmpeg passes it to their own channel with their own key.
Pure parts are tested; `Relay` runs one ffmpeg per stream. Only hosts the platforms publish are reachable, so a typed address can never send a stream, or a key, anywhere else."""
import asyncio
import re
from urllib.parse import urlsplit

PLATFORMS = {
    'twitch': {'label': 'Twitch', 'hosts': ('live.twitch.tv', 'contribute.live-video.net', 'global-contribute.live-video.net'), 'schemes': ('rtmps',), 'server': 'rtmps://live.twitch.tv/app'},
    'kick': {'label': 'Kick', 'hosts': ('contribute.live-video.net', 'global-contribute.live-video.net'), 'schemes': ('rtmps',), 'server': ''},   # Kick shows each channel its own address
    'tiktok': {'label': 'TikTok', 'hosts': ('tiktokcdn.com', 'tiktokcdn-us.com', 'tiktokcdn-eu.com'), 'schemes': ('rtmps', 'rtmp'), 'server': ''},   # TikTok gives its address to accounts it allows
}
MAX_LIVE = 3          # each stream is one video encode on the server
MAX_S = 4 * 3600
MAX_CHUNK = 2_000_000
KEY_RE = re.compile(r'^[A-Za-z0-9_\-.?=&:]{8,256}$')


def check_server(platform, url):
    """The ingest address, cleaned, or raises ValueError. Only that platform's published hosts."""
    p = PLATFORMS.get(platform)
    if not p:
        raise ValueError('Pick Twitch, Kick or TikTok.')
    u = str(url or p['server']).strip().rstrip('/')
    if not u:
        raise ValueError(f"Paste the server address from your {p['label']} stream settings.")
    s = urlsplit(u)
    host = (s.hostname or '').lower()
    if s.scheme not in p['schemes'] or s.username or s.password or not any(host == h or host.endswith('.' + h) for h in p['hosts']):
        raise ValueError(f"That is not a {p['label']} stream address.")
    return u


def check_key(key):
    k = str(key or '').strip()
    if not KEY_RE.match(k):
        raise ValueError('That does not look like a stream key.')
    return k


def target(server, key):
    return f'{server}/{key}'


def ffmpeg_args(targets):
    """One encode, sent to every channel. A channel that drops does not stop the others."""
    out = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-fflags', '+genpts', '-i', 'pipe:0',
           '-vf', 'scale=-2:720', '-r', '30', '-c:v', 'libx264', '-preset', 'veryfast', '-tune', 'zerolatency', '-pix_fmt', 'yuv420p', '-g', '60', '-b:v', '2500k', '-maxrate', '2500k', '-bufsize', '5000k',
           '-c:a', 'aac', '-b:a', '128k', '-ar', '44100']
    if len(targets) == 1:
        return out + ['-f', 'flv', targets[0]]
    return out + ['-map', '0:v', '-map', '0:a', '-f', 'tee', '|'.join(f'[f=flv:onfail=ignore]{t}' for t in targets)]


def hide_keys(text, keys):
    t = str(text or '')
    for k in keys or []:
        if k:
            t = t.replace(k, '•••')
    return t[-300:]


def public_row(row):
    """What anyone may know about a stream: that it is on, where, and since when. Never a key or address."""
    return {'on': True, 'since': row.get('since'), 'where': [PLATFORMS[p]['label'] for p in row.get('platforms') or [] if p in PLATFORMS]} if row else {'on': False}


def owner_view(keys):
    """The owner's stream settings: whether each is set, never the key."""
    return {p: {'label': v['label'], 'server': (keys or {}).get(p, {}).get('server') or v['server'], 'set': bool((keys or {}).get(p, {}).get('key')), 'needsServer': not v['server']} for p, v in PLATFORMS.items()}


class Relay:
    """One ffmpeg, fed by the owner's browser. It never logs a key."""
    def __init__(self, targets, keys=()):
        self.targets, self.keys, self.proc, self.err = list(targets), list(keys), None, ''

    async def start(self, spawn=asyncio.create_subprocess_exec):
        self.proc = await spawn(*ffmpeg_args(self.targets), stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        self._drain = asyncio.ensure_future(self._read_err())

    async def _read_err(self):
        try:
            while True:
                line = await self.proc.stderr.readline()
                if not line:
                    return
                self.err = hide_keys(line.decode(errors='ignore'), self.keys)
        except (asyncio.CancelledError, ValueError, OSError):
            return

    @property
    def alive(self):
        return bool(self.proc) and self.proc.returncode is None

    async def write(self, chunk):
        if not self.alive:
            raise ConnectionError(self.err or 'The stream stopped.')
        self.proc.stdin.write(chunk)
        await asyncio.wait_for(self.proc.stdin.drain(), 10)

    async def stop(self):
        if not self.proc:
            return
        try:
            if self.proc.stdin and not self.proc.stdin.is_closing():
                self.proc.stdin.close()
            await asyncio.wait_for(self.proc.wait(), 5)
        except (asyncio.TimeoutError, OSError, ConnectionError):
            try:
                self.proc.kill()
            except ProcessLookupError:
                pass

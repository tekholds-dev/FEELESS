"""👀 WHAT A VISITOR SEES (owner 2026-11-04): nearly everything an agent does, but never an email, a phone number or a password. A private page goes blank with a security line; the owner still sees it live.
A balance on a site may show. Anything this module cannot check is treated as private."""
import io
import re
from urllib.parse import urlsplit

from PIL import Image, ImageDraw, ImageFont

EMAIL = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
PHONE = re.compile(r'(?<![\w.])\+?\d{0,2}[\s.\-]?\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}(?![\w])')
MAIL_HOSTS = ('mail.google.com', 'outlook.live.com', 'outlook.office.com', 'mail.yahoo.com', 'proton.me', 'protonmail.com', 'mail.tm', 'agentmail.to', 'icloud.com', 'fastmail.com', 'tuta.com')
PRIVATE_WORDS = ('login', 'log-in', 'signin', 'sign-in', 'signup', 'sign-up', 'register', 'password', 'passkey', 'recover', '2fa', 'mfa', 'otp', 'verify', 'verification', 'kyc', 'identity',
                 'account', 'accounts', 'settings', 'profile', 'billing', 'payment', 'payments', 'security', 'personal', 'email', 'phone', 'contact-info', 'inbox', 'messages', 'withdraw', 'wallet-export', 'seed', 'api-keys')
LINE = 'This agent is on a private page'
SUB = 'Emails, phone numbers and sign-ins stay with its owner'
MAX_DEPTH = 8


def private_page(url):
    """True for a mailbox, a sign-in, or an account page. An address it cannot read is private."""
    try:
        s = urlsplit(str(url or ''))
    except ValueError:
        return True
    if s.scheme not in ('http', 'https') or not s.hostname:
        return bool(url)
    host = s.hostname.lower()
    if any(host == h or host.endswith('.' + h) for h in MAIL_HOSTS) or host.split('.')[0] in ('mail', 'webmail', 'accounts', 'login', 'auth', 'id', 'sso', 'signin'):
        return True
    parts = re.split(r'[/_.]', s.path.lower())
    return any(w in parts or any(p.startswith(w + '-') or p.endswith('-' + w) for p in parts) for w in PRIVATE_WORDS)


def scrub_text(text):
    return PHONE.sub('🔒', EMAIL.sub('🔒', str(text)))


def scrub(obj, depth=0):
    """Every string in a visitor's copy, with emails and phone numbers taken out."""
    if depth > MAX_DEPTH:
        return None
    if isinstance(obj, str):
        return scrub_text(obj) if '@' in obj or any(c.isdigit() for c in obj) else obj
    if isinstance(obj, dict):
        return {k: scrub(v, depth + 1) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [scrub(v, depth + 1) for v in obj]
    return obj


def _font(size):
    for path in ('/System/Library/Fonts/Supplemental/Arial Bold.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


_BLANK = None


def blank_jpg():
    """The one security screen every visitor monitor shows. Drawn once."""
    global _BLANK
    if _BLANK is None:
        im = Image.new('RGB', (960, 600), (6, 12, 10)); d = ImageDraw.Draw(im)
        for x in range(0, 960, 48):
            d.line([(x, 0), (x, 600)], fill=(11, 26, 19))
        for y in range(0, 600, 48):
            d.line([(0, y), (960, y)], fill=(11, 26, 19))
        d.rounded_rectangle([442, 190, 518, 262], 12, fill=(21, 209, 106))
        d.arc([456, 150, 504, 216], 180, 360, fill=(21, 209, 106), width=9)
        d.ellipse([472, 212, 488, 228], fill=(6, 12, 10))
        d.text((480, 306), LINE, font=_font(34), fill=(238, 243, 239), anchor='mm')
        d.text((480, 350), SUB, font=_font(20), fill=(150, 170, 160), anchor='mm')
        out = io.BytesIO(); im.save(out, 'JPEG', quality=70); _BLANK = out.getvalue()
    return _BLANK


# Runs in the agent's page: where any email, phone number or password field is on screen. It reads only; it changes nothing.
FIND_JS = r"""() => {
  const EM = /[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}/, PH = /(^|[^\w.])\+?\d{0,2}[\s.\-]?\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}(?!\w)/;
  const rects = [], push = r => { if (r.width > 0 && r.height > 0 && r.bottom > 0 && r.right > 0 && r.top < innerHeight && r.left < innerWidth) rects.push([r.left, r.top, r.right, r.bottom]); };
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let n, seen = 0;
  while ((n = w.nextNode()) && seen < 6000) { seen++; const t = n.nodeValue; if (t && t.length < 4000 && (EM.test(t) || PH.test(t))) { const r = document.createRange(); r.selectNodeContents(n); for (const b of r.getClientRects()) push(b); } }
  for (const el of document.querySelectorAll('input,textarea')) { const ty = (el.type || '').toLowerCase(), v = el.value || ''; if (ty === 'password' || ty === 'email' || ty === 'tel' || EM.test(v) || PH.test(v)) push(el.getBoundingClientRect()); }
  return { rects, w: innerWidth, h: innerHeight };
}"""


def redact(jpg, found):
    """The frame with a solid box over each spot. Raises when it cannot, and the caller then shows the blank screen."""
    im = Image.open(io.BytesIO(jpg)).convert('RGB')
    sx, sy = im.width / max(1, found['w']), im.height / max(1, found['h'])
    d = ImageDraw.Draw(im)
    for x0, y0, x1, y1 in found.get('rects') or []:
        d.rounded_rectangle([x0 * sx - 3, y0 * sy - 3, x1 * sx + 3, y1 * sy + 3], 4, fill=(6, 12, 10))
    out = io.BytesIO(); im.save(out, 'JPEG', quality=45)
    return out.getvalue()


async def visitor_frame(page, url=''):
    """A frame a stranger may see. Private page or any failure: the blank screen, never a raw frame."""
    if private_page(url or getattr(page, 'url', '')):
        return blank_jpg()
    try:
        find = page.find_private
        first = await find(FIND_JS)
        jpg = await page.shot()
        second = await find(FIND_JS)   # a page can move between the read and the picture: both sets are covered
        if not jpg or not first or not second:
            return blank_jpg()
        return redact(jpg, {**second, 'rects': [*first.get('rects', []), *second.get('rects', [])]})
    except Exception:   # noqa: BLE001 — fail closed
        return blank_jpg()


_NEVER = ('sig', 'wallet', 'tx', 'cookie', 'secret', 'token', 'owner', 'session')


def public_folder(folder):
    """A filed proof as a visitor may read it: no transaction or wallet that leads back to the owner, no PoB snapshot list, and no email or phone number."""
    keep = {k: v for k, v in (folder or {}).items() if not any(w in k.lower() for w in _NEVER) and not (k == 'shots' and str(folder.get('id') or '').startswith('pob'))}
    return scrub(keep)

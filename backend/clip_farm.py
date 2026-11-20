"""✂ Slice 15 (owner 2026-11-19: "PoC … clipfarming! yt, twitch, ig -> even if they can't access sites users should be able to upload vids etc up
to 5 mins and we provide best brains to clip farm epically and quickly!!"). The clip engine: free tools on this machine only, no service imports.

  upload (≤ 5 min, mp4 / mov / webm, size-capped, length read by ffprobe first)
    → transcript with word times (faster-whisper, local, int8 CPU: a 5-min talk in ~16 s, checked 2026-11-19)
    → peaks: loudness every ½ s, loud moments with no words (a laugh, a cheer, a hit), scene cuts (ffmpeg scdet)
    → candidate moments (15–60 s, cut on sentence ends, scored by code: hook in the first 2 s, a payoff, energy)
    → both minds score every candidate blind and say why (the service asks them; this file only writes the ask and reads the answers)
    → each pick tracked (OpenCV face finder, the speaker kept in frame; no face → where the motion is; never a fixed centre crop)
    → cut + reframed to 9:16, 1:1 and 16:9 with burned-in word-by-word captions, a hook title and a cover frame. No watermark.
Research 2026-11-19: the open clippers (OpenShorts, AutoClip, OpenClip) use the same stack (faster-whisper word times + face tracking + ffmpeg)."""
import hashlib
import json
import re
import subprocess
import tempfile
import time
from pathlib import Path

MAX_S = 300                         # the owner's cap: up to 5 minutes
MAX_BYTES = 600 * 1024 * 1024       # a 5-min 1080p phone recording is ~150–500 MB
EXTS = {'mp4': 'video/mp4', 'mov': 'video/quicktime', 'webm': 'video/webm', 'm4v': 'video/mp4', 'mkv': 'video/x-matroska', 'avi': 'video/x-msvideo'}   # any of these goes through the free converter
CLIP_MIN, CLIP_MAX, HOOK_S = 15.0, 60.0, 2.0
MAX_CANDS, MAX_PICKS = 8, 3
FORMATS = {'story': (1080, 1920, '9:16'), 'feed': (1080, 1080, '1:1'), 'wide': (1920, 1080, '16:9')}   # the folder's own format keys: feed = the 1:1 square here
WHISPER = 'base'                    # local model: free, ~150 MB, downloaded once into the Hugging Face cache
STEPS = (('probe', 'Read the file'), ('convert', 'Free converter: clean H.264 + AAC .mp4'), ('words', 'Transcript with word times'), ('peaks', 'Loudness, laughs and scene cuts'), ('moments', 'Candidate moments'),
         ('minds', 'Both minds pick blind'), ('clips', 'Track, cut, reframe and caption'), ('file', 'Filed as PoCs'))
FONT = Path(__file__).resolve().parent.parent / 'frontend' / 'public' / 'assets' / 'pdf-fonts' / 'LiberationSans-Bold.ttf'
GREEN = (25, 230, 140, 255)          # FEELESS green: a rendered file is the one place a colour is a number
INK = (8, 12, 10, 255)
WHITE = (255, 255, 255, 255)
_MODEL = {}


# ── 0 · the file ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def ext_of(name, ctype=''):
    """The upload's kind from its name (or content type) → 'mp4' | 'mov' | 'webm' | 'm4v'. ValueError with what to do."""
    m = re.search(r'\.([A-Za-z0-9]{2,5})$', str(name or ''))
    e = (m.group(1).lower() if m else '') or next((k for k, v in EXTS.items() if v == str(ctype or '').split(';')[0].strip().lower()), '')
    if e not in EXTS:
        raise ValueError('Upload a video file: MP4, MOV, WebM, MKV, AVI or M4V.')
    return e


def probe(path, ffprobe='ffprobe'):
    """ffprobe, before anything else runs → {secs, w, h, fps, audio}. ValueError when it is not a readable video."""
    try:
        r = subprocess.run([ffprobe, '-v', 'error', '-print_format', 'json', '-show_format', '-show_streams', str(path)], capture_output=True, timeout=60)
        d = json.loads(r.stdout or b'{}')
    except (subprocess.SubprocessError, ValueError, OSError):
        d = {}
    v = next((s for s in d.get('streams') or [] if s.get('codec_type') == 'video'), None)
    try:
        secs = float((d.get('format') or {}).get('duration') or (v or {}).get('duration') or 0)
    except (TypeError, ValueError):
        secs = 0.0
    if not v or secs <= 0:
        raise ValueError('ffmpeg could not read a picture in that file, so it is not a video it can convert. Export it again from your app.')
    w, h = int(v.get('width') or 0), int(v.get('height') or 0)
    rot = str(((v.get('tags') or {}).get('rotate')) or next((sd.get('rotation') for sd in v.get('side_data_list') or [] if 'rotation' in sd), '') or '0')
    if rot.strip('-') in ('90', '270'):
        w, h = h, w
    try:
        a, b = str(v.get('avg_frame_rate') or '30/1').split('/')
        fps = float(a) / float(b or 1) or 30.0
    except (ValueError, ZeroDivisionError):
        fps = 30.0
    a_ = next((s for s in d.get('streams') or [] if s.get('codec_type') == 'audio'), None)
    return {'secs': round(secs, 2), 'w': w, 'h': h, 'fps': round(min(60.0, max(1.0, fps)), 2), 'audio': bool(a_),
            'vcodec': str(v.get('codec_name') or '?'), 'acodec': str((a_ or {}).get('codec_name') or ''), 'pix': str(v.get('pix_fmt') or ''),
            'box': str((d.get('format') or {}).get('format_name') or '').split(',')[0], 'rot': rot.strip('-') in ('90', '270')}


# ── 0½ · the free converter (owner 2026-11-19: "a free converter for .mov etc") ──────────────────────────────────────────────────────
def clean(info, ext):
    """Already a plain H.264 + AAC MP4 (yuv420p, no rotation flag, ≤ 1920 px)? Then it is kept as it is. Pure."""
    return (ext in ('mp4', 'm4v') and info.get('vcodec') == 'h264' and info.get('acodec') == 'aac' and info.get('pix') in ('yuv420p', 'yuvj420p')
            and not info.get('rot') and max(info.get('w') or 0, info.get('h') or 0) <= 1920)


def convert_args(src, out, encoder='h264_videotoolbox'):
    """Any video ffmpeg reads (HEVC / iPhone .mov, MKV, AVI, WebM VP9, odd audio) → H.264 + AAC 48 kHz stereo MP4, long side ≤ 1920 px,
    at most 60 fps, upright (ffmpeg applies the rotation flag), at most MAX_S seconds, faststart so it plays while it loads."""
    enc = ['-c:v', 'h264_videotoolbox', '-b:v', '10M', '-allow_sw', '1'] if encoder == 'h264_videotoolbox' else ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20']
    return ['ffmpeg', '-v', 'error', '-nostdin', '-y', '-i', str(src), '-t', f'{MAX_S + 0.5:.1f}', '-map', '0:v:0', '-map', '0:a:0?',
            '-vf', "scale='if(gt(iw,ih),min(1920,iw),-2)':'if(gt(iw,ih),-2,min(1920,ih))',fps='min(60,source_fps)'", *enc, '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '160k', '-ac', '2', '-ar', '48000', '-movflags', '+faststart', str(out)]


def convert(src, out):
    """Runs the converter (Apple's hardware encoder, then plain x264 if that fails). → seconds it took. ValueError with a plain reason."""
    t0 = time.time(); last = ''
    for enc in ('h264_videotoolbox', 'libx264'):
        r = subprocess.run(convert_args(src, out, enc), capture_output=True, timeout=900)
        if r.returncode == 0 and Path(out).is_file() and Path(out).stat().st_size > 1000:
            return round(time.time() - t0, 1)
        last = ((r.stderr or b'').decode(errors='replace').strip().splitlines() or [''])[-1][:140]
    Path(out).unlink(missing_ok=True)
    raise ValueError(f'The free converter could not turn it into an MP4 ({last or "ffmpeg gave no reason"}). Export it again from your app.')


def check(info, size):
    """The owner's limits, said plainly. Pure."""
    if size > MAX_BYTES:
        raise ValueError(f'That file is {size / 1e6:.0f} MB. Up to {MAX_BYTES // 1_000_000} MB: export it smaller.')
    if info['secs'] > MAX_S + 0.5:
        raise ValueError(f"That video is {int(info['secs'] // 60)}:{int(info['secs'] % 60):02d} long. Up to 5:00: trim it first.")
    if info['secs'] < CLIP_MIN:
        raise ValueError(f'That video is {info["secs"]:.0f} s. A clip needs at least {CLIP_MIN:.0f} s.')
    if not info['audio']:
        raise ValueError('That video has no sound, so there is nothing to caption. Upload one with its sound.')
    return info


def pcm(path, ffmpeg='ffmpeg'):
    """The sound as 16 kHz mono float32 (numpy), decoded by ffmpeg."""
    import numpy as np
    raw = subprocess.run([ffmpeg, '-v', 'error', '-nostdin', '-i', str(path), '-vn', '-f', 's16le', '-ac', '1', '-ar', '16000', '-'], capture_output=True, timeout=180).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


# ── 1 · words, peaks, cuts ──────────────────────────────────────────────────────────────────────────────────────────────────────────
def transcribe(audio, model=WHISPER):
    """faster-whisper on this machine → [{s, e, w}] with word times. $0."""
    from faster_whisper import WhisperModel
    m = _MODEL.get(model) or _MODEL.setdefault(model, WhisperModel(model, device='cpu', compute_type='int8', cpu_threads=8))
    segs, _info = m.transcribe(audio, word_timestamps=True, vad_filter=True, beam_size=1, condition_on_previous_text=False)
    return [{'s': round(float(x.start), 2), 'e': round(float(x.end), 2), 'w': str(x.word).strip()} for s in segs for x in (s.words or []) if str(x.word).strip()]


def loudness(audio, hop=0.5, rate=16000):
    """RMS level in dB for every ½ s. Pure (numpy)."""
    import numpy as np
    n = int(hop * rate); k = len(audio) // n
    if k <= 0:
        return []
    a = audio[:k * n].reshape(k, n)
    return [round(float(x), 1) for x in 20 * np.log10(np.sqrt((a ** 2).mean(axis=1)) + 1e-6)]


def laughs(words, loud, hop=0.5):
    """Loud moments with no words spoken over them (a laugh, a cheer, a hit): ≥ 6 dB over the median, no word in that ½ s. → [seconds]. Pure."""
    if not loud:
        return []
    med = sorted(loud)[len(loud) // 2]; said = set()
    for w in words:
        for i in range(int(w['s'] / hop), int(w['e'] / hop) + 1):
            said.add(i)
    out = []
    for i, db in enumerate(loud):
        if db >= med + 6 and i not in said and (not out or i * hop - out[-1] > 2):
            out.append(round(i * hop, 1))
    return out


def scene_cuts(path, ffmpeg='ffmpeg'):
    """Scene changes (ffmpeg scdet on a small copy) → [seconds]."""
    r = subprocess.run([ffmpeg, '-v', 'info', '-nostdin', '-i', str(path), '-an', '-vf', 'fps=10,scale=320:-2,scdet=threshold=12', '-f', 'null', '-'],
                       capture_output=True, timeout=240)
    return sorted({round(float(m), 2) for m in re.findall(rb'lavfi\.scd\.time:\s*([0-9.]+)', r.stderr or b'')})


# ── 2 · candidate moments ───────────────────────────────────────────────────────────────────────────────────────────────────────────
def sentences(words):
    """Words → sentences [(first word i, last word i)], split on . ! ? or a pause over 1.2 s. Pure."""
    out, a = [], 0
    for i, w in enumerate(words):
        end = re.search(r'[.!?]["”]?$', w['w']) or (i + 1 < len(words) and words[i + 1]['s'] - w['e'] > 1.2)
        if end or i == len(words) - 1:
            out.append((a, i)); a = i + 1
    return out


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def moments(words, loud, cuts, laughs_, secs, hop=0.5, keep=MAX_CANDS):
    """Every 15–60 s window that starts on a sentence start and ends on a sentence end, scored by code; the best `keep` that do not overlap.
    → [{n, s, e, dur, text, first2, facts, local}]. Pure."""
    sents = sentences(words); med = sorted(loud)[len(loud) // 2] if loud else -40.0; rows = []
    for a, (i0, _) in enumerate(sents):
        s = max(0.0, words[i0]['s'] - 0.15)
        for i1 in range(a, len(sents)):
            j = sents[i1][1]; e = min(secs, words[j]['e'] + 0.35); d = e - s
            if d > CLIP_MAX:
                break
            if d < CLIP_MIN:
                continue
            ws = words[i0:j + 1]; seg = loud[int(s / hop):int(e / hop) + 1] or [med]
            first = [w for w in ws if w['s'] < s + HOOK_S]; tail = seg[int(len(seg) * .7):] or seg
            last_w = ws[-1]['w']; peaks = sum(1 for x in seg if x >= med + 4)
            facts = {'hookWords': len(first), 'hookDb': round(_mean(seg[:int(HOOK_S / hop)]) - med, 1), 'endsOn': '?' if last_w.endswith('?') else '!' if last_w.endswith('!') else '.',
                     'tailDb': round(_mean(tail) - _mean(seg), 1), 'wordsPerS': round(len(ws) / d, 2), 'peaks': peaks,
                     'laughs': sum(1 for t in laughs_ if s <= t <= e), 'cuts': sum(1 for t in cuts if s < t < e)}
            local = (min(3, len(first)) * 1.0 + max(0, min(2, facts['hookDb'] / 3)) + (1.0 if facts['endsOn'] in '!?' else 0) + max(0, min(1.5, facts['tailDb'] / 2))
                     + min(1.5, peaks / 8) + min(1.0, facts['laughs'] * .5) + min(1.0, facts['wordsPerS'] / 3) - abs(d - 35) / 40)
            rows.append({'s': round(s, 2), 'e': round(e, 2), 'dur': round(d, 1), 'text': ' '.join(w['w'] for w in ws)[:1200], 'first2': ' '.join(w['w'] for w in first)[:120],
                         'facts': facts, 'local': round(max(0.0, min(10.0, local)), 2)})
    rows.sort(key=lambda r: -r['local']); out = []
    for r in rows:
        if all(min(r['e'], o['e']) - max(r['s'], o['s']) < 0.25 * min(r['dur'], o['dur']) for o in out):
            out.append(r)
        if len(out) >= keep:
            break
    out.sort(key=lambda r: r['s'])
    return [{'n': i + 1, **r} for i, r in enumerate(out)]


# ── 3 · both minds, blind ───────────────────────────────────────────────────────────────────────────────────────────────────────────
SYS = ('You are a short-form video editor who clip-farms for Shorts, Reels and TikTok. Below are numbered candidate moments cut from ONE uploaded video, '
       'each with its transcript and what the sound and picture did. Score EVERY candidate 0-10 for how well it works as a stand-alone short: '
       'a hook that grabs in the first 2 seconds, a payoff at the end, and a reason to watch to the end. You may tighten a pick (start later / end '
       'earlier, inside its own times, keep it 15-60 s). For your best 3 write the hook title (on screen for the first 2 s, max 8 words), the post '
       'caption (max 180 chars, 2-4 hashtags) and what pays off. Never invent words the person did not say. Answer ONLY with JSON: '
       '{"scores":[{"n":1,"score":0-10,"why":"at most 12 words"}],"picks":[{"n":1,"start":s,"end":s,"hook":"…","caption":"…","payoff":"…","views":7-day views you expect}]}')
RETRY = 'Your last reply could not be read. Reply with ONE JSON object only, no thinking, no code fence: {"scores":[…],"picks":[…]} as asked.'


def ask_text(cands, name='', note=''):
    rows = [f"#{c['n']} {c['s']:.1f}-{c['e']:.1f} s ({c['dur']:.0f} s) · first 2 s: \"{c['first2']}\" · ends on '{c['facts']['endsOn']}' · "
            f"{c['facts']['peaks']} loud peaks, {c['facts']['laughs']} laughs/cheers, {c['facts']['cuts']} scene cuts\n   \"{c['text'][:700]}\"" for c in cands]
    return (f"The upload: {name or 'a video'}." + (f" Owner's note: {note[:200]}." if note else '') + '\n\n' + '\n'.join(rows))


def _objs(t):
    """Every complete flat {…} object in a text, in order (a reply cut off mid-way still gives the ones it finished). Pure."""
    out, depth, a, q, esc = [], 0, -1, False, False
    for i, ch in enumerate(t):
        if q:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                q = False
            continue
        if ch == '"':
            q = True
        elif ch == '{':
            depth += 1; a = i if depth == 1 else a
        elif ch == '}' and depth:
            depth -= 1
            if depth == 0 and a >= 0:
                try:
                    out.append(json.loads(t[a:i + 1]))
                except ValueError:
                    pass
    return out


def _json(raw):
    """The reply's JSON; a reply cut off before its end (a local mind out of room) → every score and pick object it finished."""
    t = re.sub(r'<think>.*?</think>', '', str(raw or ''), flags=re.S)
    a, b = t.find('{'), t.rfind('}')
    try:
        d = json.loads(t[a:b + 1]) if a >= 0 and b > a else None
        if isinstance(d, dict):
            return d
    except ValueError:
        pass
    a = t.find('{')
    if a < 0:
        return None
    k = t.find('"picks"'); body = t[a + 1:]; head, tail = (t[a + 1:k], t[k:]) if k > a else (body, '')
    sc = [o for o in _objs(head) if isinstance(o, dict) and 'score' in o]; pk = [o for o in _objs(tail) if isinstance(o, dict) and 'n' in o]
    return {'scores': sc, 'picks': pk, 'cut': True} if sc or pk else None


def _num(v, lo, hi):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if x != x else max(lo, min(hi, x))


def parse_mind(raw, cands):
    """One mind's answer → {'scores': {n: (score, why)}, 'picks': [{n, start, end, hook, caption, payoff, views}]} or None. Pure."""
    d = _json(raw); by = {c['n']: c for c in cands}
    if not isinstance(d, dict):
        return None
    sc = {}
    for r in d.get('scores') or []:
        if isinstance(r, dict) and _num(r.get('n'), 1, 99) in by and _num(r.get('score'), 0, 10) is not None:
            sc[int(r['n'])] = (round(_num(r['score'], 0, 10), 1), ' '.join(str(r.get('why') or '').split())[:200])
    picks = []
    for r in d.get('picks') or []:
        n = _num((r or {}).get('n'), 1, 99) if isinstance(r, dict) else None
        if n not in by or any(p['n'] == int(n) for p in picks):
            continue
        c = by[int(n)]; s = _num(r.get('start'), c['s'], c['e']) or c['s']; e = _num(r.get('end'), c['s'], c['e']) or c['e']
        if e - s < CLIP_MIN:
            s, e = c['s'], c['e']
        picks.append({'n': int(n), 'start': round(s, 2), 'end': round(min(e, s + CLIP_MAX), 2), 'hook': ' '.join(str(r.get('hook') or '').split())[:70],
                      'caption': ' '.join(re.sub(r'#?\bMind\s?[AB]\b', '', str(r.get('caption') or '')).split())[:220],   # its seat name is never a hashtag
                      'payoff': ' '.join(str(r.get('payoff') or '').split())[:160],
                      'views': int(_num(r.get('views'), 0, 10_000_000) or 0)})
    if not sc and not picks:
        return None
    for p in picks:   # a pick it never scored still counts as its own high mark
        sc.setdefault(p['n'], (7.0, 'picked'))
    return {'scores': sc, 'picks': picks[:MAX_PICKS]}


def choose(cands, minds, n=MAX_PICKS):
    """Both minds' blind scores → the clips to make, best first. Each clip keeps every mind's score and why; the hook / caption come from the
    mind that scored it higher (a mind that answered nothing → code's own score stands in, and the record says so). Pure."""
    out = []
    for c in cands:
        per = []
        for i, m in enumerate(minds):
            s = (m or {}).get('scores', {}).get(c['n'])
            pk = next((p for p in (m or {}).get('picks') or [] if p['n'] == c['n']), None)
            per.append({'mind': i, 'score': s[0] if s else None, 'why': s[1] if s else '', 'picked': bool(pk), 'pick': pk})
        got = [p['score'] for p in per if p['score'] is not None]
        both = round(_mean(got), 2) if got else None
        rank = (both if both is not None else c['local']) * .85 + c['local'] * .15 + .4 * sum(p['picked'] for p in per)
        lead = max((p for p in per if p['pick']), key=lambda p: p['score'] or 0, default=None)
        out.append({**c, 'minds': per, 'both': both, 'rank': round(rank, 2), 'lead': lead['mind'] if lead else None,
                    **({k: lead['pick'][k] for k in ('hook', 'caption', 'payoff', 'views')} | {'s': lead['pick']['start'], 'e': lead['pick']['end']} if lead else {})})
    out.sort(key=lambda r: -r['rank'])
    keep = [r for r in out if (r['both'] is None or r['both'] >= 4) and (r['both'] is not None or r['local'] >= 3)][:n]
    for r in keep:
        r['dur'] = round(r['e'] - r['s'], 1)
        r['hook'] = r.get('hook') or ' '.join(r['first2'].split()[:8]) or 'Watch this'
        r['caption'] = r.get('caption') or r['hook']
    return keep, out


def goal(picked):
    """The goal set at filing: the minds' own 7-day view guess, kept sane; none given → 1,000 views, and said."""
    v = int(picked.get('views') or 0)
    if v >= 10:
        return {'type': 'reach', 'target': max(100, min(5_000_000, v)), 'why': 'the minds’ own 7-day guess for this clip', 'by': 'minds', 'locked': False}
    return {'type': 'reach', 'target': 1000, 'why': 'the minds gave no number: 1,000 views in 7 days', 'by': 'code', 'locked': False}


# ── 4 · the speaker, tracked ────────────────────────────────────────────────────────────────────────────────────────────────────────
def track(path, s, e, info, cuts=(), fps=5, ffmpeg='ffmpeg'):
    """Where to point the crop, 5 times a second: the face (OpenCV's frontal + profile finders; the face nearest the last one, else the biggest),
    no face → the centre of motion and detail. Smoothed (a dead zone + easing), reset on a scene cut. → {'pts': [(t, cx, cy)], faces, frames, how}"""
    import cv2
    import numpy as np
    W = 480; H = max(2, int(round(W * info['h'] / max(1, info['w']) / 2)) * 2)
    raw = subprocess.run([ffmpeg, '-v', 'error', '-nostdin', '-ss', f'{s:.2f}', '-t', f'{e - s:.2f}', '-i', str(path), '-an', '-vf', f'fps={fps},scale={W}:{H}',
                          '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True, timeout=180).stdout
    n = len(raw) // (W * H)
    frames = np.frombuffer(raw[:n * W * H], np.uint8).reshape(n, H, W) if n else []
    det = [cv2.CascadeClassifier(cv2.data.haarcascades + f) for f in ('haarcascade_frontalface_default.xml', 'haarcascade_profileface.xml')]
    pts, faces, last, prev, cur = [], 0, None, None, None
    cut_at = [t - s for t in cuts if s < t < e]
    for k, f in enumerate(frames):
        t = k / fps
        if cut_at and any(abs(t - c) < .5 / fps + 1e-6 or (t - 1 / fps < c <= t) for c in cut_at):
            last, cur = None, None   # a new shot: find the subject again, no easing across the cut
        found = []; g = None
        for d in det:
            found += [tuple(map(int, r)) for r in d.detectMultiScale(f, 1.1, 5, minSize=(max(18, W // 24),) * 2)]
        if found:
            faces += 1
            x, y, w, h = min(found, key=lambda r: (abs(r[0] + r[2] / 2 - last[0] * W) if last else 0) - r[2] * r[3] / 50)
            target = ((x + w / 2) / W, (y + h / 2) / H); last = target; prev = None
        else:
            g = cv2.GaussianBlur(f, (9, 9), 0); edge = cv2.convertScaleAbs(cv2.Laplacian(g, cv2.CV_16S)).astype(np.float32)
            mot = cv2.absdiff(g, prev).astype(np.float32) * 3 if prev is not None and prev.shape == g.shape else 0
            wgt = edge + mot; tot = float(wgt.sum()) if hasattr(wgt, 'sum') else 0
            if tot > 1:
                xs = (wgt.sum(axis=0) * np.arange(W)).sum() / tot; ys = (wgt.sum(axis=1) * np.arange(H)).sum() / tot
                target = (float(xs) / W, float(ys) / H)
            else:
                target = cur or (0.5, 0.45)
            if last is not None:   # keep the last face a moment when it only turned away
                target = last
            prev = g
        if cur is None:
            cur = target
        else:
            dx, dy = target[0] - cur[0], target[1] - cur[1]
            if abs(dx) > .04 or abs(dy) > .06:   # dead zone: a still speaker gives a still frame
                cur = (cur[0] + dx * .35, cur[1] + dy * .35)
        pts.append((round(t, 2), round(cur[0], 4), round(cur[1], 4), 1 if found else 0))
    return {'pts': pts, 'faces': faces, 'frames': len(pts), 'how': 'face' if pts and faces >= len(pts) * .3 else 'motion' if pts else 'none'}


def crop_box(info, fmt):
    """The crop size in source pixels for a format, or None when the format is wider than the source (then it is fitted on a blurred fill). Pure."""
    W, H, _ = FORMATS[fmt]; sw, sh = info['w'], info['h']
    if W / H > sw / sh + 1e-3:
        return None
    cw = int(sh * W / H) // 2 * 2
    return (cw, sh // 2 * 2) if cw <= sw else (sw // 2 * 2, int(sw * H / W) // 2 * 2)


def crop_cmds(pts, info, box, fps_out=10):
    """sendcmd lines that slide the crop to the tracked point (interpolated 10×/s). Pure."""
    if not pts:
        return ''
    cw, ch = box; sw, sh = info['w'], info['h']; lines = []; T = pts[-1][0]; k = 0; t = 0.0
    while t <= T + 1e-6:
        while k + 1 < len(pts) and pts[k + 1][0] <= t:
            k += 1
        a = pts[k]; b = pts[k + 1] if k + 1 < len(pts) else a; f = 0 if b[0] == a[0] else (t - a[0]) / (b[0] - a[0])
        cx = a[1] + (b[1] - a[1]) * f; cy = a[2] + (b[2] - a[2]) * f
        x = int(max(0, min(sw - cw, cx * sw - cw / 2))); y = int(max(0, min(sh - ch, cy * sh - ch * .42)))
        lines.append(f'{t:.2f} crop x {x}, crop y {y};'); t += 1 / fps_out
    return '\n'.join(lines)


# ── 5 · captions, hook title, cover ─────────────────────────────────────────────────────────────────────────────────────────────────
def groups(words, s, e, most=3):
    """The clip's words as short caption groups (≤ 3 words, broken at punctuation or a pause), times from the clip start. Pure."""
    ws = [{**w, 's': max(0.0, w['s'] - s), 'e': min(e - s, w['e'] - s)} for w in words if w['e'] > s and w['s'] < e]
    out, cur = [], []
    for i, w in enumerate(ws):
        cur.append(w)
        nxt = ws[i + 1] if i + 1 < len(ws) else None
        if len(cur) >= most or re.search(r'[.,!?;:]$', w['w']) or not nxt or nxt['s'] - w['e'] > .6:
            out.append(cur); cur = []
    return out


def _font(px):
    from PIL import ImageFont
    try:
        return ImageFont.truetype(str(FONT), px)
    except OSError:
        return ImageFont.load_default()


def _band(W, words, hot, px):
    """One caption band: the group in white capitals with a thick ink edge, the word being said in FEELESS green, a touch bigger."""
    from PIL import Image, ImageDraw
    f, fb = _font(px), _font(int(px * 1.12)); txt = [re.sub(r'[^\w\'’$%#@&!?.,-]', '', w['w']).upper() or w['w'] for w in words]
    d0 = ImageDraw.Draw(Image.new('RGBA', (8, 8))); gap = int(px * .32)
    sizes = [d0.textbbox((0, 0), t, font=fb if i == hot else f, stroke_width=max(3, px // 9)) for i, t in enumerate(txt)]
    widths = [b[2] - b[0] for b in sizes]
    while sum(widths) + gap * (len(txt) - 1) > W * .9 and px > 24:
        return _band(W, words, hot, int(px * .88))
    H = int(px * 1.7); im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x = (W - sum(widths) - gap * (len(txt) - 1)) // 2
    for i, t in enumerate(txt):
        d.text((x - sizes[i][0], (H - (sizes[i][3] - sizes[i][1])) // 2 - sizes[i][1]), t, font=fb if i == hot else f, fill=GREEN if i == hot else WHITE,
               stroke_width=max(3, px // 9), stroke_fill=INK)
        x += widths[i] + gap
    return im


def hook_band(W, hook, px):
    """The hook title for the first 2 s: ink words on a FEELESS-green bar."""
    from PIL import Image, ImageDraw
    f = _font(px); d0 = ImageDraw.Draw(Image.new('RGBA', (8, 8))); lines, cur = [], ''
    for w in str(hook or '').split():
        t = (cur + ' ' + w).strip()
        if d0.textlength(t, font=f) > W * .8 and cur:
            lines.append(cur); cur = w
        else:
            cur = t
    lines = (lines + [cur])[:2] if cur else lines[:2]
    lh = int(px * 1.2); H = lh * len(lines) + int(px * .9); im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    bw = int(max(d0.textlength(x, font=f) for x in lines) + px * 1.2) if lines else 0
    d.rounded_rectangle(((W - bw) // 2, 0, (W + bw) // 2, H), radius=int(px * .35), fill=GREEN)
    for i, x in enumerate(lines):
        d.text(((W - d0.textlength(x, font=f)) // 2, int(px * .45) + i * lh), x, font=f, fill=INK)
    return im


def caption_track(words, s, e, W, H, tmp, fmt):
    """The captions as one picture stream (ffmpeg concat list of bands with their durations) → (list path, band y, band count)."""
    from PIL import Image
    px = {'story': 88, 'feed': 66, 'wide': 60}[fmt]; y = int(H * {'story': .66, 'feed': .70, 'wide': .78}[fmt])
    blank = Path(tmp) / f'{fmt}_blank.png'; Image.new('RGBA', (W, int(px * 1.7)), (0, 0, 0, 0)).save(blank)
    rows, t, k = [], 0.0, 0
    for g in groups(words, s, e):
        for i, w in enumerate(g):
            a = w['s']; b = g[i + 1]['s'] if i + 1 < len(g) else max(w['e'], a + .25)
            if a > t + .01:
                rows.append((blank, a - t))
            p = Path(tmp) / f'{fmt}_{k}.png'; _band(W, g, i, px).save(p, compress_level=1); k += 1
            rows.append((p, max(.04, b - max(a, t)))); t = max(t, b)
    dur = e - s
    if t < dur:
        rows.append((blank, dur - t))
    lst = Path(tmp) / f'{fmt}_caps.txt'
    lst.write_text('ffconcat version 1.0\n' + ''.join(f"file '{p.name}'\nduration {d:.3f}\n" for p, d in rows) + f"file '{rows[-1][0].name}'\n")
    return lst, y, k


def render(src, clip, words, info, fmt, pts, out, tmp, ffmpeg='ffmpeg', encoder='h264_videotoolbox'):
    """One clip in one format: cut, reframed on the tracked point (or fitted on a blurred fill when the format is wider than the source),
    word-by-word captions, the hook title for the first 2 s, the original sound. No watermark. → seconds it took"""
    t0 = time.time(); W, H, _ = FORMATS[fmt]; s, e = clip['s'], clip['e']; box = crop_box(info, fmt)
    lst, cy, _k = caption_track(words, s, e, W, H, tmp, fmt)
    hook = Path(tmp) / f'{fmt}_hook.png'; hb = hook_band(W, clip.get('hook') or '', {'story': 64, 'feed': 52, 'wide': 50}[fmt]); hb.save(hook)
    hy = int(H * {'story': .14, 'feed': .08, 'wide': .07}[fmt])
    if box:
        cmds = Path(tmp) / f'{fmt}_crop.txt'; cmds.write_text(crop_cmds(pts, info, box) or '0.00 crop x 0;')
        x0 = int(max(0, min(info['w'] - box[0], (pts[0][1] if pts else .5) * info['w'] - box[0] / 2)))
        base = f"[0:v]sendcmd=f='{cmds.name}',crop={box[0]}:{box[1]}:{x0}:0,scale={W}:{H}:flags=lanczos,setsar=1[b]"
    else:
        base = (f'[0:v]split[a][f];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=24:2,eq=brightness=-0.12[bg];'
                f'[f]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[b]')
    filt = base + f";[b][1:v]overlay=0:{cy}:format=auto[c];[c][2:v]overlay=0:{hy}:enable='lt(t,{HOOK_S + .5})'[v]"
    fps = min(30.0, info.get('fps') or 30)
    enc = (['-c:v', 'h264_videotoolbox', '-b:v', '9M' if fmt == 'story' else '7M', '-allow_sw', '1'] if encoder == 'h264_videotoolbox'
           else ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20'])
    cmd = [ffmpeg, '-v', 'error', '-nostdin', '-y', '-ss', f'{s:.2f}', '-t', f'{e - s:.2f}', '-i', str(src), '-f', 'concat', '-safe', '0', '-i', lst.name,
           '-loop', '1', '-t', f'{e - s:.2f}', '-i', hook.name, '-filter_complex', filt, '-map', '[v]', '-map', '0:a:0?', '-r', f'{fps:g}',
           *enc, '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', str(out)]
    r = subprocess.run(cmd, cwd=str(tmp), capture_output=True, timeout=600)
    if (r.returncode != 0 or not Path(out).is_file() or not Path(out).stat().st_size) and encoder != 'libx264':
        return render(src, clip, words, info, fmt, pts, out, tmp, ffmpeg, 'libx264')
    if r.returncode != 0:
        raise RuntimeError((r.stderr or b'').decode(errors='replace').strip().splitlines()[-1:][0][:200] if r.stderr else f'ffmpeg exit {r.returncode}')
    return round(time.time() - t0, 1)


def cover(src, clip, info, fmt, pts, ffmpeg='ffmpeg'):
    """The cover frame: a face moment a third of the way in (else its first second), framed like the clip, with the hook title. → JPEG bytes"""
    from io import BytesIO
    from PIL import Image
    W, H, _ = FORMATS[fmt]; box = crop_box(info, fmt); mid = (clip['e'] - clip['s']) / 3
    fc = [q for q in pts or [] if len(q) > 3 and q[3]]
    at = clip['s'] + (min(fc, key=lambda q: abs(q[0] - mid))[0] if fc else min(1.0, mid))
    raw = subprocess.run([ffmpeg, '-v', 'error', '-nostdin', '-ss', f'{at:.2f}', '-i', str(src), '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'],
                         capture_output=True, timeout=60).stdout
    im = Image.open(BytesIO(raw)).convert('RGB')
    if box:
        p = min(pts, key=lambda q: abs(q[0] - (at - clip['s']))) if pts else (0, .5, .45)
        x = int(max(0, min(info['w'] - box[0], p[1] * info['w'] - box[0] / 2))); y = int(max(0, min(info['h'] - box[1], p[2] * info['h'] - box[1] * .42)))
        im = im.resize((info['w'], info['h'])).crop((x, y, x + box[0], y + box[1])).resize((W, H), Image.LANCZOS)
    else:
        from PIL import ImageFilter
        bg = im.copy(); r_ = max(W / bg.width, H / bg.height); bg = bg.resize((int(bg.width * r_) + 1, int(bg.height * r_) + 1)).crop((0, 0, W, H)).filter(ImageFilter.GaussianBlur(28))
        r2 = min(W / im.width, H / im.height); fg = im.resize((int(im.width * r2), int(im.height * r2)), Image.LANCZOS); bg.paste(fg, ((W - fg.width) // 2, (H - fg.height) // 2)); im = bg
    hb = hook_band(W, clip.get('hook') or '', {'story': 72, 'feed': 60, 'wide': 58}[fmt]); im = im.convert('RGBA')
    im.alpha_composite(hb, (0, int(H * {'story': .14, 'feed': .08, 'wide': .07}[fmt])))
    buf = BytesIO(); im.convert('RGB').save(buf, 'JPEG', quality=88); return buf.getvalue()


def make_clip(src, clip, words, info, cuts, save, ffmpeg='ffmpeg', on_step=None):
    """Track once, then every format (the phone story first: it is the one that posts to Shorts / Reels / TikTok) → (files, track facts).
    `save(piece, ext, bytes)` keeps a file and gives back its url. A format that fails is listed with its error, never hidden."""
    files = []; tr = track(src, clip['s'], clip['e'], info, cuts, ffmpeg=ffmpeg)
    with tempfile.TemporaryDirectory() as tmp:
        for fmt in FORMATS:
            W, H, ratio = FORMATS[fmt]
            try:
                out = Path(tmp) / f'{fmt}.mp4'; secs = render(src, clip, words, info, fmt, tr['pts'], out, tmp, ffmpeg)
                raw = out.read_bytes()
                files.append({'piece': 'video', 'format': fmt, 'aspect': ratio, 'w': W, 'h': H, 'url': save('video', 'mp4', raw), 'bytes': len(raw),
                              'sha': hashlib.sha256(raw).hexdigest()[:16], 'secs': secs, 'dur': round(clip['e'] - clip['s'], 1),
                              'reframe': 'tracked crop' if crop_box(info, fmt) else 'fitted on a blurred fill'})
            except Exception as e:   # noqa: BLE001
                files.append({'piece': 'video', 'format': fmt, 'aspect': ratio, 'error': f'{type(e).__name__}: {str(e)[:160]}'})
            try:
                jpg = cover(src, clip, info, fmt, tr['pts'], ffmpeg)
                files.append({'piece': 'image', 'format': fmt, 'aspect': ratio, 'w': W, 'h': H, 'url': save('image', 'jpg', jpg), 'bytes': len(jpg), 'cover': True,
                              'sha': hashlib.sha256(jpg).hexdigest()[:16]})
            except Exception as e:   # noqa: BLE001
                files.append({'piece': 'image', 'format': fmt, 'aspect': ratio, 'error': f'{type(e).__name__}: {str(e)[:160]}'})
            if on_step:
                on_step(fmt)
        cap = (clip.get('caption') or clip.get('hook') or '').strip()
        for fmt in FORMATS:
            files.append({'piece': 'post', 'format': fmt, 'url': save('post', 'txt', cap.encode()), 'text': cap, 'bytes': len(cap.encode())})
    return files, {k: tr[k] for k in ('faces', 'frames', 'how')}


def files_check(files):
    """Is the clip there in every format, with its cover? → (ok, why). Pure."""
    have = {(f['piece'], f['format']) for f in files or [] if isinstance(f, dict) and f.get('url') and not f.get('error')}
    miss = [f'{p} {FORMATS[m][2]}' for p in ('video', 'image') for m in FORMATS if (p, m) not in have]
    return not miss, f"{sum(1 for p in ('video', 'image') for m in FORMATS if (p, m) in have)} of 6 files" + (f"; missing {', '.join(miss)}" if miss else ': the clip and its cover in 9:16, 1:1 and 16:9')

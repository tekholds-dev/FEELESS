"""🧠 THE MODEL DESK (owner, 2026-10-23: "the Models tab should really show all this — server settings, MCP, load, inference … more vitals for all
models"): Brain › Models as LM Studio's own panel, per model — INFO · LOAD · INFERENCE · SERVER · MCP — plus live VITALS for every model. Pure +
tested; the service feeds it what LM Studio (`GET /api/v1/models`), the router's call log and the FEELESS
MCP server really report. Nothing here is guessed: a field the source does not give is None and the screen says so.
"""
import re

SAMPLING = ('temperature', 'top_k', 'top_p', 'min_p', 'repeat_penalty', 'presence_penalty', 'frequency_penalty', 'seed')


def _f(v):
    try:
        x = float(v)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def _q(xs, q):
    s = sorted(x for x in xs if x is not None)
    return s[min(len(s) - 1, int(q * len(s)))] if s else None


def vitals(log, inflight, key, ctx=None):
    """One model's live vitals from the router's call log (oldest → newest) + calls in flight: calls, ok %, median / p90 answer time, real
    tokens per second (completion tokens ÷ seconds, only from calls that reported usage), queue, context fill of the last prompt, errors."""
    rows = [r for r in log or [] if isinstance(r, dict) and r.get('prov') == key]
    ok = [r for r in rows if r.get('ok')]
    ms = [_f(r.get('ms')) for r in ok if _f(r.get('ms'))]
    tps = [_f(r.get('out')) / (_f(r['ms']) / 1000) for r in ok if _f(r.get('out')) and _f(r.get('ms'))]
    last = rows[-1] if rows else None
    last_in = _f((last or {}).get('in')) or _f((last or {}).get('tok'))
    bad = [r for r in rows if not r.get('ok')]
    return {'calls': len(rows), 'okPct': round(100 * len(ok) / len(rows)) if rows else None, 'medMs': _q(ms, .5), 'p90Ms': _q(ms, .9),
            'tokPerSec': round(_q(tps, .5), 1) if tps else None, 'outTok': _q([_f(r.get('out')) for r in ok if _f(r.get('out'))], .5),
            'queue': sum(1 for v in (inflight or {}).values() if isinstance(v, dict) and v.get('prov') == key),
            'ctxFill': round(min(1.0, last_in / ctx), 3) if last_in and ctx else None, 'lastIn': last_in,
            'lastOkAt': max((_f(r.get('at')) or 0 for r in ok), default=None) or None, 'errors': len(bad),
            'lastErr': (bad[-1].get('err') if bad else None), 'mindset': next((r.get('mindset') for r in reversed(rows) if r.get('mindset')), None)}


STALL_STREAK, STALL_QUIET, STALL_RECENT = 3, 600, 900   # 🩺 3+ failures in a row · no good answer for 10 min · still being asked in the last 15 min


def stall_of(stats, now):
    """🩺 A model is STALLED when it keeps failing while FEELESS keeps asking: its router state is down, STALL_STREAK+ failures in a row, no
    good answer for STALL_QUIET s (or never), and a call in the last STALL_RECENT s. → {streak, timeouts, sinceOk, why} or None. Detection only:
    the reload stays the owner's tap (Brain › Models › ⚡ Reload — ai_router.reload_model is never called by a timer)."""
    s = stats or {}
    if s.get('state') not in ('OFFLINE', 'BAD ANSWER') or int(s.get('streak') or 0) < STALL_STREAK:
        return None
    ok_at, last_at = _f(s.get('lastOkAt')), _f(s.get('lastAt'))
    if not last_at or now - last_at > STALL_RECENT or (ok_at and now - ok_at < STALL_QUIET):
        return None
    since = int(now - ok_at) if ok_at else None
    why = f"{int(s['streak'])} {'timeouts' if int(s.get('timeouts') or 0) >= int(s['streak']) else 'failures'} in a row, " + \
          (f"last good answer {since // 60}m ago" if since is not None else 'no good answer yet') + (f" ({s.get('lastErr')})" if s.get('lastErr') else '')
    return {'streak': int(s['streak']), 'timeouts': int(s.get('timeouts') or 0), 'sinceOk': since, 'why': why[:160]}


def lms_info(m):
    """LM Studio's own model row (`GET /api/v1/models`, the loaded one) → the INFO tab."""
    if not isinstance(m, dict):
        return None
    q = m.get('quantization') or {}
    cap = m.get('capabilities') or {}
    rs = cap.get('reasoning') if isinstance(cap.get('reasoning'), dict) else None
    inst = [i for i in m.get('loaded_instances') or [] if isinstance(i, dict)]
    c0 = (inst[0].get('config') or {}) if inst else {}
    return {'model': m.get('key'), 'name': m.get('display_name') or m.get('key'), 'publisher': m.get('publisher'), 'arch': m.get('architecture'),
            'format': str(m.get('format') or '').upper() or None, 'quant': q.get('name'), 'bits': q.get('bits_per_weight'),
            'sizeGb': round((m.get('size_bytes') or 0) / 1e9, 2) or None, 'params': m.get('params_string'), 'maxCtx': m.get('max_context_length'),
            'loadedCtx': c0.get('context_length'), 'parallel': c0.get('parallel'), 'instances': len(inst), 'variant': m.get('selected_variant'),
            'toolUse': bool(cap.get('trained_for_tool_use')), 'vision': bool(cap.get('vision')),
            'reasoning': {'options': list(rs.get('allowed_options') or []), 'default': rs.get('default')} if rs else None}


def lms_pick(data, model):
    """The configured model's row, else the loaded one (same rule as ai_rig.lms_row)."""
    rows = [m for m in (data or {}).get('models') or [] if isinstance(m, dict) and m.get('type') in ('llm', 'vlm', None)]
    return next((x for x in rows if x.get('key') == model), None) or next((x for x in rows if x.get('loaded_instances')), None), len(rows)


def host_of(base):
    """The endpoint as host:port (the owner-only Brain shows his own LAN address; never a key or a path secret)."""
    m = re.match(r'^(https?)://([^/]+)', str(base or ''))
    return f"{m.group(1)}://{m.group(2)}" if m else None


def mcp_view(tools, ms=None, err=None, endpoint=None):
    """FEELESS's own MCP server (feeless_mcp.py) as the models see it: reachable, round trip, every tool with its one-line job."""
    ts = [{'name': t.get('name'), 'desc': str(t.get('description') or '').split('. ')[0][:140]} for t in tools or [] if isinstance(t, dict) and t.get('name')]
    return {'ok': err is None and bool(ts), 'ms': ms, 'err': err, 'endpoint': endpoint, 'tools': ts, 'n': len(ts)}

"""🧰 COL-10 (owner 2026-11-12): every Claude session's builds + methods file themselves into the Collective stash.
Each pushed commit is one stash row in 'Builds': its subject, the method it states (body), the files it touched, and WHICH Claude made it
(the Co-Authored-By trailer: Opus, Sonnet, Fable…). Git cannot tell the owner's accounts apart, only the model each session ran, so that is
the honest tag. No emails, no author names: only the model. Pure (tests: `tests/test_claude_builds.py`); `scripts/stash-builds.py` runs it.
"""
import json
import re

SEP = '\x1e'   # one record per commit
FIELD = '\x1f'
FORMAT = f'{SEP}%H{FIELD}%ct{FIELD}%s{FIELD}%b{FIELD}%(trailers:key=Co-Authored-By,valueonly)'
CATEGORY = 'Builds'
KIND = re.compile(r'^(feat|fix|docs|perf|refactor|test|chore|style)(\([^)]*\))?!?:\s*', re.I)


def who(trailer):
    """'Claude Opus 5.5 <noreply@anthropic.com>' → 'claude-opus-5.5'. Not a Claude commit → ''."""
    for line in str(trailer or '').splitlines():
        m = re.match(r'\s*(Claude(?:\s+[A-Za-z]+)?(?:\s+[\d.]+)?)\s*<', line)
        if m:
            return re.sub(r'\s+', '-', m.group(1).strip().lower())
    return ''


def parse_log(text, files=None):
    """git log --format=FORMAT output → [{sha, at, subject, kind, method, model, files}], Claude commits only."""
    out = []
    for rec in str(text or '').split(SEP):
        parts = rec.split(FIELD)
        if len(parts) < 5:
            continue
        sha, at, subject, body, trailer = (p.strip() for p in parts[:5])
        model = who(trailer)
        if not model or not re.fullmatch(r'[0-9a-f]{40}', sha):
            continue
        method = '\n'.join(ln for ln in body.splitlines() if not re.match(r'\s*(Co-Authored-By|Signed-off-by):', ln, re.I)).strip()
        k = KIND.match(subject)
        out.append({'sha': sha, 'at': int(at or 0), 'subject': subject[:300], 'kind': (k.group(1).lower() if k else 'build'),
                    'method': method[:4000], 'model': model, 'files': list((files or {}).get(sha) or [])[:200]})
    return out


def stash_args(rec):
    """→ the collective_stash.put(...) arguments for one build, after `root`."""
    raw = json.dumps(rec, sort_keys=True).encode()
    return dict(key=f"build:{rec['sha'][:12]}", category=CATEGORY, source=rec['model'], agent=f"claude:{rec['model']}", outcome='pushed',
                title=f"{rec['model']} · {rec['subject']}", raw=raw, at=rec['at'])

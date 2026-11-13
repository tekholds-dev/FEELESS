#!/usr/bin/env python3
"""🧰 COL-10: file every Claude-made commit into the Collective stash ('Builds'). Safe to run any time: a filed commit is never filed twice.
  .venv/bin/python scripts/stash-builds.py               # the last 30 days
  .venv/bin/python scripts/stash-builds.py --rev HEAD    # just one commit (the post-commit hook)
  .venv/bin/python scripts/stash-builds.py --range A..B  # what a pull brought in (auto-pull.sh)
Prints: filed N new · M already in the stash · by model."""
import argparse
import collections
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))
import claude_builds as cb   # noqa: E402
import collective_stash as cs   # noqa: E402


def git(*a):
    return subprocess.run(['git', '-C', str(ROOT), *a], capture_output=True, text=True, check=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rev'); ap.add_argument('--range'); ap.add_argument('--since', default='30.days')
    ap.add_argument('--root', default=str(ROOT / 'backend' / 'data' / 'stash'))
    a = ap.parse_args()
    sel = ['-1', a.rev] if a.rev else [a.range] if a.range else [f'--since={a.since}']
    recs = cb.parse_log(git('log', f'--format={cb.FORMAT}', *sel))
    files = {}
    for r in recs:
        files[r['sha']] = [x for x in git('show', '--name-only', '--format=', r['sha']).splitlines() if x][:200]
    recs = cb.parse_log(git('log', f'--format={cb.FORMAT}', *sel), files)
    new = 0; by = collections.Counter()
    for r in recs:
        if cs.put(pathlib.Path(a.root), **cb.stash_args(r)):
            new += 1; by[r['model']] += 1
    print(f"filed {new} new · {len(recs) - new} already in the stash · " + (', '.join(f'{m} {n}' for m, n in by.most_common()) or 'nothing new'))


if __name__ == '__main__':
    main()

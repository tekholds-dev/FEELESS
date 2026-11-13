---
name: feeless-ship
description: Ship a finished FEELESS change the same way on every Claude account — gate on real exit codes, push to main from the gate snapshot, update HANDOFF/history, file to the stash, report. Use whenever work is ready to push.
---
# Ship it (FEELESS)

1. **Done check** (CLAUDE.md §2): UI seen in the browser with a screenshot · new mechanic has a test · money code got `/code-review` or `/security-review`.
2. **Commit** in the main tree, only your files (never `.emergent/recordings/`, `scripts/trim-mongo-caches.py`). Message ends with `Co-Authored-By: <your model> <noreply@anthropic.com>`.
3. **Backend changed?** Make sure no build/proof is running (a push restarts every service on the owner's machine).
4. **Gate + push** from the snapshot, in the background, nothing else running:
   ```bash
   cd .claude/worktrees/gate && git fetch -q .. && git checkout -q --detach <sha> && git push origin HEAD:main
   ```
   If the gate worktree is missing, run the 3 gate commands in CLAUDE.md §5 with `set -e`, then `git push origin main`.
5. **Stash:** `.venv/bin/python scripts/stash-builds.py --rev HEAD` (never files twice).
6. **HANDOFF:** update or delete the card; a done card → one line in `docs/history/<YYYY-MM>.md`. Update the "% left" line.
7. **Report:** Done · Not verified · Judgment calls · Proposed · % left. Money work ends with "ready to test" for the owner.

---
name: Post-merge setup hook
description: The frontend has no committed dependency lockfile, so merge setup must install without generating one.
---

Use a registered, non-interactive post-merge script for this project. The frontend dependency install must use Yarn with `--no-lockfile`; the repository does not commit a lockfile and merge setup should not create one as a side effect.

**Why:** The merge system runs the hook with stdin closed, and an absent hook previously caused merged tasks to fail before workflow reconciliation.

**How to apply:** Keep the hook fail-fast and idempotent, install with `--non-interactive --ignore-scripts --no-lockfile`, then run the frontend production build within the configured timeout.
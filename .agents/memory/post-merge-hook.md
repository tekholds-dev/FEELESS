---
name: Post-merge setup hook
description: The frontend has no committed dependency lockfile, so merge setup must install without generating one.
---

Use a registered, non-interactive post-merge script for this project. The frontend dependency install must use Yarn with `--no-lockfile`; the repository does not commit a lockfile and merge setup should not create one as a side effect.

**Why:** The merge system runs the hook with stdin closed, and an absent hook previously caused merged tasks to fail before workflow reconciliation.

**How to apply:** Keep the hook fail-fast and idempotent, install with `--non-interactive --ignore-scripts --no-lockfile`, then run the frontend production build within the configured timeout. Pin dependencies when the package firewall lacks the newest transitive release.

The frontend pins `framer-motion` and its `motion-dom` resolution to the cached 13.4.1 release because the package firewall returned 404 for 13.4.2 during merge setup.

**Why:** There is no committed lockfile, so a caret range can resolve to an unavailable transitive tarball and fail an otherwise healthy post-merge build.

**How to apply:** When merge setup fails in dependency fetching, inspect the exact resolved package before changing the hook; prefer a known-good exact version and matching Yarn resolution.
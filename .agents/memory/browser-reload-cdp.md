---
name: Browser reload CDP behavior
description: Chromium can invalidate a page DevTools Protocol session during a full reload.
---

A dependency-free Chromium smoke test should reconnect to the fresh page target after calling `Page.reload`; evaluating immediately on the old CDP session can fail even when the browser reload succeeds.

**Why:** The page target may report that it navigated or closed while the application itself continues loading normally.

**How to apply:** Treat full-reload checks as two phases: issue the reload, reconnect to the page target, then wait for the post-reload DOM.
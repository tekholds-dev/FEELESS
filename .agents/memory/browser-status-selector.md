---
name: Browser status selector scope
description: Browser checks must distinguish multiple simultaneous live status regions.
---

When a page can show more than one `role="status"` region at once, browser checks should select the specific status component they are asserting rather than relying on the first matching element.

**Why:** Filter explanations and action confirmations can legitimately coexist, so a generic first-status lookup can report a false failure even when the UI is correct.

**How to apply:** Give each independently asserted live message a stable class or test id and scope browser assertions to that region.
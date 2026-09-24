---
name: Mobile collection verification
description: Reliable browser verification for selectable, filterable mobile galleries.
---

When validating a filterable gallery in a real browser, wait for the React update after each click before reading counts or state. Reset to the unfiltered view before selecting a named fixture so the fixture is guaranteed to be visible.

**Why:** A rapid sequence can read the previous render, and a named card may be intentionally absent from the currently selected filter. Both cases can look like product failures when they are test-order errors.

**How to apply:** Use settled browser actions for filter assertions and viewport measurements; explicitly return to “All” before testing selection, preview updates, or featured actions.
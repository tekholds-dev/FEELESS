---
name: Landing page test harness
description: The frontend Jest setup needs a virtual router mock for isolated routed-component tests.
---

Focused routed-component tests should provide a virtual `react-router-dom` mock with only the hooks and link primitives they use rather than importing the installed router package directly.

**Why:** The installed router package is available to the application build but Jest's resolver cannot load its ESM export in this frontend setup, so direct test imports fail before the test suite runs.

**How to apply:** Keep isolated page/component tests independent of router internals; mock `Link` to an anchor and provide minimal `useSearchParams` or `useNavigate` behavior as needed.
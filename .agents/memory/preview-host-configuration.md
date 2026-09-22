---
name: Preview host configuration
description: CRA/CRACO must accept Replit's proxied hostname and bind the preview server correctly.
---

The React preview server must bind to `0.0.0.0` on port 5000 and set the webpack dev server `allowedHosts` option to `all`; otherwise Replit's proxied preview can show `Invalid Host header` even when localhost works.

**Why:** Replit renders the app through a host name different from the local request host, and CRA's default host validation rejects that proxy host.

**How to apply:** Keep the host and allowed-host settings in the CRACO dev-server configuration and start script, then restart the configured webview workflow after changing them.
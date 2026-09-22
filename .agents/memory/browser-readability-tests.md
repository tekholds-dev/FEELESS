---
name: Browser readability test CSS
description: Jest/jsdom does not resolve the trade readability custom-property calc values like a real browser.
---

When testing class-driven trade readability in Jest/jsdom, assert the rendered scale class and inspect the loaded production CSS rule through CSSOM. `getComputedStyle` may retain the base font size even when the browser-facing selector and custom property are correct. Portaled dialogs do not inherit a scale class from the terminal root, so their active scale must be propagated through an inherited body variable or a class on the dialog itself.

**Why:** jsdom's CSS engine does not fully evaluate the multiplication of CSS custom properties used by the trade stylesheet.

**How to apply:** Keep interaction and localStorage assertions on the rendered Terminal, inject the production stylesheet for the test, and use CSSOM assertions for large and extra-large declarations.

**Why:** Radix dialog content is portaled outside the terminal root, which otherwise leaves approval surfaces at the default size even when the workspace readouts scale.

**How to apply:** Test the portaled dialog separately from the workspace and verify its narrow-width constraints as CSSOM rules rather than relying on jsdom layout.
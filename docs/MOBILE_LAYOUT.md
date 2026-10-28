# Mobile and Duo layout contract

Owner requirement, 2026-10-28: every page must fit the usable browser screen on mobile and Duo, across orientation and browser chrome changes. All controls must remain available. The matrix is a test requirement, not a device-name allowlist.

## Exact owner-supplied Duo reference

These are the CSS viewport sizes already supplied for this user's “iPhone Duo”. They are not a universal Apple hardware specification or independently measured physical screen dimensions. DPR is 3. Safari in this environment reports no viewport segments; never require that API to enable the layout.

| State | Width × height, CSS px | Expected behavior |
|---|---|---|
| Folded upright | 466 × 678 | Single-column phone flow |
| Folded sideways (rotated reference) | 678 × 466 | Compact landscape split where usable |
| Unfolded wide | 890 × 626 | Chart left, desk right; split near center |
| Unfolded upright | 626 × 890 | Chart above independently scrollable desk |

Browser chrome, keyboard, display scaling and split windows can produce other usable sizes. Do not hard-code these numbers as layout heights. Do not multiply them by DPR for CSS geometry.

## Rules for every mobile feature

1. Fit available space using flex/grid with min-width/min-height:0. Use dvh with fallback and safe-area env insets; for Safari shell fitting, observe visualViewport resize/scroll plus window resize/orientationchange, coalesced with requestAnimationFrame. Clean up on unmount. Preserve native pinch zoom.
2. Orientation comes from the usable layout dimensions, not the device name. Preserve selected coin, interval, dock tab and swap state across rotation. Existing useDuoFloor detects coarse-pointer wide devices/sideways phones; keep ordinary desktop behavior intact.
3. Scroll the content panes, not the entire fixed cockpit. Avoid a fixed minimum height larger than the viewport. Avoid overflow:hidden ancestors that can be programmatically scrolled by focus; use overflow:clip where no scrolling is intended.
4. Safe areas, browser bars, keyboard and standalone/home-screen mode must never cover close/navigation/trading controls. iPhone browser fullscreen behavior is platform-controlled; CSS fitting must work without requestFullscreen.
5. Toolbars are swipeable rows with readable labels and usable touch targets (32px minimum; prefer 40–44px). No missing controls: collapse secondary navigation behind a clearly labeled toggle, preserve keyboard/focus access and allow scrolling.
6. Canvas charts resize from their allocated container. Do not subtract guessed toolbar heights or let a descendant overwrite the intended chart size token. Keep live state intact on viewport changes.
7. Verify ordinary 360/390px phones; folded 466×678 and 678×466; open 890×626 and 626×890; intermediate widths; shortened Safari viewport; keyboard; day/night; reduced motion/lite; desktop regression. Capture evidence and label emulation versus physical-device testing.

## This delivery

Agents only: fitted HQ shell, safe-area padding, visualViewport listeners with cleanup, chart-height allocation, rotation, scroll containment and HQ-controls toggle. Landscape chart gets the entire left half; the money/navigation strip lives above the right desk. Portrait prioritizes the chart above the dock. Other tabs must adopt/verify this contract in M01; they were not all modified here. Physical Safari fullscreen/keyboard verification is still OWNER work.

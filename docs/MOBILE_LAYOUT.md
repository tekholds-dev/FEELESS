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

## Duo floors — the OFFICIAL Duo / fold / phone view (owner 2026-10-29: "the official Duo view should be in MD's so no f-ups, bugs, bad containments")

Every app that runs full-screen on a Duo, fold, tablet or phone uses ONE shell: `styles/duoFloor.css` (`dfl-*`). Today: the Trenches floor
(`components/terminal/DuoFloor.jsx`, modes trench · pump) and HQ › Agents (`AgentCockpit` duo branch, `.dfl.dfl-agents`). A new floor copies this, never invents a layout.

| When (`lib/duo.js`) | Layout (`.dfl` class) | Grid |
|---|---|---|
| Duo unfolded wide 890×626 · tablet wide · phone sideways (`useDuoFloor().wide`) | `is-wide` | `rail 56px · chart = 50% − rail · side = 50%` → the split sits EXACTLY on the crease (445 px) |
| Duo unfolded upright 626×890 · tablet upright (`useDuoFloor().on && !wide`) | `is-up` | `chart 58fr · side 42fr · act auto` |
| Phone upright < 600 px wide, incl. Duo folded 466×678 (`usePhoneUp()`, Agents) | `is-up` | same as above — one screen, chart first, never a multi-screen scroll |
| `is-swap` (⇄ / ⇅, saved per device) | either | the two halves trade places |

Rules (each one is a bug we already had):
1. **Portal to `<body>`**, `position: fixed`, own z-layer (Trenches 45 under dialogs · Agents 4500 above the HQ pop-out 4000, under the Brain drawer 5200 / AI panel 9000).
   NEVER fit a floor by retouching a host (`.hqp` classes, `cc-shell` overflow) — that was the Agents "bad containment" (2026-10-28 build).
2. **Height = the visible viewport**: `100dvh`; floors inside Safari chrome follow `visualViewport` (resize + scroll; skip while pinch-zoomed) via `--adf-vh` / `--adf-top`.
   Safe areas = `env(safe-area-inset-*)` padding on `.dfl`. `body.duo-floor-on` hides the site chrome (FeeCat widget, Duo bar, mobile tab bar) while a floor is open.
3. **The chart height is MEASURED, never guessed**: a ResizeObserver on `.dfl-plot` sets `--dfl-h` = its height − the measured heads/toolbars; `.chart-area` + `.candle-canvas`
   read `--dfl-h`. No descendant may set its own chart height. Short landscape (≤ 520 px tall) drops secondary blocks above the candles (Agents: the P&L block — the ride bar keeps it).
4. **Only the panes scroll** (`.dfl-pane`, `overscroll-behavior: contain`); the shell, rail, bar and tabs never move. Use `overflow: clip`, not `hidden`, on anything focus could scroll.
5. **Every control stays**: secondary nav lives in the side half (Agents: money strip + nav lead it; the nav's pick opens in the DESK tab). An exit (`←` / `☰ HQ`) is always on screen; ☰ HQ steps the floor aside and ⤢ brings it back.
6. **State survives a turn / fold**: the open tab, the coin, the interval and swap are remembered (`feeless.duo*`, `feeless.ack.*`), so a rotation re-renders the same screen.
7. **Tabs** = a locked `.dfl-tabs` row (≥ 38 px tall); every button ≥ 32 px (rail 40 px), `data-tip`, hover / active / focus-visible.
8. **Proof before done**: screenshot 890×626, 626×890, 678×466, 466×678 and 390×844 in the Browser pane (`/dev/hq?touch` for Agents) and check: crease at 50 %, no page
   side-scroll, the chart filling its half, the pane scrolling alone, no control clipped. Physical Safari (toolbars, keyboard, home-screen) stays OWNER verification.

## This delivery

Agents only: fitted HQ shell, safe-area padding, visualViewport listeners with cleanup, chart-height allocation, rotation, scroll containment and HQ-controls toggle. Landscape chart gets the entire left half; the money/navigation strip lives above the right desk. Portrait prioritizes the chart above the dock. Other tabs must adopt/verify this contract in M01; they were not all modified here. Physical Safari fullscreen/keyboard verification is still OWNER work.

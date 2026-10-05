// 📖 Every Fuse word in plain language — ONE list, read by the Lab card plan, the cycle picker and the FuseGuide pop-up.
// Mirrors backend arena_prime.PHASES / CYCLE_MODES and fuse.STYLES: change them together.
export const CYCLE_OPTS = [['steady', '➡ Steady', 'Every reshuffle swaps a weak coin for the best gated runner'],
  ['classic', '⚓→🔥 Classic', 'Rounds go anchor (into majors) → degen (runners) → anchor → mixed'], ['adaptive', '🧠 Adaptive', 'Losing → swaps into a major (protect) · +5% → a runner (press) · flat → mixed'],
  ['safe', '⚓⇄⚖ Safe', 'Anchor round ⇄ mixed round'], ['press', '🔥⇄⚖ Press', 'Degen round ⇄ mixed round'],
  ['rescue', '🛟 Rescue', '🛡 Safest run (3 majors + 1 new major) ⇄ ⚖ Breakeven (1 high-volume pool + 3 high-volume runners). Any card ≤ −50% switches here by itself.'],
  ['auto', '🤖 Auto', 'The engine picks each round: deep red → breakeven · red → safest · +5% → degen · flat → mixed']];

export const SHAPE_WORDS = [
  ['anchor', '⚓ Anchor', '3 majors + 1 new major', 'Rest in the coins with the deepest pools — still MOVING ones: anchors are ranked by what they do today, never by name.'],
  ['degen', '🔥 Degen', '1 major + 3 runners', 'Press: most of the card rides gated runners that are pumping now.'],
  ['mixed', '⚖ Mixed', '2 majors + a new major + a runner', 'Half safe, half chase.'],
  ['safest', '🛡 Safest', '3 majors + 1 new major', 'The protect shape a losing card falls back to.'],
  ['breakeven', '⚖ Breakeven', '1 high-volume pool + 3 high-volume runners', 'Picks by flow, not score — the fastest way back to even after a bad run.'],
];

export const CLOCK_WORDS = [
  ['Round clock', 'How often the card may change coins (5m · 15m · 1h · 6h · 12h · 24h). Faster = more swaps and more fees; protection (TP / SL / rug) checks every tick on any clock.'],
  ['Patience', 'A coin is only rotated after losing this many rounds in a row AND being held long enough — noise never churns the card.'],
  ['TP / SL', 'Take profit / stop loss per coin, as a % from YOUR entry. Fees are never mixed into it.'],
  ['❄ Freeze', 'This coin is never rotated or stopped.'],
  ['🏇 Ride', 'A coin up big is held (no TP, no rotation) and sold only once it falls the trail % off its new high.'],
  ['⚡ Instant swap', 'A coin at −X% is swapped for a NEW coin at once instead of waiting for the bell.'],
  ['Floor', 'If the whole card falls this far, everything goes into its anchor and the card is re-dealt.'],
];
export const STOP_WORDS = [['✂ Sell', 'A coin at its stop is sold to SOL.'], ['🅿 Park', 'Sold to SOL, then bought back at entry once buyers return.'], ['❄ Hold', 'Never sold on a stop (the card floor still protects).'], ['⇄ Replace', 'Swapped for the best coin of its kind.']];

export const STRATEGY_WORDS = [
  ['yield', '💧 Yield hunter', 'Pools trading a lot for their size (pool APR). Holders earn price moves, not the APR.'],
  ['momentum', '🚀 Momentum', 'What moved up in 24h. Rides trends, can reverse.'],
  ['steady', '🛡 Steady', 'Deep pools, small swings.'],
  ['degen', '🎲 Degen', 'APR + momentum, no care for calm.'],
  ['dip', '📉 Buy the dip', 'Down on the day, buyers back (1h green, 55%+ buys). A coin still dumping scores only 30%.'],
  ['meta', '💳 Pump meta', 'DEX-paid profiles / boosts + momentum + real flow.'],
];

export const COIN_WORDS = [
  ['⚓ Anchors', 'Real majors (BTC, ETH, SOL, JUP, PUMP, BONK, WIF, POPCAT, TRUMP, PENGU, FARTCOIN …) + big new majors (≥ $5M, ≥ $300K pool, ≥ 1 day). Ranked by turnover + 1h/6h/24h moves + buyers. Stables and staked SOL never anchor.'],
  ['🚀 New majors', 'Young coins that arrived big: ≤ 14 days, $800K–$50M, real volume, deep pool.'],
  ['🏃 Runners', 'Launchpad coins that pass EVERY safety gate (holders, insiders, dev, creator, flow, volume). Fail closed: unscanned = out.'],
  ['📉 Dip buy', 'A gated coin down 25%+ on the day that is bouncing: 5m green, 1h no longer falling, 55%+ buys, buys speeding up.'],
  ['💳 Dex paid', 'Its team paid for the DexScreener profile or boosts — somebody stands behind it. A bonus, never a pass on the safety gates.'],
  ['🔔 Bond run', 'Pre-bond at 90%+ of the curve with every box ticked (buys, volume, holders, clean creator).'],
  ['☠ Retired', 'A strategy whose typical arena run AND outlier-proof average are below 0 leaves the trader rails. It gets one test run a day and returns by itself when it wins.'],
];

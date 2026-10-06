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
  ['trench', '🗑 Trench', '1 major + 1 pool + 1–2 trench breakouts', 'Fresh launches (≤6h) that broke $20K with a real crowd: ≥400 holders, 250+ trades an hour, 55%+ buys, clean holders, clean creator, mint + freeze revoked. The riskiest coins on the site — max 2 per card.'],
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

// 🗣 Trench talk: the words traders use, and what FEELESS actually measures for each. Entry setups mirror arena_prime.ENTRY_SETUPS.
export const TRENCH_WORDS = [
  ['Meta', 'The theme the market is paying for right now (AI agents, animals, a news story). Coins inside the meta get the volume; the same coin a week later may get none. FEELESS learns new words from launches and chat every few minutes.'],
  ['Tek (tech)', 'A coin whose pitch is what it DOES (a tool, a bot, a protocol) instead of a joke. Tek coins are judged the same way here: holders, flow and creator first — a pitch is not a safety check.'],
  ['Runner', 'A launch coin that is moving now with real buyers. Here it also has to pass every safety gate (holders, insiders, dev, creator, flow, volume). Unscanned = out.'],
  ['Trench', 'The first hours of a launch. Highest reward and highest risk on the site: most trench coins go to zero.'],
  ['Bonding / graduating', 'A pump coin trades on a curve until enough is bought; then it “graduates” to a normal pool. 🔔 Bond run = 90%+ of the way with every box ticked.'],
  ['Jeet', 'A holder who sells the first small pump. Lots of jeets = buys under 50% and a chart that cannot hold a green hour.'],
  ['Cabal / bundle', 'One group holding many wallets. Bundled = several wallets bought in the same block at launch. Our gates cap bundled wallets and insider share.'],
  ['Sniper', 'A bot that buys in the first seconds. 🎯 Snipers out = they have sold, so their bags no longer hang over the chart.'],
  ['Holder zones', 'Who holds the supply: top-10 share, insiders, the dev. Under 20% top-10 = spread out · 20–30% = watch · above that only passes while the big holders are not selling.'],
  ['Dev sold / CTO', 'The creator dumped. A CTO (community takeover) is holders carrying on without them — treated as a new, unproven coin here.'],
  ['Rug', 'The pool’s liquidity is pulled or the supply is dumped. 🚨 Rug shield sells when a pool loses half of what it had at entry — it limits the loss, it cannot undo it.'],
  ['🧹 Liquidity sweep & reclaim', 'Price is pushed under a level where stops sit (the flush), then buyers take it straight back. Read here as: red on the hour, green in the last 5 min, 58%+ buys.'],
  ['🚀 Breakout', 'Up on the hour and still pushing with volume speeding up. A coin already up more than 150% in the hour is not counted — that move is done.'],
  ['🧲 Pullback / FVG', 'A fast move leaves a gap on the chart (a fair value gap). The pullback into it, with buyers still in charge, is the classic second entry. Read here as: strong hour, small 5-min dip, 52%+ buys.'],
  ['House money', 'Once a coin doubles, selling your cost leaves a position that cannot lose your own money. The card’s 💰 skim does this in pieces.'],
  ['Market cap vs pool', 'Market cap is price × supply. What you can actually sell into is the POOL. A $2M coin with a $10K pool cannot be sold for $2M of anything.'],
];

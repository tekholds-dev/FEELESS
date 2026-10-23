// 🎭 Prompt Studio fixture (tests + /dev/brain): G4 with a red record and three habits, OSSY healthy with PROGRESSIVE applied, NEXA's YES calls.
const set = (s, label, tag, dials, text, why) => ({ set: s, label, tag, dials, text, why });
const SETS = name => [
  set('elite', 'ELITE', 'few trades · all clean', { speed: 35, patience: 80, risk: 25, discipline: 95 }, `ELITE MINDSET — ${name}, the family's sniper. Few trades, all clean: if fewer than three facts agree (trend, buyers, pool), WAIT. Set TP / SL before the buy and size only what the pool can take back.`, 'Quality over count: the card pays on the few setups that work.'),
  set('degen', 'DEGEN TRENCH', 'germ floor · trench laws', { speed: 75, patience: 55, risk: 70, discipline: 60 }, `DEGEN TRENCH MINDSET — ${name}, born in the trenches, ruled by the laws: a coin under 15 min old loses, the bonding curve is the worst bucket, graduated under $30K is the one setup that pays. The germ floor is the base before the pump: above it with buyers over 55 % and a higher low, you send it.`, 'Argues from the measured trench theory, in trench slang.'),
  set('progressive', 'PROGRESSIVE', 'rush in · ride green · cut red', { speed: 85, patience: 85, risk: 55, discipline: 80 }, `PROGRESSIVE MINDSET — ${name}: quick in, patient in profit. RUSH the entry once the move is confirmed (buyers leading, a higher low, volume rising). Once green, SLOW DOWN: trail the peak, let +10 % become +30 %, trim a third at +25 % and ride the rest.`, 'Your words: quick, but patient when in profit — rush is good.'),
  set('tuned', 'AUTO-TUNED', '3 habits fixed from the record', { speed: 50, patience: 70, risk: 35, discipline: 100 }, `AUTO-TUNED for ${name} from your real record: 76 trades, 17 % won. Fix these habits first: (1) Once a trade is +10 %, your stop goes to break-even. (2) Cut a loser at the line you set BEFORE the buy. (3) A clean trade gets at least 15 minutes.`, 'rides winners back to red: 21 of 76 trades peaked +10 % and closed under +2 %; lets losers run: average loss −11.2 % vs average win +4.1 %'),
];
const layers = (job, studio) => [{ k: 'job', label: 'Seat prompt', chars: job * 4, tok: job, text: 'You and one partner model take TURNS on ONE seat of a small real-money Solana trench card…' },
  { k: 'identity', label: 'Identity', chars: 420, tok: 105, text: 'Your name is G4 — the lead trench analyst…', note: 'chat only' },
  { k: 'brain', label: 'Coin reads (brain)', chars: 9200, tok: 2300, text: '# FEELESS brain…', note: 'background reads' },
  { k: 'studio', label: 'Applied mindset', chars: studio * 4, tok: studio, text: studio ? '🎭 MINDSET … PROGRESSIVE MINDSET — OSSY: quick in, patient in profit…' : '', ...(studio ? {} : { note: 'none applied' }) }];
export const STUDIO = {
  dials: ['speed', 'patience', 'risk', 'discipline'], at: 0,
  models: [
    { key: 'lan', name: 'G4', state: 'ONLINE', model: 'qwen/qwen3-4b-2507', ctx: 8704, layers: layers(2600, 0), active: null,
      record: { n: 76, wonPct: 17, avgPct: -4.7, avgWin: 4.1, avgLoss: -11.2, medHeld: 11, quickN: 48, quickWonPct: 12, gaveN: 21, calls: 30, answerPct: 100, medMs: 15600 },
      fixes: [{ key: 'giveback', title: 'rides winners back to red', evidence: '21 of 76 trades peaked +10 % and closed under +2 %', rule: 'Once a trade is +10 %, your stop goes to break-even.' },
        { key: 'bleed', title: 'lets losers run', evidence: 'average loss −11.2 % vs average win +4.1 %', rule: 'Cut a loser at the line you set BEFORE the buy.' },
        { key: 'jumpy', title: 'bails inside 15 min', evidence: '48 of 76 trades closed under 15 min, 12 % of those won', rule: 'A clean trade gets at least 15 minutes.' }],
      sets: SETS('G4') },
    { key: 'local', name: 'OSSY', state: 'ONLINE', model: 'openai/gpt-oss-20b', ctx: 16384, layers: layers(2600, 190),
      active: { set: 'progressive', text: 'PROGRESSIVE MINDSET — OSSY…', at: Date.now() / 1000 - 5400, by: 'owner', edited: false, since: { n: 4, wonPct: 50, avgPct: 2.6 } },
      record: { n: 100, wonPct: 26, avgPct: -0.4, medHeld: 22, calls: 30, answerPct: 100, medMs: 51200 }, fixes: [], sets: SETS('OSSY') },
    { key: 'win', name: 'NEXA', state: 'ONLINE', model: 'Ministral-3-3B', ctx: 4096, layers: [{ k: 'job', label: 'Desk calls (YES / NO · HOLD / SELL)', chars: 380, tok: 95, text: "You trade FeeCat's paper desk…" }, { k: 'studio', label: 'Applied mindset', chars: 0, tok: 0, text: '', note: 'none applied' }],
      active: null, record: { n: 0, yesN: 42, yesRight: 45, yesTypical: -1.2 },
      fixes: [{ key: 'yes', title: 'its YES calls lose', evidence: '42 YES calls graded: 45 % right, typical -1.2 %', rule: 'YES only when graduated, cap under $30K, buyers over 55 % and the pool over $10K.' }],
      sets: SETS('NEXA').map(s => ({ ...s, text: s.text.slice(0, 300) })) },
  ],
};

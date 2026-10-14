// 🫀 THE VITAL BOARD (decision panel › Live): every vital the agents read on a coin as ONE clickable tile — the reading, a tone (good · watch ·
// bad · unknown), the line it is judged against, WHO reads it and WHAT it does. Built from the kernel candidate's `vit` (no fetch). Pure.
const n = v => (v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v));
const pctW = (v, d = 0) => (n(v) == null ? '—' : `${n(v) > 0 && d ? '+' : ''}${n(v).toFixed(d ? 1 : 0)}%`);
const money = v => (n(v) == null ? '—' : n(v) >= 1e6 ? `$${(n(v) / 1e6).toFixed(1)}M` : n(v) >= 1e3 ? `$${(n(v) / 1e3).toFixed(1)}K` : `$${Math.round(n(v))}`);
const tone3 = (v, ok, mid, low = true) => (n(v) == null ? 'unk' : low ? (n(v) < ok ? 'good' : n(v) < mid ? 'watch' : 'bad') : (n(v) >= ok ? 'good' : n(v) >= mid ? 'watch' : 'bad'));

export const VITAL_GROUPS = [['holders', '🧩 HOLDERS'], ['flow', '🌊 FLOW'], ['launch', '🚀 LAUNCH'], ['chart', '📈 CHART'], ['story', '📖 STORY'], ['rules', '🎓 YOUR RULES'], ['social', '📣 SOCIALS']];
const BAD_CHART = /BOT LADDER|DOWNTREND|LIQUIDITY FAILURE|COLLAPS|DISTRIBUTION|DATA INVALID|FAILED BREAKOUT|PARABOLIC/;
const GOOD_CHART = /UPTREND|BREAKOUT|PULLBACK|RECLAIM|BASE|COMPRESSION|EARLY/;
const SOC_TONE = { STRONG: 'good', OK: 'good', THIN: 'watch', NONE: 'watch', CONFLICT: 'bad', UNREAD: 'unk' };

// 🫀 every reading the panel already has, so the board is never blank (owner, 2026-10-14: "agent decision don't show shit"): the kernel
// candidate's own numbers + the held position, overlaid by the server's `vit` when it sends one. Pure.
export function mergedVit(c, pos) {
  const p = pos || {}; const th = p.thesis || {};
  const base = { d5: c?.move5m, buy: c?.buyShare, liqUsd: c?.liq ?? p.liq, top10: p.top10, chart: p.structure || th.structure, entry: th.call, entryWhy: th.why,
    dq: p.data?.state, phase: p.li?.phase, cls: p.li?.cls, press: p.li?.press };
  const out = { ...Object.fromEntries(Object.entries(base).filter(([, x]) => x != null)), ...(c?.vit || {}) };
  return out;
}

export function vitalTiles(c, pos) {
  const v = mergedVit(c, pos); const out = [];
  const add = (group, key, icon, label, value, tone, line, who, effect, extra) => out.push({ group, key, icon, label, value, tone, line, who, effect, ...extra });
  add('holders', 'top10', '🐋', 'TOP-10', pctW(v.top10), tone3(v.top10, 20, 30), 'under 20% good · 30%+ heavy', '🔍 Sherlock · ⚖ Devil', 'ranks +6 under 20% · −8 at 30%+ · over 40% the agents never buy');
  add('holders', 'bundled', '📦', 'BUNDLED', v.bundled == null ? '—' : `${v.bundled}`, tone3(v.bundled, 1, 3), '0 clean · 3+ = bundled launch', '⚖ Devil', '3+ bundles count as botted; a bundle wallet dumping = rug radar exit');
  add('holders', 'snipers', '🎯', 'SNIPERS', v.snipers == null ? '—' : `${v.snipers}`, tone3(v.snipers, 4, 8), 'under 4 clean · 8+ heavy', '⚖ Devil', '8+ snipers = heavy sniper launch (warning, ranks down)');
  add('holders', 'dev', '👤', 'DEV HOLDS', pctW(v.dev), tone3(v.dev, 5, 10), 'under 5% · 10%+ = risk', '⚖ Devil · 🛡 Warden', 'dev selling now = the one Devil hard line in trench mode');
  add('holders', 'holders', '👥', 'HOLDERS', v.holders == null ? '—' : Math.round(v.holders).toLocaleString(), tone3(v.holders, 300, 100, false), '300+ crowd · under 100 thin', '📊 Tally', 'context — a growing crowd ranks up');
  add('flow', 'd5', '⚡', '5 MIN', pctW(v.d5, 1), n(v.d5) == null ? 'unk' : n(v.d5) <= -8 ? 'bad' : n(v.d5) > 15 ? 'watch' : n(v.d5) > 0 ? 'good' : 'watch', '−8% = hard no · +15% = chasing', '⏱ Trigger', 'falling 8% in 5 min = never bought · a +40% candle (young) / +15% (older) = skipped');
  add('flow', 'buy', '🟢', 'BUYERS', pctW(v.buy), tone3(v.buy, 55, 50, false), '55%+ buyers lead · under 50% sellers', '⏱ Trigger · ☠ Reaper', 'sellers taking over banks a green seat (R4f)');
  if (v.vol1h == null && v.liqUsd != null) add('flow', 'pool', '💧', 'POOL', money(v.liqUsd), tone3(v.liqUsd, 20000, 8000, false), '$20K+ deep · under $8K = the keeper refuses', '🛡 Warden · 📮 Courier', 'a pool under half its entry depth = Reaper sells (R1)');
  add('flow', 'vol1h', '💧', '1H VOLUME', money(v.vol1h), tone3(v.vol1h, 20000, 5000, false), `${v.tx1h ? `${Math.round(v.tx1h)} trades · ` : ''}$20K+ busy`, '📊 Tally', 'volume velocity is a rank part; no trades in 5 min = dead (hard no)');
  add('flow', 'organic', '🌱', 'ORGANIC', pctW(v.organic), tone3(v.organic, 10, 5, false), '10%+ real buyers · under 5% bots', '🔍 Sherlock', 'shown + judged — Jupiter reads most Pump coins 2–3%, so it never blocks');
  add('launch', 'rug', '☠', 'RUG METER', v.rug == null ? '—' : `${v.rug}`, tone3(v.rug, 35, 50), 'under 35 · 50+ = hard no', '⚖ Devil', 'rug ≥ 50 is never bought; ≥ 65 on a held coin = out');
  add('launch', 'phase', '🌀', 'PHASE', v.phase || '—', !v.phase ? 'unk' : /DISTRIBUTION|COLLAPSE|CROWD FOMO/.test(v.phase) ? 'bad' : /PRE-FOMO|EARLY/.test(v.phase) ? 'good' : 'watch', 'PRE-FOMO / EARLY good · CROWD FOMO late', '🔍 Sherlock', 'DISTRIBUTION / COLLAPSE = hard no · early ranks up · crowd ranks down');
  add('launch', 'cls', '🕵', 'LAUNCH', v.cls || '—', !v.cls ? 'unk' : v.cls === 'NORMAL' ? 'good' : 'bad', 'NORMAL · or bundled / insider / snipers', '⚖ Devil · 🛡 Warden', 'a cluster holding 20%+ halves the seat');
  add('launch', 'press', '🩸', 'EARLY SELLING', v.press || '—', !v.press ? 'unk' : v.press === 'HIGH' ? 'bad' : v.press === 'WATCH' ? 'watch' : 'good', 'NONE · WATCH · HIGH', '☠ Reaper', 'HIGH = never bought, held coin sold (R4e)');
  add('chart', 'chart', '📈', 'STRUCTURE', v.chart || '—', !v.chart || v.chart === 'UNKNOWN' ? 'unk' : BAD_CHART.test(v.chart) ? 'bad' : GOOD_CHART.test(v.chart) ? 'good' : 'watch', 'read from the real 1-minute candles', '⏱ Trigger', 'bot ladder / downtrend / liquidity failure = no buy');
  add('chart', 'entry', '🎯', 'ENTRY CALL', v.entry || '—', !v.entry ? 'unk' : v.entry === 'ENTER NOW' ? 'good' : v.entry === 'SKIP' ? 'bad' : 'watch', v.entryWhy || 'ENTER NOW · WAIT · SKIP', '⏱ Trigger', '🎯 Chart says go: anything but ENTER NOW waits');
  add('chart', 'dq', '🧪', 'DATA', v.dq || '—', !v.dq ? 'unk' : /TRUSTED|USABLE/.test(v.dq) ? 'good' : /INVALID|MALFORMED|STALE|INCONSISTENT|UNTRUSTED/.test(v.dq) ? 'bad' : 'watch', 'is the chart real candles?', '📊 Tally', 'invalid data = WAIT FOR DATA, never a structure read');
  if (v.narr || v.wave || v.callers || v.swarm) {
    add('story', 'narr', '📖', 'NARRATIVE', v.narr || 'none', 'unk', 'what its name rides', '🔍 Sherlock', 'a narrative is learned by its own record (no starting belief)');
    add('story', 'wave', '🌊', 'WAVE', v.wave === 'lead' ? 'ORIGINAL' : v.wave === 'copy' ? 'COPYCAT' : '—', v.wave === 'lead' ? 'good' : v.wave === 'copy' ? 'watch' : 'unk', 'the first coin of a ticker wave vs its copies', '🔍 Sherlock', 'your 🪞 Copycat rule can flag / rank / skip copies');
    add('story', 'callers', '📣', 'PUMP CALLERS', v.callers == null ? '—' : `${v.callers}${v.swarm ? ' · swarm' : ''}`, v.swarm ? 'bad' : n(v.callers) > 0 ? 'good' : 'unk', 'real callers vs a copy-paste swarm', '⚖ Devil', 'a bot swarm is a Devil warning');
  }
  Object.entries(v.taught || {}).forEach(([k, why]) => add('rules', `rule:${k}`, '🎓', k.toUpperCase(), 'HIT', 'bad', why, '🎓 your rule', 'set it below — off · 👀 flag · ⬇ rank down · ✋ skip', { rule: k }));
  const s = v.soc;
  add('social', 'soc', '📣', 'SOCIALS', s?.grade || 'UNREAD', SOC_TONE[s?.grade || 'UNREAD'], s?.line || 'not researched yet', '🔍 Sherlock · ⚖ Devil', 'a CA mismatch / different X = Devil warning; never a veto by itself', { soc: s || null });
  return out;
}

// how many tiles of each tone — the board's one-line headline
export function vitalScore(tiles) {
  const t = { good: 0, watch: 0, bad: 0, unk: 0 }; (tiles || []).forEach(x => { t[x.tone] = (t[x.tone] || 0) + 1; });
  const known = t.good + t.watch + t.bad;
  return { ...t, known, word: !known ? 'NOT READ YET' : t.bad >= 3 ? 'RED FLAGS' : t.bad ? 'MIXED' : t.watch > t.good ? 'WATCH' : 'CLEAN' };
}

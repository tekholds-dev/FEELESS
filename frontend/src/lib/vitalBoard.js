// 🫀 THE VITAL BOARD (decision panel › Live): every vital the agents read on a coin as ONE clickable tile — the reading, a tone (good · watch ·
// bad · unknown), the line it is judged against, WHO reads it and WHAT it does. Built from the kernel candidate's `vit` (no fetch). Pure.
const n = v => (v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v));
const pctW = (v, d = 0) => (n(v) == null ? '—' : `${n(v) > 0 && d ? '+' : ''}${n(v).toFixed(d ? 1 : 0)}%`);
const money = v => (n(v) == null ? '—' : n(v) >= 1e6 ? `$${(n(v) / 1e6).toFixed(1)}M` : n(v) >= 1e3 ? `$${(n(v) / 1e3).toFixed(1)}K` : `$${Math.round(n(v))}`);
const tone3 = (v, ok, mid, low = true) => (n(v) == null ? 'unk' : low ? (n(v) < ok ? 'good' : n(v) < mid ? 'watch' : 'bad') : (n(v) >= ok ? 'good' : n(v) >= mid ? 'watch' : 'bad'));

export const VITAL_GROUPS = [['drain', '🩸 EXIT RISK'], ['holders', '🧩 HOLDERS'], ['flow', '🌊 FLOW'], ['launch', '🚀 LAUNCH'], ['germ', '🦠 GERM vs 🔫 GUN'], ['chart', '📈 CHART'], ['story', '📖 STORY'], ['rules', '🎓 YOUR RULES']];
const clamp01 = x => Math.max(0, Math.min(1, x));
const DRAIN_TONE = { CLEAR: 'good', WATCH: 'watch', DRAIN: 'bad' };
const TAPE_TONE = { BUYERS: 'good', BALANCED: 'watch', PEAK: 'watch', SELLERS: 'bad', THIN: 'unk' };
const BAD_CHART = /BOT LADDER|DOWNTREND|LIQUIDITY FAILURE|COLLAPS|DISTRIBUTION|DATA INVALID|FAILED BREAKOUT|PARABOLIC/;
const GOOD_CHART = /UPTREND|BREAKOUT|PULLBACK|RECLAIM|BASE|COMPRESSION|EARLY/;

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
  // 🩸 EXIT RISK first: will the chart be drained? (server `vit.drain` {s, st, xl, hd, lq, w} · `vit.tape` [state, $ bought, $ sold] · `vit.odds` [rug %, n, base %, feature])
  const dr = v.drain || {}; const tp = Array.isArray(v.tape) ? v.tape : null; const od = Array.isArray(v.odds) ? v.odds : null;
  add('drain', 'drain', '🩸', 'DRAIN', dr.st ? `${dr.st} ${dr.s ?? 0}` : '—', DRAIN_TONE[dr.st] || 'unk', (dr.w || []).join(' · ') || 'holders leaving · pool draining · sellers · heavy bags', '☠ Reaper · ⚖ Devil',
    'DRAIN + a MOVING part (holders / pool / sellers / a big wallet dumping) = Reaper sells an agent seat at once (R4d)', { meter: dr.st ? clamp01((dr.s || 0) / 100) : null, bad: true });
  add('drain', 'xl', '🐋', 'EXIT LIQ', n(dr.xl) == null ? '—' : `${n(dr.xl).toFixed(1)}× pool`, n(dr.xl) == null ? 'unk' : dr.xl < 1 ? 'good' : dr.xl < 3 ? 'watch' : 'bad', "the top-10 holders' $ bag ÷ the pool — 3× = they can sell three pools' worth",
    '☠ Reaper', 'a heavy bag alone never sells; with holders leaving or sellers on the tape it does', { meter: n(dr.xl) == null ? null : clamp01(dr.xl / 4), bad: true });
  add('drain', 'hd', '👥', 'HOLDERS Δ', pctW(dr.hd, 1), n(dr.hd) == null ? 'unk' : dr.hd > -2 ? 'good' : dr.hd > -5 ? 'watch' : 'bad', 'holders over Tally\'s window · −2% leaving · −5% running', '📊 Tally · ☠ Reaper', 'a moving part of the drain read', { meter: n(dr.hd) == null ? null : clamp01(-dr.hd / 8), bad: true });
  add('drain', 'lq', '💧', 'POOL Δ', pctW(dr.lq, 1), n(dr.lq) == null ? 'unk' : dr.lq > -10 ? 'good' : dr.lq > -25 ? 'watch' : 'bad', 'pool over Tally\'s window · −10% leaking · −25% draining', '📊 Tally · ☠ Reaper', 'a pool under half its entry depth = sold (R1); draining = a moving drain part', { meter: n(dr.lq) == null ? null : clamp01(-dr.lq / 40), bad: true });
  const tb = tp ? n(tp[1]) || 0 : 0; const ts = tp ? n(tp[2]) || 0 : 0;
  add('drain', 'tape', '🌊', 'TAPE 90s', tp ? tp[0] || '—' : '—', tp ? TAPE_TONE[tp[0]] || 'unk' : 'unk', tp ? `${money(tb)} bought · ${money(ts)} sold in the last 90s` : 'the live buy / sell tape (read for held + top coins)',
    '⏱ Trigger · ☠ Reaper', 'SELLERS = no buy + a green seat banked (R4f) · PEAK = no buy at the top', { split: tp && tb + ts > 0 ? tb / (tb + ts) : null });
  add('drain', 'odds', '🔮', 'RUG ODDS', od ? `${od[0]}%` : '—', !od ? 'unk' : od[0] <= od[2] ? 'good' : od[0] <= od[2] * 1.6 ? 'watch' : 'bad',
    od ? `${od[0]}% of ${Number(od[1]).toLocaleString()} coins like it (${String(od[3]).replace(':', ' ')}) fell 50%+ within the hour · all coins ${od[2]}%` : 'measured from the trench brain\'s judged coins (needs 40 like it)',
    '🧠 trench brain', 'a record, never a promise — the bucket that says the MOST about this coin', { meter: od ? clamp01(od[0] / 100) : null, bad: true });
  add('holders', 'top10', '🐋', 'TOP-10', pctW(v.top10), tone3(v.top10, 20, 30), 'under 20% good · 30%+ heavy', '🔍 Sherlock · ⚖ Devil', 'ranks +6 under 20% · −8 at 30%+ · over 40% the agents never buy');
  add('holders', 'bundled', '📦', 'BUNDLED', v.bundled == null ? '—' : `${v.bundled}`, tone3(v.bundled, 1, 3), '0 clean · 3+ = bundled launch', '⚖ Devil', '3+ bundles count as botted; a bundle wallet dumping = rug radar exit');
  add('holders', 'snipers', '🎯', 'SNIPERS', v.snipers == null ? '—' : `${v.snipers}`, tone3(v.snipers, 4, 8), 'under 4 clean · 8+ heavy', '⚖ Devil', '8+ snipers = heavy sniper launch (warning, ranks down)');
  add('holders', 'dev', '👤', 'DEV HOLDS', pctW(v.dev), tone3(v.dev, 5, 10), 'under 5% · 10%+ = risk', '⚖ Devil · 🛡 Warden', 'dev selling now = the one Devil hard line in trench mode');
  add('flow', 'd5', '⚡', '5 MIN', pctW(v.d5, 1), n(v.d5) == null ? 'unk' : n(v.d5) <= -8 ? 'bad' : n(v.d5) > 15 ? 'watch' : n(v.d5) > 0 ? 'good' : 'watch', '−8% = hard no · +15% = chasing', '⏱ Trigger', 'falling 8% in 5 min = never bought · a +40% candle (young) / +15% (older) = skipped');
  add('flow', 'buy', '🟢', 'BUYERS', pctW(v.buy), tone3(v.buy, 55, 50, false), '55%+ buyers lead · under 50% sellers', '⏱ Trigger · ☠ Reaper', 'sellers taking over banks a green seat (R4f)');
  if (v.vol1h == null && v.liqUsd != null) add('flow', 'pool', '💧', 'POOL', money(v.liqUsd), tone3(v.liqUsd, 20000, 8000, false), '$20K+ deep · under $8K = the keeper refuses', '🛡 Warden · 📮 Courier', 'a pool under half its entry depth = Reaper sells (R1)');
  add('flow', 'vol1h', '💧', '1H VOLUME', money(v.vol1h), tone3(v.vol1h, 20000, 5000, false), `${v.tx1h ? `${Math.round(v.tx1h)} trades · ` : ''}$20K+ busy`, '📊 Tally', 'volume velocity is a rank part; no trades in 5 min = dead (hard no)');
  add('launch', 'rug', '☠', 'RUG METER', v.rug == null ? '—' : `${v.rug}`, tone3(v.rug, 35, 50), 'under 35 · 50+ = hard no', '⚖ Devil', 'rug ≥ 50 is never bought; ≥ 65 on a held coin = out');
  add('launch', 'phase', '🌀', 'PHASE', v.phase || '—', !v.phase ? 'unk' : /DISTRIBUTION|COLLAPSE|CROWD FOMO/.test(v.phase) ? 'bad' : /PRE-FOMO|EARLY/.test(v.phase) ? 'good' : 'watch', 'PRE-FOMO / EARLY good · CROWD FOMO late', '🔍 Sherlock', 'DISTRIBUTION / COLLAPSE = hard no · early ranks up · crowd ranks down');
  add('launch', 'cls', '🕵', 'LAUNCH', v.cls || '—', !v.cls ? 'unk' : v.cls === 'NORMAL' ? 'good' : 'bad', 'NORMAL · or bundled / insider / snipers', '⚖ Devil · 🛡 Warden', 'a cluster holding 20%+ halves the seat');
  add('launch', 'press', '🩸', 'EARLY SELLING', v.press || '—', !v.press ? 'unk' : v.press === 'HIGH' ? 'bad' : v.press === 'WATCH' ? 'watch' : 'good', 'NONE · WATCH · HIGH', '☠ Reaper', 'HIGH = never bought, held coin sold (R4e)');
  // 🦠 the owner's germ method: buy near the germ floor (the base of the coin's biggest run), never at the gun line (the high it must break)
  const gd = n(v.germD) ?? n(v.germ5D); const hd = n(v.hiD);
  add('germ', 'germ', '🦠', 'GERM FLOOR', gd == null ? (v.germ || '—') : `${gd.toFixed(1)}% above`, gd == null ? 'unk' : gd < 0 ? 'bad' : gd <= 15 ? 'good' : gd <= 25 ? 'watch' : 'bad',
    `1m ${v.germ || '—'} · 5m ${v.germ5 || '—'} · within 15% of the floor = the buy zone`, '⏱ Trigger · 🛡 Warden', 'on the germ ranks up (1m + 5m = confirmed ×1.25) · past the line = half seat or wait · lost = no buy', { meter: gd == null ? null : clamp01(1 - Math.max(0, gd) / 30), germ: true });
  add('germ', 'gun', '🔫', 'GUN LINE', hd == null ? '—' : `${hd.toFixed(1)}% under`, hd == null ? 'unk' : hd <= 4 ? 'bad' : hd <= 10 ? 'watch' : 'good',
    'how far under its high — within 4% = buying the gun line', '⏱ Trigger', 'at the gun line with a hot 5 min = WAIT (never READY on a breakout chase)', { meter: hd == null ? null : clamp01(1 - hd / 30), bad: true });
  add('chart', 'chart', '📈', 'STRUCTURE', v.chart || '—', !v.chart || v.chart === 'UNKNOWN' ? 'unk' : BAD_CHART.test(v.chart) ? 'bad' : GOOD_CHART.test(v.chart) ? 'good' : 'watch', 'read from the real 1-minute candles', '⏱ Trigger', 'bot ladder / downtrend / liquidity failure = no buy');
  add('chart', 'entry', '🎯', 'ENTRY CALL', v.entry || '—', !v.entry ? 'unk' : v.entry === 'ENTER NOW' ? 'good' : v.entry === 'SKIP' ? 'bad' : 'watch', v.entryWhy || 'ENTER NOW · WAIT · SKIP', '⏱ Trigger', '🎯 Chart says go: anything but ENTER NOW waits');
  if (v.narr || v.wave || v.callers || v.swarm) {
    add('story', 'narr', '📖', 'NARRATIVE', v.narr || 'none', 'unk', 'what its name rides', '🔍 Sherlock', 'a narrative is learned by its own record (no starting belief)');
    add('story', 'wave', '🌊', 'WAVE', v.wave === 'lead' ? 'ORIGINAL' : v.wave === 'copy' ? 'COPYCAT' : '—', v.wave === 'lead' ? 'good' : v.wave === 'copy' ? 'watch' : 'unk', 'the first coin of a ticker wave vs its copies', '🔍 Sherlock', 'your 🪞 Copycat rule can flag / rank / skip copies');
    add('story', 'callers', '📣', 'PUMP CALLERS', v.callers == null ? '—' : `${v.callers}${v.swarm ? ' · swarm' : ''}`, v.swarm ? 'bad' : n(v.callers) > 0 ? 'good' : 'unk', 'real callers vs a copy-paste swarm', '⚖ Devil', 'a bot swarm is a Devil warning');
  }
  Object.entries(v.taught || {}).forEach(([k, why]) => add('rules', `rule:${k}`, '🎓', k.toUpperCase(), 'HIT', 'bad', why, '🎓 your rule', 'set it below — off · 👀 flag · ⬇ rank down · ✋ skip', { rule: k }));
  return out;
}

// how many tiles of each tone — the board's one-line headline
export function vitalScore(tiles) {
  const t = { good: 0, watch: 0, bad: 0, unk: 0 }; (tiles || []).forEach(x => { t[x.tone] = (t[x.tone] || 0) + 1; });
  const known = t.good + t.watch + t.bad;
  return { ...t, known, word: !known ? 'NOT READ YET' : t.bad >= 3 ? 'RED FLAGS' : t.bad ? 'MIXED' : t.watch > t.good ? 'WATCH' : 'CLEAN' };
}

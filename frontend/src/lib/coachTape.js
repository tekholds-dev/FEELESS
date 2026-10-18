// 🎬 the real trade tape + 👑 the coach — pure reads of the one Agents payload (`office.tradeTape`, `office.coach`). Nothing here fetches.
const num = v => (v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v));
export const signedPct = v => (num(v) == null ? '—' : `${num(v) >= 0 ? '+' : ''}${Math.abs(num(v)) >= 100 ? num(v).toFixed(0) : num(v).toFixed(1)}%`);
export const money2 = v => (num(v) == null ? '—' : `${num(v) < 0 ? '−' : ''}$${Math.abs(num(v)).toFixed(Math.abs(num(v)) < 10 ? 2 : 0)}`);
export const agoWord = (at, now = Date.now() / 1000) => { if (!at) return '—'; const s = Math.max(0, Math.round(now - at)); return s < 60 ? `${s}s` : s < 3600 ? `${Math.round(s / 60)}m` : s < 86400 ? `${(s / 3600).toFixed(1)}h` : `${Math.round(s / 86400)}d`; };

export const secWord = v => (num(v) == null ? '—' : num(v) < 90 ? `${num(v).toFixed(0)}s` : `${(num(v) / 60).toFixed(1)}m`);

// one trade → what its card shows. tone: up / dn / open. Every word is from the row; a missing piece stays out.
export function tradeCard(r, now = Date.now() / 1000) {
  const bk = r?.state === 'part' ? r?.banked || null : null;   // 💰 a trim so far: the sold coins against what THEY cost (never the whole buy)
  const res = r?.result || (bk ? { pct: bk.pct, usd: bk.usd } : null); const pct = num(res?.pct);
  const tone = r?.open && !bk ? 'is-open' : pct == null ? 'is-flat' : pct > 0 ? 'is-up' : 'is-dn';
  const w = r?.why || {};
  const why = [w.tag ? String(w.tag).replace('🤖 agents · ', '') : null, w.structure, w.rule, w.phase ? `phase ${w.phase}` : null, w.size != null ? `size ×${w.size}` : null].filter(Boolean);
  const b = r?.buy || {};
  return { key: `${r?.mint}-${r?.at}`, mint: r?.mint, sym: r?.sym || '?', tone, ago: agoWord(r?.at, now), yours: r?.who === 'you', models: r?.who === 'models',
    head: r?.state === 'part' ? (bk ? `◐ PART SOLD · banked ${money2(bk.usd)} (${signedPct(bk.pct)})` : '◐ PART SOLD') : r?.open ? '🟢 STILL HELD' : pct == null ? 'SOLD' : `SOLD ${signedPct(pct)}`,
    verdict: r?.open ? (r?.state === 'part' ? 'PART' : 'HELD') : pct == null ? 'SOLD' : pct > 0.5 ? 'WIN' : pct < -0.5 ? 'LOSS' : 'FLAT', pct: pct == null ? null : signedPct(pct),
    held: num(res?.heldMin) == null ? null : num(res.heldMin) < 60 ? `${num(res.heldMin).toFixed(0)}m` : `${(num(res.heldMin) / 60).toFixed(1)}h`,
    inUsd: num(b.usd) != null ? money2(b.usd) : null, rule: res?.rule ? String(res.rule).split(' · ')[0].slice(0, 34) : null, state: r?.state || (r?.open ? 'held' : 'sold'), usd: res?.usd != null ? money2(res.usd) : null,
    buy: [b.usd != null ? `${money2(b.usd)} in` : null, num(b.slipPct) != null ? `filled ${signedPct(b.slipPct)} vs market` : null, num(b.waitSec) != null ? `sent ${secWord(b.waitSec)} after the call` : null, num(b.landSec) != null ? `landed ${num(b.landSec).toFixed(0)}s` : null].filter(Boolean),
    slow: num(b.waitSec) != null && num(b.waitSec) + (num(b.landSec) || 0) > 60,
    buySig: b.sig || null, slipBad: num(b.slipPct) != null && num(b.slipPct) > 2.5,
    why, src: (w.src || []).slice(0, 4),
    ai: r?.ai ? { stance: r.ai.stance || 'NEUTRAL', text: r.ai.summary || '', label: r.ai.label || 'AI', flags: (r.ai.risk_flags || []).slice(0, 3) } : null,
    sells: (r?.sells || []).map(s => ({ sig: s.sig, text: [s.usd != null ? `${money2(s.usd)} out` : null, s.why].filter(Boolean).join(' · ') })),
    exit: res ? [res.rule, num(res.heldMin) != null ? `held ${num(res.heldMin) < 60 ? `${num(res.heldMin).toFixed(0)}m` : `${(num(res.heldMin) / 60).toFixed(1)}h`}` : null, num(res.peak) != null ? `peak ${signedPct(res.peak)}` : null].filter(Boolean) : [],
    judge: r?.judge ? (r.judge.kind === 'yours' ? `📝 your trade — notes only${r.judge.cause && r.judge.cause !== 'variance' ? ` · ${String(r.judge.cause).replace(/_/g, ' ')}` : ''}`
    : [r.judge.kind === 'win' ? '✅ win' : r.judge.lossClass || r.judge.cause || 'loss', r.judge.desk ? `on ${r.judge.desk}` : null, r.judge.change || r.judge.why].filter(Boolean).join(' · ')) : null };
}

// 🏁 the recent results, newest first: one pill per CLOSED trade (win / loss / flat) + the tally (owner, 2026-10-16: "needs to show recent
// wins / losses — I don't know if I caught Macca on a win")
export function recentResults(rows, n = 12) {
  const done = (rows || []).filter(r => !r.open && num(r?.result?.pct) != null).slice(0, n)
    .map(r => { const pct = num(r.result.pct); return { key: `${r.mint}-${r.at}`, mint: r.mint, sym: r.sym || '?', pct, usd: num(r.result.usd), yours: r.who === 'you', models: r.who === 'models', tone: pct > 0.5 ? 'is-up' : pct < -0.5 ? 'is-dn' : 'is-flat' }; });
  const won = done.filter(x => x.tone === 'is-up').length; const lost = done.filter(x => x.tone === 'is-dn').length;
  const usd = done.reduce((a, x) => a + (x.usd || 0), 0);
  // 💵 EARNINGS by who traded: every closed trade on the tape in the last 24h, yours apart from the agents' (realized $, fees apart)
  const day = (rows || []).filter(r => !r.open && num(r?.result?.pct) != null && (!r.at || Date.now() / 1000 - r.at <= 86400));
  const side = who => { const xs = day.filter(r => (r.who || 'agents') === who); const u = xs.filter(r => num(r.result.usd) != null);
    return { n: xs.length, won: xs.filter(r => num(r.result.pct) > 0.5).length, lost: xs.filter(r => num(r.result.pct) < -0.5).length, usd: u.length ? u.reduce((a, r) => a + num(r.result.usd), 0) : null }; };
  return { list: done, won, lost, usd: done.some(x => x.usd != null) ? usd : null, you: side('you'), agents: side('agents'), models: side('models') };
}

// 📸 the entry snapshot as short chips (only what was read)
export function snapChips(sn) {
  if (!sn) return [];
  const c = [];
  if (sn.chart) c.push(['📈', String(sn.chart).toLowerCase(), '']);
  if (num(sn.germ) != null) c.push(['🦠', `${num(sn.germ) >= 0 ? '+' : ''}${num(sn.germ).toFixed(0)}% off germ`, num(sn.germ) >= 0 && num(sn.germ) <= 15 ? 'is-good' : 'is-warn']);
  if (num(sn.buyers) != null) c.push(['🌊', `${num(sn.buyers).toFixed(0)}% buyers`, num(sn.buyers) >= 55 ? 'is-good' : num(sn.buyers) < 45 ? 'is-bad' : '']);
  if (num(sn.offHigh) != null) c.push(['🔫', `${num(sn.offHigh).toFixed(0)}% under high`, num(sn.offHigh) <= 4 ? 'is-warn' : '']);
  if (num(sn.d5) != null) c.push(['⚡', `${signedPct(sn.d5)} 5m`, num(sn.d5) >= 12 ? 'is-warn' : '']);
  return c;
}

export const tapeLine = st => (st ? [`${st.n} closed`, st.n ? `${st.won} won` : null, st.medPct != null ? `typical ${signedPct(st.medPct)}` : null, st.open ? `${st.open} open` : null,
  st.medSlipPct != null ? `fills ${signedPct(st.medSlipPct)} vs market` : null].filter(Boolean).join(' · ') : 'no real agent trade yet');

// {key: {n, med, won}} → rows for a graded list (sources / exit rules), worst first; bar = how bad / good the typical result is (±40% = full)
export function gradeRows(rec, min = 1) {
  return Object.entries(rec || {}).filter(([, v]) => (v?.n || 0) >= min).map(([k, v]) => ({ k, n: v.n, med: num(v.med), won: v.won, fill: Math.max(0.04, Math.min(1, Math.abs(num(v.med) || 0) / 40)), tone: (num(v.med) || 0) > 0 ? 'is-up' : (num(v.med) || 0) < 0 ? 'is-dn' : 'is-flat' }))
    .sort((a, b) => (a.med ?? 0) - (b.med ?? 0));
}

const BY = { owner: ['👑', 'YOU'], ai: ['🧠', 'AI'], judge: ['👨‍⚖️', 'JUDGE'] };
export function coachRows(coach, now = Date.now() / 1000) {
  return ((coach || {}).rules || []).map(r => { const [icon, who] = BY[r.by] || ['·', String(r.by || '').toUpperCase()]; const left = num(r.left) ?? (r.until ? r.until - now : null);
    return { id: r.id, key: r.key, by: r.by, icon, who, points: num(r.points), words: r.words || r.key, why: r.why || '', sym: r.sym || null,
      left: left == null ? null : left >= 3600 ? `${(left / 3600).toFixed(0)}h left` : `${Math.max(1, Math.round(left / 60))}m left`,
      canBack: r.by === 'ai' && r.id != null, canKill: r.id != null, grade: ruleGrade(r.grade) }; });
}
// held seats the creator may pull with a reason (never a seat still buying, never an open one)
export const pullable = seats => (seats || []).filter(s => !s.open && s.mint && s.pair && !s.buying);

// ⏱ the three clocks of a real fill as meters: call → send (the keeper's queue), send → land (the chain), fill vs the call's price.
// `fill` = share of the bar (60s / 60s / 5% = full); tone: ok under a third, mid under two thirds, bad past it.
export function speedMeters(st) {
  const row = (k, label, v, full, word, tip) => (num(v) == null ? null : { k, label, word, tip, fill: Math.max(0.03, Math.min(1, Math.abs(num(v)) / full)),
    tone: Math.abs(num(v)) / full < 1 / 3 ? 'is-ok' : Math.abs(num(v)) / full < 2 / 3 ? 'is-mid' : 'is-bad' });
  return [row('wait', 'CALL → SENT', st?.medWaitSec, 60, secWord(st?.medWaitSec), 'Typical time between the agents allowing a buy and the keeper sending it. The keeper sends one order at a time and waits for each to confirm.'),
    row('land', 'SENT → LANDED', st?.medLandSec, 60, secWord(st?.medLandSec), 'Typical time the chain took to confirm the buy after it was sent.'),
    row('slip', 'FILL vs CALL PRICE', st?.medSlipPct, 5, signedPct(st?.medSlipPct), 'Typical fill price against the market price when the buy was called (above = paid more).')].filter(Boolean);
}

// 📏 a directive's own record → one chip. right = the coins it ranked down typically fell · wrong = they rose 3%+ · else still open.
export function ruleGrade(g) {
  if (!g || !g.n) return null;
  const v = g.verdict === 'right' ? ['✅', 'is-up', 'holds'] : g.verdict === 'wrong' ? ['⚠', 'is-dn', 'ranks winners down'] : ['👀', 'is-flat', 'judging'];
  return { icon: v[0], tone: v[1], word: `${v[2]} · ${signedPct(g.med)} after · n ${g.n}`, tip: `Coins this rule ranked down, 30 minutes later: typical ${signedPct(g.med)}, ${g.up} of ${g.n} went up. A rule is judged from 10 coins.` };
}

// 🧪 "exit on the thesis, not the stop", replayed on the real trades → one honest line.
export function lineWord(l) {
  if (!l || !l.n || !l.actual) return null;
  const b = (l.lines || []).find(x => x.x === l.best) || {};
  return { tone: l.verdict === 'pays' ? 'is-up' : 'is-flat', head: l.verdict === 'pays' ? 'A TIGHTER EXIT LINE PAYS' : 'TIGHTER EXIT LINE · NOT PROVEN',
    text: [`cut at −${l.best}%: average ${signedPct(b.avg)} vs ${signedPct(l.actual.avg)} real`, `${b.won} vs ${l.actual.won} winners (it throws away ${b.cutWinners})`,
      `${l.gapped} of ${l.n} were already past −15% at the first look — no exit line saves those`].join(' · ') };
}


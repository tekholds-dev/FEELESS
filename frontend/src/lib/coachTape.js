// 🎬 the real trade tape + 👑 the coach — pure reads of the one Agents payload (`office.tradeTape`, `office.coach`). Nothing here fetches.
const num = v => (v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v));
export const signedPct = v => (num(v) == null ? '—' : `${num(v) >= 0 ? '+' : ''}${Math.abs(num(v)) >= 100 ? num(v).toFixed(0) : num(v).toFixed(1)}%`);
export const money2 = v => (num(v) == null ? '—' : `${num(v) < 0 ? '−' : ''}$${Math.abs(num(v)).toFixed(Math.abs(num(v)) < 10 ? 2 : 0)}`);
export const agoWord = (at, now = Date.now() / 1000) => { if (!at) return '—'; const s = Math.max(0, Math.round(now - at)); return s < 60 ? `${s}s` : s < 3600 ? `${Math.round(s / 60)}m` : s < 86400 ? `${(s / 3600).toFixed(1)}h` : `${Math.round(s / 86400)}d`; };

// one trade → what its card shows. tone: up / dn / open. Every word is from the row; a missing piece stays out.
export function tradeCard(r, now = Date.now() / 1000) {
  const res = r?.result || null; const pct = num(res?.pct);
  const tone = r?.open ? 'is-open' : pct == null ? 'is-flat' : pct > 0 ? 'is-up' : 'is-dn';
  const w = r?.why || {};
  const why = [w.tag ? String(w.tag).replace('🤖 agents · ', '') : null, w.structure, w.rule, w.phase ? `phase ${w.phase}` : null, w.size != null ? `size ×${w.size}` : null].filter(Boolean);
  const b = r?.buy || {};
  return { key: `${r?.mint}-${r?.at}`, mint: r?.mint, sym: r?.sym || '?', tone, ago: agoWord(r?.at, now),
    head: r?.open ? 'OPEN' : pct == null ? 'CLOSED' : signedPct(pct), usd: res?.usd != null ? money2(res.usd) : null,
    buy: [b.usd != null ? `${money2(b.usd)} in` : null, num(b.slipPct) != null ? `filled ${signedPct(b.slipPct)} vs market` : null, num(b.landSec) != null ? `landed ${num(b.landSec).toFixed(0)}s` : null].filter(Boolean),
    buySig: b.sig || null, slipBad: num(b.slipPct) != null && num(b.slipPct) > 2.5,
    why, src: (w.src || []).slice(0, 4),
    ai: r?.ai ? { stance: r.ai.stance || 'NEUTRAL', text: r.ai.summary || '', label: r.ai.label || 'AI', flags: (r.ai.risk_flags || []).slice(0, 3) } : null,
    sells: (r?.sells || []).map(s => ({ sig: s.sig, text: [s.usd != null ? `${money2(s.usd)} out` : null, s.why].filter(Boolean).join(' · ') })),
    exit: res ? [res.rule, num(res.heldMin) != null ? `held ${num(res.heldMin) < 60 ? `${num(res.heldMin).toFixed(0)}m` : `${(num(res.heldMin) / 60).toFixed(1)}h`}` : null, num(res.peak) != null ? `peak ${signedPct(res.peak)}` : null].filter(Boolean) : [],
    judge: r?.judge ? [r.judge.kind === 'win' ? '✅ win' : r.judge.lossClass || r.judge.cause || 'loss', r.judge.desk ? `on ${r.judge.desk}` : null, r.judge.change || r.judge.why].filter(Boolean).join(' · ') : null };
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
      canBack: r.by === 'ai' && r.id != null, canKill: r.id != null }; });
}
// held seats the creator may pull with a reason (never a seat still buying, never an open one)
export const pullable = seats => (seats || []).filter(s => !s.open && s.mint && s.pair && !s.buying);

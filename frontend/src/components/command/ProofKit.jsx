import React, { useEffect, useMemo, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { Ic3 } from '../../lib/icon3d';
import '../../styles/proofKit.css';

// 🧰 THREE TOOLS IN EVERY PROOF FOLDER (owner 2026-11-05). Each one reads the agent's own filed proofs, so a number here is always something that really happened. Too few proofs says so; nothing is ever filled in.
const pct = v => `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(1)}%`;
const avg = a => (a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0);
const count = (list, key) => { const m = {}; list.forEach(x => { const k = key(x); if (k) m[k] = (m[k] || 0) + 1; }); return Object.entries(m).sort((a, b) => b[1] - a[1]); };
const bars = (rows, unit = '') => { const top = Math.max(1, ...rows.map(r => r[1])); return rows.slice(0, 5).map(([l, n]) => ({ l, v: `${n}${unit}`, part: n / top })); };

export function powTools(folders = []) {
  const done = folders.filter(f => f.pnlPct != null);
  const mins = f => (f.soldAt && f.boughtAt ? (f.soldAt - f.boughtAt) / 60 : null);
  const hold = [['Under 5 min', 0, 5], ['5 to 15 min', 5, 15], ['15 to 30 min', 15, 30], ['30 min or more', 30, 1e9]].map(([l, lo, hi]) => { const rows = done.filter(f => mins(f) != null && mins(f) >= lo && mins(f) < hi); const a = avg(rows.map(f => f.pnlPct)); return rows.length ? { l: `${l} · ${rows.length}`, v: pct(a), part: Math.min(1, Math.abs(a) / 30), tone: a >= 0 ? 'up' : 'dn' } : null; }).filter(Boolean);
  const kind = f => { const w = String(f.why || '').toLowerCase(); return w.startsWith('stop') ? 'Its stop' : w.startsWith('take') || w.includes('tp') ? 'Its take profit' : w.includes('watcher') ? 'The watcher' : w.startsWith('trail') ? 'Its trail' : 'Other'; };
  const groups = {}; done.forEach(f => { (groups[kind(f)] = groups[kind(f)] || []).push(f.pnlPct); });
  const exits = Object.entries(groups).sort((a, b) => b[1].length - a[1].length).map(([l, r]) => { const a = avg(r); return { l: `${l} · ${r.length}`, v: pct(a), part: Math.min(1, Math.abs(a) / 30), tone: a >= 0 ? 'up' : 'dn' }; });
  const duel = [0, 1].map(i => { const r = done.filter(f => Number(f.rMind) === i); const w = r.filter(f => f.pnlPct > 0).length; return { l: `Mind ${'AB'[i]} · ${r.length} picked`, v: r.length ? `${Math.round((100 * w) / r.length)}% won` : 'None yet', part: r.length ? w / r.length : 0, tone: 'up' }; });
  return [{ ic: '⏳', t: 'What pays', say: 'Its real result by how long it held', rows: hold, need: 'Shows after its first closed trade', ask: 'What hold time has paid best in your PoW folders, and why?' },
    { ic: '🚪', t: 'How it gets out', say: 'What closed each trade, and how that went', rows: exits, need: 'Shows after its first closed trade', ask: 'Look at how your PoW trades closed. Which exit costs you most?' },
    { ic: '🥊', t: 'Mind against mind', say: 'Whose pick it bought, and who won more', rows: duel.some(d => d.part || d.v !== 'None yet') ? duel : [], need: 'Shows once a mind has picked a trade', ask: 'Which of your two minds picks better coins? Show the numbers.' }];
}
export function popTools(folders = []) {
  const calls = folders.flatMap(f => f.calls || []); const traded = folders.filter(f => !f.noTrade).length;
  const sides = ['long', 'short'].map(s => ({ l: s === 'long' ? 'Long' : 'Short', v: `${calls.filter(c => c.side === s).length}`, part: calls.length ? calls.filter(c => c.side === s).length / calls.length : 0, tone: s === 'long' ? 'up' : 'dn' }));
  const lev = calls.length ? avg(calls.map(c => Number(c.lev) || 0)) : 0; const sl = calls.length ? avg(calls.map(c => Number(c.sl) || 0)) : 0;
  const sources = folders.flatMap(f => Object.values(f.sources || {}).flat()).filter(s => s && s.ok);
  const dev = sources.length ? avg(sources.map(s => Math.abs(Number(s.devBps) || 0))) : 0;
  return [{ ic: '📉', t: 'Its market calls', say: `${folders.length} rounds, ${traded} went on to a paper trade`, rows: calls.length ? [...sides, ...bars(count(calls, c => c.market))] : [], need: 'Shows after its first PoP', ask: 'file a perp' },
    { ic: '🎚', t: 'Its risk', say: 'What it asks for on an average call', rows: calls.length ? [{ l: 'Leverage', v: `${lev.toFixed(1)}x`, part: Math.min(1, lev / 10), tone: lev > 5 ? 'dn' : 'up' }, { l: 'Stop distance', v: `${sl.toFixed(1)}%`, part: Math.min(1, sl / 5) }, { l: 'A stop at this leverage costs', v: `${(lev * sl).toFixed(1)}%`, part: Math.min(1, (lev * sl) / 25), tone: 'dn' }] : [], need: 'Shows after its first PoP', ask: 'Is your leverage too high for your stops? Show the numbers.' },
    { ic: '🌐', t: 'Its price sources', say: 'How close each live source was', rows: sources.length ? [{ l: 'Live sources read', v: `${sources.length}`, part: 1, tone: 'up' }, { l: 'Average gap from the mid price', v: `${dev.toFixed(1)} bps`, part: Math.min(1, dev / 25), tone: dev > 10 ? 'dn' : 'up' }, ...bars(count(sources, s => s.site)).slice(0, 3)] : [], need: 'Shows after its first PoP with live sources', ask: 'Which of your price sources disagree the most, and what does that mean?' }];
}
export function pobTools(folders = []) {
  const calls = folders.flatMap(f => f.calls || []); const picks = calls.flatMap(c => c.picks || []);
  const byMind = [0, 1].map(i => { const r = calls.filter(c => c.mind === i).flatMap(c => c.picks || []); const a = avg(r.map(p => Number(p.confidence) || 0)); return { l: `Mind ${'AB'[i]} · ${r.length} picks`, v: r.length ? `${Math.round(a)}% sure` : 'None yet', part: a / 100, tone: 'up' }; });
  const agreed = folders.flatMap(f => f.agreed || []).length;
  const rate = picks.length ? (2 * agreed) / picks.length : 0;
  return [{ ic: '🎯', t: 'How sure it is', say: 'Average confidence, mind by mind', rows: picks.length ? byMind : [], need: 'Shows after its first PoB', ask: 'file a pob best picks tonight' },
    { ic: '🤝', t: 'Where both agree', say: 'Picks both minds made without seeing each other', rows: picks.length ? [{ l: 'Both picked the same', v: `${agreed}`, part: Math.min(1, rate), tone: 'up' }, { l: 'All picks made', v: `${picks.length}`, part: 1 }] : [], need: 'Shows after its first PoB', ask: 'Which picks did both your minds agree on, and how did they do?' },
    { ic: '🌐', t: 'Sites it trusts', say: 'Where its bids read from', rows: bars(count(folders.flatMap(f => f.sites || []), s => s), ' reads'), need: 'Shows after its first PoB', ask: 'Which sites gave you the most useful facts for your bids?' }];
}
export function pocTools(folders = []) {
  const shots = folders.flatMap(f => f.shots || []); const posted = folders.filter(f => f.result?.link); const earned = posted.reduce((a, f) => a + (Number(f.result?.earnedUsd) || 0), 0); const marked = folders.filter(f => f.graded); const worked = marked.filter(f => f.graded === 'right').length;
  const angles = folders.flatMap(f => (f.calls || []).map(c => c.name || `Mind ${'AB'[c.mind]}`));
  return [{ ic: '🔥', t: 'Where its trends come from', say: 'The pages it read before pitching', rows: bars(count(shots, s => s.site), ' reads'), need: 'Shows after its first PoC', ask: 'file a poc' },
    { ic: '💰', t: 'What posts earn', say: 'From what you reported on each post', rows: folders.length ? [{ l: 'Filed', v: `${folders.length}`, part: 1 }, { l: 'Posted', v: `${posted.length}`, part: posted.length / folders.length, tone: 'up' }, { l: 'Earned per post', v: posted.length ? `$${(earned / posted.length).toFixed(2)}` : '$0.00', part: posted.length ? Math.min(1, earned / posted.length / 50) : 0, tone: 'up' }] : [], need: 'Shows after its first PoC', ask: 'Which of your PoC ideas should I post first, and why?' },
    { ic: '✅', t: 'What worked', say: 'From the marks you gave', rows: marked.length ? [{ l: 'Worked', v: `${worked} of ${marked.length}`, part: worked / marked.length, tone: 'up' }, ...bars(count(angles, a => a)).slice(0, 2)] : [], need: 'Mark an idea and this fills in', ask: 'What do the ideas I marked as working have in common?' }];
}
export function posTools(folders = []) {
  const marked = folders.filter(f => f.graded); const worked = marked.filter(f => f.graded === 'right').length; const weeks = count(folders, f => (f.at ? new Date(f.at * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : ''));
  return [{ ic: '🧪', t: 'Does it work', say: 'Pages you tried and marked', rows: folders.length ? [{ l: 'Filed pages', v: `${folders.length}`, part: 1 }, { l: 'You said it works', v: `${worked} of ${marked.length}`, part: marked.length ? worked / marked.length : 0, tone: 'up' }] : [], need: 'Shows after its first page', ask: 'Which of your pages should I try first?' },
    { ic: '🥊', t: 'Who builds better', say: 'Which mind finished each page', rows: bars(count(folders, f => f.by)), need: 'Shows after its first page', ask: 'Which of your minds builds better pages? Show why.' },
    { ic: '📅', t: 'Its pace', say: 'Pages filed by day', rows: bars(weeks), need: 'Shows after its first page', ask: 'Build me a page. Suggest the idea first.' }];
}
const MAKE = { pow: powTools, pop: popTools, pob: pobTools, poc: pocTools, pos: posTools };
export function ProofKit({ kind, folders, onCommand }) {
  const tools = MAKE[kind](folders || []);
  return <section className="pkt" aria-label="Its tools" data-testid={`pkt-${kind}`}>{tools.map((t, i) => <article key={t.t} className="pkt-card" style={{ '--i': i }} data-testid={`pkt-${kind}-${i}`}><header><Ic3 e={t.ic} size="26px" /><span><b>{t.t}</b><small>{t.say}</small></span></header>
    {t.rows.length ? <ul>{t.rows.map(r => <li key={r.l} className={r.tone ? `is-${r.tone}` : ''}><span>{r.l}</span><b className="m-num">{r.v}</b><i aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.02, r.part || 0)})` }} /></i></li>)}</ul> : <p className="pkt-none">{t.need}</p>}
    {onCommand ? <button type="button" className="m-btn" onClick={() => onCommand(t.ask)} data-tip="Puts this in its chat box. You press send" data-testid={`pkt-${kind}-ask-${i}`}>Ask it</button> : null}</article>)}</section>;
}
// 🧬 Each proof's own print: its ridges grow with what it has filed and bend with how it did. Together they make the desktop's fingerprint.
const KIND_FULL = { pow: 'PROOF OF WORK', pop: 'PROOF OF PERPS', pob: 'PROOF OF BIDS', poc: 'PROOF OF CONTENT', pos: 'PROOF OF CODE' };
const KIND_NAME = { pow: 'PoW', pop: 'PoP', pob: 'PoB', poc: 'PoC', pos: 'PoStatic' }; const KIND_INK = { pow: '#3ee58a', pop: '#c58bff', pob: '#ffc24d', poc: '#ff8bd8', pos: '#57c7ff' }; const KIND_SEED = { pow: 3, pop: 5, pob: 7, poc: 11, pos: 13 };
export const printRings = (kind, n) => Math.min(9, 2 + Math.ceil(Math.sqrt(Math.max(0, n)) * 1.6));
const hashId = s => { let h = 7; for (const c of String(s)) h = (h * 31 + c.charCodeAt(0)) % 9973; return h; };
export function ProofPrint({ kind, folders = [], size = 54, seedId = '' }) {   // seedId: one folder's own print, so no two proofs share one
  const n = folders.length; const rings = printRings(kind, n); const seed = seedId ? 3 + (hashId(seedId) % 9) : KIND_SEED[kind]; const bend = seedId ? (hashId(`${seedId}b`) % 628) / 100 : 0; const ink = KIND_INK[kind]; const won = folders.filter(f => (f.pnlPct != null && f.pnlPct > 0) || f.graded === 'right' || f.roePct > 0).length;
  const paths = useMemo(() => Array.from({ length: rings }, (_, r) => { const R = 5 + r * (40 / Math.max(1, rings)); const pts = Array.from({ length: 41 }, (_x, i) => { const a = (i / 40) * Math.PI * 2; const w = Math.sin(a * seed + r * 0.6 + bend) * (1.2 + r * 0.25) + Math.sin(a * 2 + r + bend) * 1.2; return `${(50 + Math.cos(a) * (R * 0.86 + w)).toFixed(1)} ${(50 + Math.sin(a) * (R + w)).toFixed(1)}`; }); return `M${pts.join('L')}Z`; }), [rings, seed, bend]);
  return <svg className="ppm" viewBox="0 0 100 100" width={size} height={size} role="img" aria-label={`${KIND_NAME[kind]} print: ${n} filed, ${won} won`}>{paths.map((d, i) => <path key={d} d={d} fill="none" stroke={ink} strokeWidth={i % 3 === 0 ? 1.6 : 0.8} opacity={n ? 0.45 + (0.55 * (i + 1)) / rings : 0.28} />)}</svg>;
}
// 🪜 Its steps, per proof. The last one says what it needs before it can run the whole loop on its own; until then it proposes.
const STEPS = {
  pow: { steps: ['Reads 4 coins', 'Both minds propose', 'They agree on 1', 'Buys it', 'Holds and watches', 'Sells', 'Files it'], loop: 'Runs the whole loop with its own wallet.', needs: 'Proposes until its wallet is funded.' },
  pop: { steps: ['Reads live prices', 'Both call blind', 'They argue once', 'Proposes to you', 'Paper trade', 'Stops or takes', 'Graded'], loop: 'On paper, on true prices. Nothing real opens.', needs: 'On paper, on true prices. Nothing real opens.' },
  pob: { steps: ['Reads the games', 'Both pick blind', 'Builds the legs', 'Proposes to you', 'Waits for the game', 'Live scores in chat', 'Graded at the final'], loop: 'Picks are filed on paper.', needs: 'Proposes until its Polymarket address is on file.' },
  poc: { steps: ['Reads what is trending', 'Both pitch blind', 'You pick one', 'You post it', 'You report the result', 'Marked'], loop: 'It never posts on its own.', needs: 'Proposes. You post it and report what it earned.' },
  pos: { steps: ['You ask', 'It researches', 'It suggests', 'You approve', 'It builds', 'Second mind reviews', 'You say if it works'], loop: 'Filed once you say it works.', needs: 'Proposes. Publishing needs a host you sign in to.' },
};
const stepNow = (kind, d) => { if (kind === 'pow') { const p = d?.powFolder?.phase; return !p ? -1 : /scan|read|intake/.test(p) ? 0 : /propose|split/.test(p) ? 1 : /choose/.test(p) ? 2 : /buy/.test(p) ? 3 : /hold|watch|run/.test(p) ? 4 : /sell/.test(p) ? 5 : 4; } if (kind === 'pop') return d?.popRead ? 0 : d?.popCard ? 3 : d?.popFolder ? 4 : -1; if (kind === 'pob') { const open = (d?.pobFolders || []).find(f => f.games?.length && !f.graded); const live = open?.games?.some(g => g.state === 'in'); return d?.pobRead ? 0 : live ? 5 : open ? 4 : -1; } return -1; };
export function ProofHead({ kind, folders, d, onBrowse }) {
  const [src, setSrc] = useState(null); const [open, setOpen] = useState(false); const s = STEPS[kind]; const now = stepNow(kind, d); const canLoop = kind === 'pow' && !!(d?.wallet?.address || d?.agentWallet?.address);
  useEffect(() => { if (!open || src) return; fetch(apiUrl('/api/cats/tools/sourcefile')).then(r => (r.ok ? r.json() : null)).then(j => setSrc(j?.proofs?.[kind] || [])).catch(() => setSrc([])); }, [open, src, kind]);
  return <section className={`phd m-live is-${kind}`} data-testid={`phd-${kind}`}><div className="phd-top"><span className="phd-print" data-tip={`${KIND_NAME[kind]}'s part of its fingerprint. It grows with each proof filed`}><ProofPrint kind={kind} folders={folders || []} size={84} /></span><span className="phd-t"><em>{KIND_FULL[kind]}</em><b>{KIND_NAME[kind]}</b><small>{(folders || []).length} filed · {canLoop ? s.loop : s.needs}</small></span><button type="button" className="m-btn" aria-expanded={open} onClick={() => setOpen(x => !x)} data-tip="The best places to read for this proof" data-testid={`phd-src-${kind}`}>Its sources</button></div>
    <ol className="phd-steps">{s.steps.map((t, i) => <li key={t} className={i === now ? 'is-now' : i < now ? 'is-done' : ''}><i className="m-num">{i + 1}</i>{t}</li>)}</ol>
    {open ? <ul className="phd-src" data-testid={`phd-srcs-${kind}`}>{!src ? <li>Reading…</li> : src.map(r => <li key={r.host}><a href={`https://${r.host}`} target="_blank" rel="noopener noreferrer"><b>{r.name}</b><small>{r.what}</small></a>{onBrowse ? <button type="button" className="m-btn" onClick={() => onBrowse(r.host.split('/')[0])} data-tip="Opens it in its Browser" data-testid={`phd-open-${r.host}`}>Open</button> : null}</li>)}</ul> : null}</section>;
}
// 🧬 The desktop's fingerprint, made of its five proofs.
export function PrintParts({ d, extra = {} }) {
  const parts = [['pow', d?.powFolders], ['pop', d?.popFolders], ['pob', d?.pobFolders], ['poc', d?.pocFolders || extra.poc], ['pos', d?.psFolders || extra.pos]].map(([k, f]) => [k, f || []]); const total = parts.reduce((a, [, f]) => a + f.length, 0);
  return <section className="ppp" aria-label="What makes its print" data-testid="print-parts">{parts.map(([k, f]) => <span key={k} data-tip={`${f.length} ${KIND_NAME[k]} filed`}><ProofPrint kind={k} folders={f} size={64} /><b>{KIND_NAME[k]}</b><small className="m-num">{total ? `${Math.round((100 * f.length) / total)}%` : '0%'}</small></span>)}</section>;
}

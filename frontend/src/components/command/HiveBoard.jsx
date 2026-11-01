import React, { useCallback, useEffect, useRef, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { AiCursor, readCursor } from './CatWorkbench';
import '../../styles/hive.css';

// 🐝 THE HIVE (owner 2026-10-31: "a FEELESS twist on Crawl — they browse forever until turned off and compound"): proof of insight. Agents with the
// Hive on read the trenches on their own and file CELLS (BUY / WATCH / AVOID + why); an hour on every cell is graded on what the coin really did —
// right calls earn honey. A drawn honeycomb (newest cell drops in from the top), the epoch ring (one UTC day) and the honey board.
const HEX = 'M14 0 L28 8 L28 24 L14 32 L0 24 L0 8 Z';
const CALL = { BUY: 'is-buy', AVOID: 'is-avoid', WATCH: 'is-watch' };
const hm = s => `${Math.floor(s / 3600)}h ${String(Math.floor((s % 3600) / 60)).padStart(2, '0')}m`;

export function HiveBoard({ api }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const seenIds = useRef(null); const [fresh, setFresh] = useState(new Set());
  useEffect(() => { let on = true; const go = first => { if (document.hidden && first !== true) return; api('/api/cats/hive').then(x => { if (!on || !x || !Array.isArray(x.cells)) return;
      const ids = new Set(x.cells.map(c => c.id)); if (seenIds.current) setFresh(new Set([...ids].filter(i => !seenIds.current.has(i)))); seenIds.current = ids; setD(x); setErr(''); }).catch(e => on && setErr(e.message)); };
    go(true); const t = setInterval(go, 20000); return () => { on = false; clearInterval(t); }; }, [api]);
  if (!d) return <section className="hv" data-testid="hive"><p className="hv-nil">{err || 'reading the Hive…'}</p></section>;
  const p = 1 - d.left / 86400; const cells = d.cells.slice(0, 48);
  return <section className="hv" data-testid="hive">
    <header className="hv-head">
      <span className="hv-ring" style={{ '--p': p }} data-tip="This epoch (one UTC day): honey adds up until it turns"><svg viewBox="0 0 44 44" aria-hidden="true"><circle cx="22" cy="22" r="19" /><circle className="on" cx="22" cy="22" r="19" style={{ strokeDashoffset: 119.4 * (1 - p) }} /></svg><b className="m-num">{hm(d.left)}</b><small>EPOCH {d.epoch % 1000}</small></span>
      <span className="hv-kpi"><em>CELLS FILED</em><b className="m-num" key={d.filed}>{d.filed}</b></span>
      <span className="hv-kpi"><em>GRADED</em><b className="m-num" key={d.graded}>{d.graded}</b><i aria-hidden="true"><u style={{ transform: `scaleX(${d.filed ? d.graded / d.filed : 0})` }} /></i></span>
      <p className="hv-how">Agents read the trenches on their own and file a call; an hour later the Hive grades it on what the coin really did. Right calls earn 🍯 honey.</p>
    </header>
    <div className="hv-body">
      <ol className="hv-comb" aria-label="The newest cells" data-testid="hive-comb">{cells.length ? cells.map((c, i) => <li key={c.id} className={`${CALL[c.call] || ''}${c.honey > 0 ? ' is-right' : c.honey < 0 ? ' is-wrong' : ''}${fresh.has(c.id) ? ' is-new' : ''}`} style={{ '--i': i }}
        data-tip={`${c.name}: ${c.call} $${c.sym} — ${c.why}${c.honey == null ? ' · grading in the hour' : ` · ${c.move != null ? `${c.move > 0 ? '+' : ''}${c.move}% → ` : ''}${c.honey > 0 ? '+' : ''}${c.honey} honey`}`}>
        <svg viewBox="0 0 28 32" aria-hidden="true"><path d={HEX} /></svg><b>${c.sym}</b><small>{c.call}</small>{c.honey != null ? <em className="m-num">{c.honey > 0 ? '+' : ''}{c.honey}</em> : <em className="hv-wait" aria-label="grading">⏳</em>}</li>)
        : <li className="hv-empty">No cells yet — turn 🐝 Hive on in an agent's desk.</li>}</ol>
      <ol className="hv-board" aria-label="Honey this epoch" data-testid="hive-board"><li className="hv-board-h">🍯 HONEY THIS EPOCH</li>
        {d.board.length ? d.board.map((r, i) => { const top = Math.max(1, ...d.board.map(x => Math.abs(x.honey)));
          return <li key={r.cat} style={{ '--i': i }}><b className="m-num">{i + 1}</b><span>{r.name}</span><i aria-hidden="true"><u className={r.honey < 0 ? 'is-dn' : ''} style={{ transform: `scaleX(${Math.max(0.03, Math.abs(r.honey) / top)})` }} /></i>
            <em className={`m-num ${r.honey < 0 ? 'is-dn' : 'is-up'}`}>{r.honey > 0 ? '+' : ''}{r.honey}</em><small>{r.right}/{r.graded} right</small></li>; })
          : <li className="hv-empty">The board fills as cells are graded.</li>}</ol>
    </div>
  </section>;
}

// 🏺 THE COLONY POT (owner 2026-10-31: "the smartest, next-level way of safe growth — I create a Circle wallet for it and pick how it's secured"):
// one Circle wallet; our server is the only one that can send from it, so it enforces the guards — the principal never leaves, at most the
// epoch cap of the GROWTH pays out, only to owners who signed to share winnings (split by what each shared), only after a timelocked approval.
// Opportunity 1 = the colony pool the owner opens with this wallet (assigned here); opportunity 2 = the sharers' airdrop (daily / weekly).
const usd = v => (v == null ? '—' : `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: Number(v) >= 100 ? 0 : 2 })}`);
const GUARD = { principalLock: ['🔒 Principal lock', 'What was staked or locked in never pays out — only growth'], allowlist: ['📜 Allowlist', 'Airdrops go only to owners who signed to share'], ownerSigns: ['✍ You approve', 'Every payout batch waits for your approval'] };
export function ColonyPot({ call }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState('');
  const [pool, setPool] = useState(''); const [plat, setPlat] = useState(''); const seeded = useRef(false);
  const take = x => { if (x && 'policy' in x) { setD(x); setErr(''); if (!seeded.current) { seeded.current = true; setPool(x.pool?.address || ''); setPlat(x.pool?.platform || ''); } } else setErr('The colony did not answer.'); };
  useEffect(() => { let on = true; const go = first => { if (first || !document.hidden) call('/admin/colony').then(x => on && take(x)).catch(e => on && setErr(e.message)); };
    go(true); const t = setInterval(go, 30000); return () => { on = false; clearInterval(t); }; }, [call]);   // eslint-disable-line react-hooks/exhaustive-deps
  const act = async (action, extra) => { setBusy(action); setErr(''); try { take(await call('/admin/colony', { method: 'POST', body: JSON.stringify({ action, ...extra }) })); } catch (e) { setErr(e.message); } finally { setBusy(''); } };
  if (!d) return <article className="fch-card hv-pot" data-testid="colony-pot"><h4>🏺 COLONY POT</h4><p className="fch-nil">{err || 'reading the pot…'}</p></article>;
  const v = d.value?.usd ?? 0; const top = Math.max(v, d.principalUsd, 1);
  return <article className="fch-card fch-wide hv-pot" data-testid="colony-pot">
    <h4>🏺 COLONY POT<small>{d.wallet ? <>Circle · <code>{d.wallet.address.slice(0, 4)}…{d.wallet.address.slice(-4)}</code></> : 'no wallet yet'} · {d.colonized} colonized · next airdrop in {Math.max(0, Math.round((d.nextAirdrop * 1000 - Date.now()) / 3600000))}h</small></h4>
    {!d.wallet ? <p className="hv-pot-new"><span>The pot is ONE Circle wallet. Your users' money is never pooled — each agent trades from its own wallet; the pot only ever pays out what it GREW.</span>
      <button type="button" className="m-btn m-go" disabled={!!busy} onClick={() => act('create')} data-tip="Makes the pot's Solana wallet on the agent Circle account (one, ever — a second click returns the same wallet)" data-testid="colony-create">{busy === 'create' ? 'Making…' : '🏺 Create the pot wallet'}</button></p>
      : <>
        <div className="hv-pot-vault" data-tip="Locked principal (never pays out) · growth above it · the part that may leave this epoch">
          <i className="is-floor" style={{ transform: `scaleX(${Math.min(1, d.principalUsd / top)})` }} /><i className="is-grow" style={{ transform: `scaleX(${Math.min(1, v / top)})` }} />
          <p className="fch-flow"><span><b className="m-num" key={v}>{usd(v)}</b><small>in the pot</small></span><i aria-hidden>−</i><span><b className="m-num">{usd(d.principalUsd)}</b><small>🔒 locked</small></span><i aria-hidden>=</i>
            <span className={d.growthUsd ? 'is-good' : ''}><b className="m-num">{usd(d.growthUsd)}</b><small>growth</small></span><i aria-hidden>→</i><span className="hv-pot-pay"><b className="m-num">{usd(d.payableUsd)}</b><small>may pay this epoch</small></span></p></div>
        <p className="hv-pot-parts m-note">{d.value ? `${d.value.sol} SOL · ${usd(d.value.usdc)} USDC · ${usd(d.value.feecatUsd)} FEECAT` : "couldn't read the chain — numbers are the last good ones"}</p>
        <div className="hv-pot-row">
          <ul className="hv-guards" aria-label="Guards that are always on">{d.guards.map(g => <li key={g} data-tip={GUARD[g]?.[1]}>{GUARD[g]?.[0] || g}<em>ALWAYS ON</em></li>)}</ul>
          <div className="hv-pot-set">{[['epochCapPct', 'Epoch cap', '% of growth'], ['timelockH', 'Timelock', 'hours']].map(([k, l, u]) => { const [lo, hi] = d.bounds[k];
            return <label key={k} data-tip={k === 'epochCapPct' ? 'The most of the growth that may leave in one epoch — the rest keeps compounding' : 'How long a payout batch waits (anyone can see it) before you can approve it'}>
              <span>{l}<b className="m-num">{d.policy[k]}</b><small>{u}</small></span>
              <input type="range" min={lo} max={hi} value={d.policy[k]} disabled={!!busy} onChange={e => setD(x => ({ ...x, policy: { ...x.policy, [k]: Number(e.target.value) } }))}
                onPointerUp={e => act('policy', { policy: { ...d.policy, [k]: Number(e.target.value) } })} onKeyUp={e => act('policy', { policy: { ...d.policy, [k]: Number(e.target.value) } })} data-testid={`colony-${k}`} /></label>; })}
            <button type="button" className="m-btn" disabled={!!busy || !d.growthUsd} onClick={() => act('lock')} data-tip="Lock today's value in as principal: the floor only ever goes up, so gains compound instead of paying out" data-testid="colony-lock">{busy === 'lock' ? 'Locking…' : '🔒 Lock gains in'}</button></div>
        </div>
        <div className="hv-pot-row">
          <form className="hv-pot-pool" onSubmit={e => { e.preventDefault(); act('pool', { address: pool.trim(), platform: plat.trim() }); }} data-tip="Opportunity 1: the pool you opened with the colony wallet — users see it in the Colonize popout">
            <span>🌊 COLONY POOL {d.pool ? <em className="is-on">OPEN · {d.pool.platform}</em> : <em>not open</em>}</span>
            <input className="m-input" value={plat} onChange={e => setPlat(e.target.value)} placeholder="platform (e.g. Meteora)" aria-label="Pool platform" data-testid="colony-pool-platform" />
            <input className="m-input" value={pool} onChange={e => setPool(e.target.value)} placeholder="pool address" aria-label="Pool address" data-testid="colony-pool-addr" />
            <button type="submit" className="m-btn" disabled={!!busy} data-testid="colony-pool-save">{pool.trim() ? 'Save the pool' : 'Clear'}</button></form>
          <div className="hv-pot-set"><label><span>🪂 AIRDROP<b className="m-num">{d.sharers}</b><small>signed sharers · {d.sharedSol} SOL shared, unsent</small></span>
            <span className="m-seg" role="group" aria-label="How often the airdrop pays">{[['daily', 'Every 24 h'], ['weekly', 'Weekly']].map(([k, l]) => <button key={k} type="button" className={d.policy.cadence === k ? 'active' : ''} aria-pressed={d.policy.cadence === k} disabled={!!busy} onClick={() => act('policy', { policy: { cadence: k } })} data-testid={`colony-cadence-${k}`}>{l}</button>)}</span></label></div>
        </div>
        <ol className="hv-board hv-split" aria-label="The next airdrop" data-testid="colony-airdrop"><li className="hv-board-h">🪂 NEXT AIRDROP · {usd(d.payableUsd)} BY WHAT EACH SHARED</li>
          {d.airdrop.length ? d.airdrop.map((r, i) => <li key={r.owner} style={{ '--i': i }}><b className="m-num">{i + 1}</b><span>{r.owner.slice(0, 4)}…{r.owner.slice(-4)}</span><i aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.03, r.pct / 100)})` }} /></i>
            <em className="m-num is-up">{usd(r.usd)}</em><small>{r.sol} SOL shared · {r.pct}%</small></li>)
            : <li className="hv-empty">Nobody has shared winnings this period — an airdrop pays by what each owner shared.</li>}</ol>
        <p className="fch-note">Airdrops and pool deposits are not sent from here yet — this is the exact split the guards allow. Sending needs your approval flow (not built).</p>
      </>}
    <p className="hv-pot-net" data-tip="The real browsers this server can open, in order — names only, keys stay on the server"><small>BROWSERS</small>{d.browsers.map((b, i) => <span key={b} className={b === 'reader' ? 'is-off' : ''}>{i + 1}. {b}</span>)}</p>
    {err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}
  </article>;
}

// 🐝 THE COLONY PAGE (owner 2026-10-31: "like Crawl's crawlers page — about 8-10 agents a page, more on scroll, each with 2 good-sized screens and
// the agent drawn in the middle"): every agent's two windows as visitors may see them (a real cached screenshot, its last page when it's done, frozen
// while its owner signs in, nothing when incognito), the drawn agent between them, its honey this epoch and its newest graded call.
function useSeen(ref) {
  const [on, setOn] = useState(true);
  useEffect(() => { const el = ref.current; if (!el || typeof IntersectionObserver === 'undefined') return undefined;
    const io = new IntersectionObserver(([e]) => setOn(e.isIntersecting), { threshold: 0.05 }); io.observe(el); return () => io.disconnect(); }, [ref]);
  return on;
}
function ColonyScreen({ a, w, side, tick }) {
  const [bad, setBad] = useState(false); useEffect(() => setBad(false), [tick, w?.screen]);
  const host = w?.host || (a.kind === 'trading' ? 'FEELESS · trenches' : 'idle');
  let body;
  if (a.incognito) body = <span className="cl-off is-incog"><b aria-hidden="true">🕶</b>incognito</span>;
  else if (w?.frozen) body = <span className="cl-off is-frozen"><b aria-hidden="true">❄</b>paused — its owner is signing in</span>;
  else if (w?.screen && !bad) body = <img src={apiUrl(`/api/cats/${a.id}/screen/${w.i}${w.last ? '' : `?t=${tick}`}`)} alt={`${a.name}'s window ${side}`} loading="lazy" onError={() => setBad(true)} />;
  else body = <span className="cl-off"><i className="cl-scan" aria-hidden="true" /><b aria-hidden="true">{a.kind === 'trading' ? '📈' : '🧭'}</b>{a.status === 'working' ? 'loading the screen…' : a.kind === 'trading' ? 'reading the trenches' : 'waiting for its next job'}</span>;
  return <span className={`cl-scr${w?.status === 'working' ? ' is-go' : ''}`} data-testid={`cl-scr-${a.id}-${side}`}>
    <span className="cl-bar"><i /><i /><i /><b>{host}</b>{w?.last && !a.incognito ? <em className="cl-last">LAST PAGE</em> : w?.status === 'working' ? <em className="cl-rec">● LIVE</em> : null}</span>
    <span className="cl-view">{body}{a.incognito || w?.frozen ? null : <AiCursor c={w?.cursor} kind={readCursor()} />}<small className="cl-model">{side} · {w?.model || a.brains?.[side === 'A' ? 0 : 1] || '—'}</small></span></span>;
}
function ColonyCell({ a, face, onOpen, i, top, extra }) {
  const ref = useRef(null); const seen = useSeen(ref); const [tick, setTick] = useState(0); const live = a.windows?.some(w => w.status === 'working');
  useEffect(() => { if (!seen || !live) return undefined; const t = setInterval(() => { if (!document.hidden) setTick(x => x + 1); }, 5000); return () => clearInterval(t); }, [seen, live]);
  const wins = [0, 1].map(k => a.windows?.find(w => w.i === k) || a.windows?.[k] || null);
  const c = a.last; const seenAt = useRef(a.carrying?.at); const [drop, setDrop] = useState(null);
  useEffect(() => { const t = a.carrying?.at; if (!t || t === seenAt.current) return undefined; seenAt.current = t; setDrop(a.carrying.text); const k = setTimeout(() => setDrop(null), 2600); return () => clearTimeout(k); }, [a.carrying?.at, a.carrying?.text]);   // 🗄 a NEW keep drops into the agent
  return <article ref={ref} className={`cl-cell${a.colonized ? ' is-col' : ''}${live ? ' is-go' : ''}`} style={{ '--i': i }} data-testid={`cl-${a.id}`}>
    <div className="cl-stage"><ColonyScreen a={a} w={wins[0]} side="A" tick={tick} />
      <button type="button" className="cl-face" onClick={() => onOpen?.(a)} data-tip={`Open ${a.name}'s desk`} aria-label={`Open ${a.name}`}><span className="cl-halo" aria-hidden="true" />{face ? face(a) : null}
        {drop ? <span className="cl-drop" key={a.carrying.at} aria-hidden="true" data-testid={`cl-drop-${a.id}`}>🗄 {drop}</span> : null}</button>
      <ColonyScreen a={a} w={wins[1]} side="B" tick={tick} /></div>
    <footer className="cl-foot">
      <span className="cl-who"><b>{a.name}</b><small>{a.kind === 'general' ? '🧭 GENERAL' : '📈 TRADER'} · LVL {a.level || 1}{a.colonized ? ' · 🐝 COLONIZED' : ''}</small></span>
      <span className="cl-honey" data-tip={`${a.honey} honey this epoch · ${a.right}/${a.graded} graded calls right`}><em>🍯</em><b className={`m-num ${a.honey < 0 ? 'is-dn' : ''}`} key={a.honey}>{a.honey > 0 ? '+' : ''}{a.honey}</b>
        <i aria-hidden="true"><u className={a.honey < 0 ? 'is-dn' : ''} style={{ transform: `scaleX(${Math.max(0.04, Math.min(1, Math.abs(a.honey) / Math.max(1, top)))})` }} /></i><small>{a.right}/{a.graded} right</small></span>
      <small className={`cl-carry${drop ? ' is-new' : ''}`} data-tip="What it stored last — it goes into its drawer">› {a.carrying ? <>carrying “{a.carrying.text}” to its drawer</> : a.status === 'working' ? 'reading — nothing kept yet' : 'nothing carried yet'}</small>
      {extra ? extra(a) : null}
      {c ? <span className={`cl-call ${CALL[c.call] || ''}${c.honey > 0 ? ' is-right' : c.honey < 0 ? ' is-wrong' : ''}`} data-tip={`${c.call} $${c.sym} — ${c.why}`}>{c.call} ${c.sym}<em>{c.honey == null ? '⏳' : `${c.honey > 0 ? '+' : ''}${c.honey}`}</em></span> : <span className="cl-call is-none">no call yet</span>}
    </footer></article>;
}
export function ColonyGrid({ api, face, onOpen, ids, extra }) {
  const [rows, setRows] = useState([]); const [meta, setMeta] = useState(null); const [err, setErr] = useState(''); const pageRef = useRef(0); const busy = useRef(false); const end = useRef(null); const seeEnd = useSeen(end);
  const load = useCallback(async (page, replace) => { if (busy.current) return; busy.current = true;
    try { const x = await api(`/api/cats/colony?page=${page}${ids ? `&ids=${encodeURIComponent(ids)}` : ''}`); if (!x || !Array.isArray(x.agents)) throw new Error('The colony did not answer.');
      setRows(r => (replace ? x.agents : [...r.filter(o => !x.agents.some(n => n.id === o.id)), ...x.agents])); setMeta(x); pageRef.current = page; setErr(''); }
    catch (e) { setErr(e.message); } finally { busy.current = false; } }, [api, ids]);
  useEffect(() => { load(0, true); const t = setInterval(() => { if (!document.hidden) load(0, false); }, 15000); return () => clearInterval(t); }, [load]);
  useEffect(() => { if (seeEnd && meta?.more && meta.page === pageRef.current) load(pageRef.current + 1, false); }, [seeEnd, meta, load]);   // more on scroll
  const top = Math.max(1, ...rows.map(r => Math.abs(r.honey || 0)));
  return <section className={`cl${ids ? ' is-mine' : ''}`} data-testid={ids ? 'colony-mine' : 'colony'}>
    {ids ? null : <header className="cl-head"><span><small>THE COLONY</small><b>{meta ? <><em className="m-num">{meta.colonized}</em> colonized · <em className="m-num">{meta.total}</em> agents</> : 'reading the colony…'}</b></span>
      <p>Every agent's two windows, live — the drawn agent between them. Colonized agents file graded calls and their trades are graded before and after; honey splits the colony pot's growth.</p></header>}
    {err && !rows.length ? <p className="hv-nil">{err}</p> : null}
    <div className="cl-grid">{rows.map((a, k) => <ColonyCell key={a.id} a={a} face={face} onOpen={onOpen} i={k % 10} top={top} extra={extra} />)}</div>
    <span ref={end} className="cl-end" aria-hidden="true">{meta?.more ? 'more agents…' : null}</span>
    {ids ? null : <HiveBoard api={api} />}
  </section>;
}

import { useSolPrice } from '../../lib/solPrice';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { AiCursor, FolderView, readCursor } from './CatWorkbench';
import { PowCard } from './CatCockpit';
import '../../styles/hive.css';
import '../../styles/colonyTree.css';
import { HoneyTank } from './HoneyTanks';
import { ShaderWall } from './DeskShell';

// 🐝 THE HIVE (owner 2026-10-31: "a FEELESS twist on Crawl — they browse forever until turned off and compound"): proof of insight. Agents with the
// Hive on read the trenches on their own and file CELLS (BUY / WATCH / AVOID + why); an hour on every cell is graded on what the coin really did —
// right calls earn honey. A drawn honeycomb (newest cell drops in from the top), the epoch ring (one UTC day) and the honey board.
const CALL = { BUY: 'is-buy', AVOID: 'is-avoid', WATCH: 'is-watch' };
const hm = s => `${Math.floor(s / 3600)}h ${String(Math.floor((s % 3600) / 60)).padStart(2, '0')}m`;

// 🐝 HOW COLONIZING WORKS, alive (owner 2026-11-01: "a true left, right, up, down alive connection in a honey design of how colonizing works"):
// eight honeycomb stations in one loop — agents → PoW → buy on FEELESS → graded → honey → share → pot → airdrop → back to agents. Bees (dots)
// run every lane; more run, faster, while agents are live. Every number is real (/api/cats/hive + the colony meta); transform / opacity only.
// 📖 THE MANUAL (owner 2026-11-01: "a manual in the Colony tab") — how a PoW runs, step by step, with the commands that start it. The same rules every model reads.
const MANUAL = [['🧺', 'POOL', 'FEELESS vets up to 8 coins (intake · Pump · DexScreener) with every buy guard + the safety check — an unsafe one is replaced, never offered'],
  ['🗣', 'PROPOSE', 'Mind A proposes 3, mind B proposes 3 — each sees the coin\'s prior PoW from the archive'],
  ['✂', 'SPLIT', 'Each mind takes 2 of the shortlist and writes how it will investigate them'],
  ['🔎', 'RESEARCH', 'Each researches its own: FEELESS + 3 sites, 3–8 moves a site (random), ≤3 vitals a site, duplicate facts dropped, 2 snapshots a site'],
  ['⚖', 'DECIDE', 'Every coin checked again → 3 turns pick the ONE, its size, TP + SL → bought from its own wallet → checks at +15 s, +30 s, every 60 s until it sells'],
  ['🗄', 'FILE', 'The folder + its final report land on its Desktop; every research + outcome stays in the PoW archive FOREVER (agents search it with the pow tool)']];
export function ColonyManual() {
  const [open, setOpen] = useState(false);
  return <section className={`cfm${open ? ' is-open' : ''}`} data-testid="colony-manual"><button type="button" className="cfm-h" onClick={() => setOpen(o => !o)} aria-expanded={open}>
    <b>📖 THE PoW MANUAL</b><small>what every agent does when you type <code>file a PoW</code> · <code>propose a PoW</code> · <code>stop PoW</code> · <code>propose a PoP</code></small><i aria-hidden="true">{open ? '−' : '+'}</i></button>
    <ol className="cfm-steps">{MANUAL.map(([ic, k, t], i) => <li key={k} style={{ '--i': i }}><span className="cfm-n" aria-hidden="true">{ic}</span><em>{i + 1} · {k}</em>{open ? <small>{t}</small> : null}</li>)}</ol>
  </section>;
}
// 💸 THE COLONY'S MONEY, LIVE (owner 2026-11-02: "a realistic visual like crawl's treasury --flow, but FEELESS"): real boxes with real numbers —
// PoW trades → P/L → shares owed → the colony pot (its on-chain balance) → the airdrop — joined by pipes whose packets move only where money
// really moved, and THE LEDGER beside it: every real trade an agent's own wallet made + every share, each with its tx. /api/cats/colony/flow.
const sol4 = v => (v == null ? '—' : `${Number(v) >= 0 ? '' : '−'}${Math.abs(Number(v)).toFixed(4)} SOL`);
const solT = v => (Number(v) > 0 && Number(v) < 0.0001 ? `${Number(Number(v).toPrecision(2))} SOL` : sol4(v));   // a tiny real amount never reads as zero
const usd2 = (v, px) => (v == null || !px ? '' : `≈ $${(Math.abs(Number(v)) * px).toFixed(2)}`);
const utc = t => new Date(t * 1000).toISOString().slice(11, 19);
function useColonyFlow(api) {
  const [d, setD] = useState(null); const [fresh, setFresh] = useState(new Set()); const seen = useRef(null);
  useEffect(() => { let on = true; const go = first => { if (document.hidden && first !== true) return;
    api('/api/cats/colony/flow').then(x => { if (!on || !x) return; const keys = (x.ledger || []).map(r => `${r.at}${r.sig}${r.kind}`);
      if (seen.current) setFresh(new Set(keys.filter(k => !seen.current.has(k)))); seen.current = new Set(keys); setD(x); }).catch(() => {}); };
    go(true); const t = setInterval(go, 20000); return () => { on = false; clearInterval(t); }; }, [api]);
  return { d, fresh };
}
function ColonyLedger({ rows, fresh, ready }) {
  return <div className="cmf-ledger" aria-label="Ledger"><span className="cmf-cap">ledger <i aria-hidden="true" /> live</span>
    <div className="cmf-table" role="table"><div className="cmf-tr is-head" role="row"><span>utc</span><span>kind</span><span>agent · coin</span><span>SOL</span><span>tx</span></div>
      {rows.length ? rows.map((r, i) => { const k = `${r.at}${r.sig}${r.kind}`;
        return <div key={k} role="row" className={`cmf-tr is-${r.kind}${fresh.has(k) ? ' is-new' : ''}`} style={{ '--i': i % 20 }} data-tip={r.memo}><span className="m-num">{utc(r.at)}</span><span>{r.memo}</span>
          <span>{r.agent}{r.sym ? ` · $${r.sym}` : ''}</span><span className={`m-num ${r.kind === 'sell' || r.kind === 'share' ? 'is-up' : 'is-dn'}`}>{r.sol ? `${r.kind === 'buy' ? '−' : '+'}${Number(r.sol).toFixed(4)}` : '—'}</span>
          <span>{r.sig ? <a href={`https://solscan.io/tx/${r.sig}`} target="_blank" rel="noopener noreferrer">{r.sig.slice(0, 4)}…{r.sig.slice(-4)} ↗</a> : '—'}</span></div>; })
        : <p className="cmf-empty">{ready ? 'No real trades yet — the first PoW buy from an agent’s own wallet lands here with its tx.' : 'reading the chain…'}</p>}</div></div>;
}
// 🍯 one agent's own lines of the colony ledger (the Honey pot's tanks show the totals)
export function AgentLedger({ api, agent }) {
  const { d, fresh } = useColonyFlow(api); const key = String(agent || '').slice(0, 12);
  return <section className="cfl cmf" data-testid="agent-ledger"><ColonyLedger rows={(d?.ledger || []).filter(r => String(r.agent || '').startsWith(key))} fresh={fresh} ready={!!d} /></section>;
}
// 🌳 THE COLONY TREE (owner 2026-11-04): the pot at the top of the chain, what flows into it, every agent in the comb, every winning proof and what it owes.
const BEES = [['6%', '12%', '19s', '0s'], ['62%', '30%', '24s', '-7s'], ['28%', '62%', '21s', '-13s']];
const DRIPS = [['18%', '9s', '0s'], ['46%', '12s', '-4s'], ['77%', '10s', '-7s']];
export function ColonyFlow({ api, onOpen }) {
  const { d, fresh } = useColonyFlow(api); const px = useSolPrice(); const [, tick] = useState(0);
  useEffect(() => { const c = setInterval(() => tick(n => n + 1), 1000); return () => clearInterval(c); }, []);
  const sh = d?.shares || {}; const pot = d?.pot || {}; const ep = d?.epoch || {}; const ad = d?.airdrop || {}; const t = d?.tree || {}; const agents = t.agents || []; const wins = t.wins || [];
  const left = ad.next ? Math.max(0, ad.next - Date.now() / 1000) : null; const cycle = ad.cadence === 'weekly' ? 604800 : 86400;
  const owed = sh.owedSol || 0; const sent = d?.sentSol || 0; const paid = ad.paidSol || 0; const potSol = pot.sol || 0; const most = Math.max(potSol, owed, sent, paid);
  const lvl = v => (most > 0 ? v / most : 0); const usdOf = v => usd2(v, px) || 'nothing yet'; const topHoney = Math.max(1, ...agents.map(a => Math.abs(a.honey)));
  return <section className="ctr" data-testid="colony-flow" aria-label="The colony tree">
    <i className="ctr-sky" aria-hidden="true" />
    <div className="ctr-live" aria-hidden="true"><ShaderWall mood="colony" />{BEES.map(([x, y, d, w]) => <svg key={x} className="ctr-bee" style={{ '--x': x, '--y': y, '--d': d, '--w': w }} viewBox="0 0 26 20"><g className="w"><ellipse cx="10" cy="5" rx="5" ry="3.4" fill="#ffffffa8" /><ellipse cx="16" cy="5" rx="5" ry="3.4" fill="#ffffff80" /></g><ellipse cx="13" cy="12" rx="8" ry="5.6" fill="#ffc533" /><path d="M10 7v10M15 7v10" stroke="#2a1604" strokeWidth="2.4" /><circle cx="20" cy="11" r="2.8" fill="#2a1604" /></svg>)}{DRIPS.map(([x, d, w]) => <i key={x} className="ctr-drip" style={{ '--x': x, '--d': d, '--w': w }} />)}</div>
    <div className="ctr-crown">
      <div className="ctr-side">
        <span className="ctr-clock" data-tip="The next airdrop to owners who shared, each waiting for approval"><em>🪂 NEXT AIRDROP</em><b className="m-num">{left == null ? '—' : `${Math.floor(left / 3600)}h ${String(Math.floor(left / 60) % 60).padStart(2, '0')}m`}</b><u><s style={{ transform: `scaleX(${left == null ? 0 : Math.min(1, left / cycle)})` }} /></u></span>
      </div>
      <HoneyTank shape="barrel" tone="honey" level={lvl(potSol)} label="🏺 THE POT" value={d ? solT(potSol) : '…'} sub={usdOf(potSol)} testid="ctr-pot" tip="The colony wallet's balance, read on-chain" />
      <div className="ctr-side">
        <span data-tip="Honey every graded call earned this epoch"><em>🐝 THIS EPOCH</em><b className={`m-num ${ep.honey > 0 ? 'is-up' : ep.honey < 0 ? 'is-dn' : ''}`}>{ep.honey > 0 ? '+' : ''}{ep.honey || 0}</b><small>{ep.agents || 0} agents graded</small></span>
        {pot.address ? <a className="m-btn" href={`https://solscan.io/account/${pot.address}`} target="_blank" rel="noopener noreferrer" data-tip="See the pot on-chain">{pot.address.slice(0, 4)}…{pot.address.slice(-4)} ↗</a> : <small className="m-dim">The pot isn't opened yet</small>}
      </div>
    </div>
    <div className="ctr-chain" aria-hidden="true">{[owed > 0, sent > 0, paid > 0].map((on, i) => <i key={i} className={on ? 'is-on' : ''}><u /></i>)}</div>
    <div className="ctr-vessels">
      <HoneyTank i={1} shape="jar" tone="amber" level={lvl(owed)} label="OWED" value={solT(owed)} sub={`${sh.count || 0} wins · ${sh.sharing || 0} sharing`} testid="ctr-owed" tip="Shares of winning proofs on the ledger, not sent yet" />
      <HoneyTank i={2} shape="hex" tone="deep" level={lvl(sent)} label="SENT" value={solT(sent)} sub={usdOf(sent)} testid="ctr-sent" tip="SOL owners sent to the pot, each with a proof or a reason" />
      <HoneyTank i={3} shape="drop" tone="mint" level={lvl(paid)} label="PAID BACK" value={solT(paid)} sub={usdOf(paid)} testid="ctr-paid" tip="What the pot has paid out to sharers" />
    </div>
    <header className="ctr-cap"><b>🐝 THE COMB</b><small>{agents.length} agents · honey fills each cell</small></header>
    <ul className="ctr-comb" data-testid="ctr-comb">{agents.map((a, i) => <li key={a.id} className="ctr-cell" style={{ '--i': Math.min(i, 12) }}>
        <HoneyTank shape="hex" tone={a.pnlSol < 0 ? 'amber' : 'honey'} level={Math.abs(a.honey) / topHoney} label={a.name} value={`${a.honey > 0 ? '+' : ''}${a.honey} honey`} sub={a.kind === 'general' ? 'general' : 'trader'} />
        <span className="ctr-v"><em>RIGHT</em><u><s style={{ transform: `scaleX(${a.graded ? a.right / a.graded : 0})` }} /></u><b className="m-num">{a.graded ? `${a.right}/${a.graded}` : '—'}</b></span>
        <span className="ctr-v"><em>WON</em><u><s style={{ transform: `scaleX(${a.trades ? a.won / a.trades : 0})` }} /></u><b className="m-num">{a.won}/{a.trades}</b></span>
        <span className="ctr-n"><b className={`m-num ${a.pnlSol > 0 ? 'is-up' : a.pnlSol < 0 ? 'is-dn' : ''}`}>{sol4(a.pnlSol)}</b><small>{a.proofs} proofs{a.owedSol > 0 ? ` · owes ${solT(a.owedSol)}` : ''}{a.sharePct ? ` · ${a.sharePct}% share` : ''}</small></span>
      <button type="button" className="ctr-open" onClick={() => onOpen?.(a)} aria-label={`Open ${a.name}`} data-tip={`Open ${a.name}`} data-testid={`ctr-agent-${a.id}`} /></li>)}{!agents.length ? <li className="m-dim">{d ? 'No agents yet.' : 'Reading the colony…'}</li> : null}</ul>
    <header className="ctr-cap"><b>🏆 WINNING PROOFS</b><small>each one, and what it owes the pot</small></header>
    <ul className="ctr-wins" data-testid="ctr-wins">{wins.map((w, i) => <li key={w.id} className={`m-glass is-${w.state}`} style={{ '--i': Math.min(i, 12) }}><span className="m-chip">{w.kind}</span><b>${w.sym}</b><em className="m-num is-up">+{Number(w.pnlPct || 0).toFixed(1)}%</em><small>{w.agent} · {w.name}</small>
      <strong>{w.state === 'sent' ? <>🍯 {solT(w.honeySol)} sent{w.sig ? <a href={`https://solscan.io/tx/${w.sig}`} target="_blank" rel="noopener noreferrer" data-tip="See it on-chain"> tx ↗</a> : null}</> : w.state === 'owed' ? `⏳ owes ${solT(w.honeySol)}` : 'no share on'}</strong></li>)}{!wins.length ? <li className="m-dim">{d ? 'No winning real proof yet.' : '…'}</li> : null}</ul>
    <ColonyLedger rows={d?.ledger || []} fresh={fresh} ready={!!d} />
  </section>;
}

// 🏺 THE COLONY POT (owner 2026-10-31: "the smartest, next-level way of safe growth — I create a Circle wallet for it and pick how it's secured"):
// one Circle wallet; our server is the only one that can send from it, so it enforces the guards — the principal never leaves, at most the
// epoch cap of the GROWTH pays out, only to owners who signed to share winnings (split by what each shared), only after a timelocked approval.
// Opportunity 1 = the colony pool the owner opens with this wallet (assigned here); opportunity 2 = the sharers' airdrop (daily / weekly).
const usd = v => (v == null ? '—' : `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: Number(v) >= 100 ? 0 : 2 })}`);
const GUARD = { principalLock: ['🔒 Principal lock', 'What was staked or locked in never pays out — only growth'], allowlist: ['📜 Allowlist', 'Airdrops go only to owners who signed to share'], ownerSigns: ['✍ You approve', 'Every payout batch waits for your approval'] };
// ⛏ THE PoW ENGINE (owner 2026-10-31: "an official PoW engine in Fee's command center — Ultimate"): the hard rules every agent works under, the
// pipeline a colonized agent runs, the live numbers (filed · graded · right · strength) and the newest proofs. Reads the public /api/cats/pow.
const POW_STAGES = [['📥', 'INTAKE', 'one coin from the FEELESS intake'], ['🔎', 'SEARCH', 'DuckDuckGo first, DexScreener when walled'], ['🌐', 'SITES', '≤ {sites} sites · ≤ {steps} moves each'],
  ['🧪', 'VITALS', '≤ {pulls} vitals a site, numbers only'], ['⚖', 'CALL', 'BUY · WATCH · AVOID + why'], ['🍯', 'GRADED', 'an hour on, on what it really did']];
export function PowEngine({ limit = 12 }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [seen, setSeen] = useState(null);
  useEffect(() => { let on = true; const go = first => { if (first || !document.hidden) fetch(apiUrl(`/api/cats/pow?limit=${limit}`)).then(r => r.json()).then(x => { if (on) { setD(x); setErr(''); } }).catch(e => on && setErr(e.message)); };
    go(true); const t = setInterval(go, 30000); return () => { on = false; clearInterval(t); }; }, [limit]);
  const liveF = (d?.folders || []).find(x => x.live); const shown = seen ?? (liveF ? `${liveF.cat}-${liveF.folder?.id}` : '');   // a live folder is open until you pick another
  const rows = d?.rows || []; const r = d?.rules || {}; const graded = rows.filter(x => x.graded); const right = graded.filter(x => x.honey > 0).length;
  const avg = rows.length ? Math.round(rows.reduce((a, x) => a + (Number(x.strength) || 0), 0) / rows.length) : 0;
  const fill = t => t.replace('{sites}', r.sites ?? 4).replace('{steps}', r.steps ?? 5).replace('{pulls}', r.pulls ?? 3);
  return <article className="fch-card fch-wide hv-pow m-live" data-testid="pow-engine">
    <h4>⛏ PROOF OF WORK ENGINE<small>every colonized agent · one intake coin per {r.everyMin ?? 30} min · rules are code, the same for every model</small></h4>
    <ol className="hv-pow-flow" aria-label="The PoW pipeline">{POW_STAGES.map(([ic, k, t], i) => <li key={k} style={{ '--i': i }} data-tip={fill(t)}><b aria-hidden="true">{ic}</b><em>{k}</em><small>{fill(t)}</small></li>)}</ol>
    <div className="hv-pow-stats">{[['FILED', rows.length, 'Proofs in this list'], ['GRADED', graded.length, 'Judged an hour after the call'], ['RIGHT', graded.length ? `${Math.round(100 * right / graded.length)}%` : '—', 'Graded calls that earned honey'],
      ['STRENGTH', avg, 'Average work behind a call: sites with vitals, distinct vitals, safety vitals, a vital confirmed twice']].map(([k, v, tip]) =>
      <span key={k} data-tip={tip}><em>{k}</em><b className="m-num" key={v}>{v}</b></span>)}</div>
    {(d?.folders || []).length ? <div className="hv-pow-db" data-testid="pow-db"><b className="hv-pow-db-h">🗄 EVERY AGENT'S PoW FOLDERS · tap one to open it</b>
      <ul className="hv-pow-shelf">{d.folders.map(x => { const k = `${x.cat}-${x.folder?.id}`; const p = x.folder?.pnlPct; return <li key={k}><button type="button" className={`${shown === k ? 'on' : ''}${x.live ? ' is-live' : ''}`} aria-expanded={shown === k} onClick={() => setSeen(shown === k ? '' : k)} data-tip={x.folder?.why || x.folder?.name} data-testid={`pow-shelf-${x.folder?.id}`}><b>{x.folder?.sym ? `$${x.folder.sym}` : x.folder?.name}</b><small>{x.name}{x.live ? ' · ● live' : ''}</small><em className={`m-num ${p > 0 ? 'is-up' : p < 0 ? 'is-dn' : ''}`}>{p == null ? (x.live ? 'live' : '—') : `${p >= 0 ? '+' : ''}${p}%`}</em></button></li>; })}</ul>
      {(() => { const x = d.folders.find(y => `${y.cat}-${y.folder?.id}` === shown); return x ? <div className="hv-pow-db-row"><FolderView f={x.folder} live={x.live} catId={x.cat} /></div> : null; })()}</div> : null}
    {rows.length ? <div className="hv-pow-grid">{rows.map((x, i) => <div key={x.id} className="hv-pow-cell" style={{ '--i': i }}><small className="hv-pow-by">{x.name}</small><PowCard p={x} compact /></div>)}</div>
      : (d?.folders || []).length ? null : <p className="fch-nil">{err || 'No proof filed yet — colonize an agent (🐝 Colonize on its desk) and its next free moment researches an intake coin.'}</p>}
  </article>;
}

export function ColonyPot({ call }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState('');
  const [pool, setPool] = useState(''); const [plat, setPlat] = useState(''); const seeded = useRef(false);
  const take = x => { if (x && 'policy' in x) { setD(x); setErr(''); if (!seeded.current) { seeded.current = true; setPool(x.poolDraft?.amountA ? String(x.poolDraft.amountA) : ''); setPlat(x.poolDraft?.amountB ? String(x.poolDraft.amountB) : ''); } } else setErr('The colony did not answer.'); };
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
          <form className="hv-pot-pool" onSubmit={e => e.preventDefault()} data-tip="Opportunity 1: the colony's own FEECAT / SOL pool on Meteora — fees compound into it, the colony wallet pays, nothing is sent until you create">
            <span>🌊 COLONY POOL {d.pool ? <em className="is-on">OPEN · {d.pool.platform}</em> : <em>Meteora · not open</em>}</span>
            {d.pool ? <small className="hv-pool-addr"><code>{d.pool.address.slice(0, 6)}…{d.pool.address.slice(-6)}</code>{d.pool.sol ? ` · ${d.pool.feecat?.toLocaleString()} FEECAT + ${d.pool.sol} SOL` : ''}{d.pool.lock ? ' · liquidity locked' : ''}</small> : <>
              <label><small>FEECAT in</small><input className="m-input" inputMode="decimal" value={pool} onChange={e => setPool(e.target.value)} placeholder="1,000,000" aria-label="FEECAT to put in the pool" data-testid="colony-pool-feecat" /></label>
              <label><small>SOL in</small><input className="m-input" inputMode="decimal" value={plat} onChange={e => setPlat(e.target.value)} placeholder="0.5" aria-label="SOL to put in the pool" data-testid="colony-pool-sol" /></label>
              {Number(pool) > 0 && Number(plat) > 0 ? <small className="hv-pool-px">starts at {(Number(plat) / Number(pool)).toPrecision(3)} SOL per FEECAT · fees compound into it · liquidity stays unlocked</small> : null}
              <span className="hv-pool-acts"><button type="button" className="m-btn" disabled={!!busy || !(Number(pool) > 0 && Number(plat) > 0)} onClick={() => act('pool_preview', { feecat: Number(pool), sol: Number(plat) })} data-testid="colony-pool-preview"
                data-tip="Builds the real transaction with Meteora's SDK and simulates it on Solana — free, nothing signed or sent">{busy === 'pool_preview' ? 'Simulating…' : '🔍 Preview (free)'}</button>
                <button type="button" className="m-btn m-go" disabled={!!busy || !(d.poolDraft?.ok && d.poolDraft.amountA === Number(pool) && d.poolDraft.amountB === Number(plat))}
                  onClick={() => window.confirm(`Create the colony pool on Meteora with ${Number(pool).toLocaleString()} FEECAT + ${plat} SOL from the colony wallet? The liquidity is LOCKED (it stays in the pool for good, earning compounding fees).`) && act('pool_create', { feecat: Number(pool), sol: Number(plat) })}
                  data-testid="colony-pool-create" data-tip="Circle signs it as the colony wallet and it is sent — only after a clean preview of these exact amounts">{busy === 'pool_create' ? 'Creating…' : '🌊 Create the pool'}</button></span>
              {d.poolDraft ? <small className={`hv-pool-sim ${d.poolDraft.ok ? 'is-ok' : 'is-bad'}`} data-testid="colony-pool-sim">{d.poolDraft.ok ? `✓ simulation passed · pool ${String(d.poolDraft.pool).slice(0, 6)}…` : `✗ simulation: ${String(d.poolDraft.err).includes('AccountNotFound') ? 'the colony wallet has no SOL yet — fund it first' : String(d.poolDraft.err).slice(0, 90)}`}</small> : null}</>}</form>
          <div className="hv-pot-set"><label><span>🪂 AIRDROP<b className="m-num">{d.sharers}</b><small>signed sharers · {d.sharedSol} SOL shared, unsent</small></span>
            <span className="m-seg" role="group" aria-label="How often the airdrop pays">{[['daily', 'Every 24 h'], ['weekly', 'Weekly']].map(([k, l]) => <button key={k} type="button" className={d.policy.cadence === k ? 'active' : ''} aria-pressed={d.policy.cadence === k} disabled={!!busy} onClick={() => act('policy', { policy: { cadence: k } })} data-testid={`colony-cadence-${k}`}>{l}</button>)}</span></label>
            <label data-tip="Agents only ever send to ONE place — the colony wallet. This picks where those shares end up: kept in the wallet, or added to the colony pool (once it is open)"><span>🤝 SHARES LAND IN<small>{d.policy.dest === 'pool' ? (d.pool ? 'the colony pool' : 'the pool — not open yet, they wait in the wallet') : 'the colony wallet'}</small></span>
              <span className="m-seg" role="group" aria-label="Where shared winnings land">{[['wallet', '🏺 Colony wallet'], ['pool', '🌊 Colony pool']].map(([k, l]) => <button key={k} type="button" className={(d.policy.dest || 'wallet') === k ? 'active' : ''} aria-pressed={(d.policy.dest || 'wallet') === k} disabled={!!busy} onClick={() => act('policy', { policy: { dest: k } })} data-testid={`colony-dest-${k}`}>{l}</button>)}</span></label></div>
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
  else if (w?.screen && !bad) body = <img src={apiUrl(w.last ? `/api/cats/${a.id}/last/${w.slot ?? w.i}` : `/api/cats/${a.id}/screen/${w.i}?t=${tick}`)} alt={`${a.name}'s window ${side}`} loading="lazy" onError={() => setBad(true)} />;
  else if (a.status === 'working' || w?.status === 'working') body = <span className="cl-off"><i className="cl-scan" aria-hidden="true" />loading the screen…</span>;
  else body = <span className="cl-desk" aria-label="idle — its desktop"><i className="cl-desk-glow" aria-hidden="true" /><b className="cl-desk-mark" aria-hidden="true">FEELESS</b>   {/* 🖥 idle = its desktop (owner 2026-11-01) */}
    <span className="cl-desk-icons" aria-hidden="true"><i className="is-v" /><i className="is-p" /><i className="is-h" /><i className="is-f" /></span>
    <span className="cl-desk-bar" aria-hidden="true"><u /><em>{a.kind === 'trading' ? 'trader · idle' : 'idle'}</em></span></span>;
  return <span className={`cl-scr${w?.status === 'working' ? ' is-go' : ''}`} data-testid={`cl-scr-${a.id}-${side}`}>
    <span className="cl-bar"><i /><i /><i /><b>{host}</b>{w?.last && !a.incognito ? <em className="cl-last">LAST PAGE</em> : w?.status === 'working' ? <em className="cl-rec">● LIVE</em> : null}</span>
    <span className="cl-view">{body}{a.incognito || w?.frozen ? null : <AiCursor c={w?.cursor} kind={readCursor()} />}<small className="cl-model">{side} · {w?.model || a.brains?.[side === 'A' ? 0 : 1] || '—'}</small></span></span>;
}
function ColonyCell({ a, onOpen, i, top, extra }) {
  const ref = useRef(null); const seen = useSeen(ref); const [tick, setTick] = useState(0); const live = a.windows?.some(w => w.status === 'working');
  useEffect(() => { if (!seen || !live) return undefined; const t = setInterval(() => { if (!document.hidden) setTick(x => x + 1); }, 5000); return () => clearInterval(t); }, [seen, live]);
  const wins = [0, 1].map(k => a.windows?.find(w => w.i === k) || a.windows?.[k] || null);
  const c = a.last; const seenAt = useRef(a.carrying?.at); const [drop, setDrop] = useState(null);
  useEffect(() => { const t = a.carrying?.at; if (!t || t === seenAt.current) return undefined; seenAt.current = t; setDrop(a.carrying.text); const k = setTimeout(() => setDrop(null), 2600); return () => clearTimeout(k); }, [a.carrying?.at, a.carrying?.text]);   // 🗄 a NEW keep drops into the agent
  return <article ref={ref} className={`cl-cell${a.colonized ? ' is-col' : ''}${live ? ' is-go' : ''}`} style={{ '--i': i }} data-testid={`cl-${a.id}`}>
    <header className="cl-foot">
      <button type="button" className="cl-who" onClick={() => onOpen?.(a)} data-tip={`Open ${a.name}'s desk`}><i className={`cl-dot${live ? ' is-go' : ''}`} aria-hidden="true" /><b>{a.name}</b><small>{a.kind === 'general' ? 'GENERAL' : 'TRADER'} · LVL {a.level || 1}{a.colonized ? ' · 🐝 COLONIZED' : ''}</small></button>
      <small className={`cl-carry${drop ? ' is-new' : ''}`} data-tip="What it stored last — it goes into its drawer">› {a.carrying ? <>carrying “{a.carrying.text}” to its drawer</> : a.status === 'working' ? 'reading — nothing kept yet' : 'nothing carried yet'}</small>
      {drop ? <span className="cl-drop" key={a.carrying.at} aria-hidden="true" data-testid={`cl-drop-${a.id}`}>🗄 {drop}</span> : null}
      {c ? <span className={`cl-call ${CALL[c.call] || ''}${c.honey > 0 ? ' is-right' : c.honey < 0 ? ' is-wrong' : ''}`} data-tip={`${c.call} $${c.sym} — ${c.why}`}>{c.call} ${c.sym}<em>{c.honey == null ? '⏳' : `${c.honey > 0 ? '+' : ''}${c.honey}`}</em></span> : <span className="cl-call is-none">no call yet</span>}
      <span className="cl-honey" data-tip={`${a.honey} honey this epoch · ${a.right}/${a.graded} graded calls right`}><em>🍯</em><b className={`m-num ${a.honey < 0 ? 'is-dn' : ''}`} key={a.honey}>{a.honey > 0 ? '+' : ''}{a.honey}</b>
        <i aria-hidden="true"><u className={a.honey < 0 ? 'is-dn' : ''} style={{ transform: `scaleX(${Math.max(0.04, Math.min(1, Math.abs(a.honey) / Math.max(1, top)))})` }} /></i><small>{a.right}/{a.graded} right</small></span>
      {extra ? extra(a) : null}
    </header>
    <div className="cl-stage"><ColonyScreen a={a} w={wins[0]} side="A" tick={tick} /><ColonyScreen a={a} w={wins[1]} side="B" tick={tick} /></div>
  </article>;
}
export function ColonyGrid({ api, onOpen, ids, extra }) {
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
      <p>Every agent's two windows, live — an idle one shows its desktop. Colonized agents file graded calls and their trades are graded before and after; honey splits the colony pot's growth.</p></header>}
    {err && !rows.length ? <p className="hv-nil">{err}</p> : null}
    {ids ? null : <ColonyFlow api={api} onOpen={onOpen} />}   {/* 🐝 the live loop at the TOP (owner 2026-11-01) */}
    {ids ? null : <ColonyManual />}
    <div className="cl-grid">{rows.map((a, k) => <ColonyCell key={a.id} a={a} onOpen={onOpen} i={k % 10} top={top} extra={extra} />)}</div>
    <span ref={end} className="cl-end" aria-hidden="true">{meta?.more ? 'more agents…' : null}</span>
  </section>;
}

import React, { Suspense, lazy, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { apiUrl } from '../../lib/api';
import { AgentLog, SafeGate, safeOk } from './CatCockpit';
import { ApiDrawer } from './LaunchCat';
import '../../styles/agentDemo.css';
import '../../styles/catWorkbench.css';
import { agentAuth, agentAuthQuery, revealMessage, getChatSession } from '../../lib/chatSession';
import { svgPngBlob } from '../../lib/svgPng';
import { useWallet } from '../../hooks/useWallet';
import { useSolPrice } from '../../lib/solPrice';
import { FirstTips } from '../FirstTips';

// 🧠🧠 THE GENERAL CAT'S WORKBENCH (owner 2026-10-29, P2 — backend cat_agent.py + cat_browser.py). Two browser windows, one per model, running in
// the cloud (Steel → Browserbase → the reader: never on this device). Each window: its model, its provider, the page it is on, a bubble top-right
// with what it is doing right now, and — when a sign-in / sign-up / CAPTCHA needs a person — a centred ✋ card (you act in the live window, then
// CONTINUE). Under them ONE chat: Enter → a fast answer from memory, or both models research their halves and merge. The $ bars: the cat's credit
// left and THIS task's spend against its cap (you set it; the task stops at it). Live views run only while on screen; polling pauses when hidden.
const CAPS = [0.02, 0.05, 0.25, 1];
const PROV = { steel: ['STEEL', 'is-steel'], browserless: ['BROWSERLESS', 'is-bl'], browserbase: ['BROWSERBASE', 'is-bb'], reader: ['READER', 'is-reader'] };
const usd = v => (v == null ? '—' : `$${Number(v) < 1 ? Number(v).toFixed(4) : Number(v).toFixed(2)}`);
const LIVE_STATES = ['planning', 'working', 'merging'];
const PriceChart = lazy(() => import('../terminal/PriceChart').then(m => ({ default: m.PriceChart })));
// 🧭 its two ways (cat_agent.MODES): plan together → one answer · each mind its own job
const WAYS = [['plan', '🧠🤝 ONE ANSWER', 'They plan it in a sentence each, split it, research in their own windows, merge into one answer'], ['jobs', '🎯🎯 TWO JOBS', 'Give each mind its own job — both run at once, two results']];

// 🛟 the agent service not answering (a restart, a 502 / 503 / 504 from the proxy) says so in plain words — never a bare "HTTP 504"
const DOWN = 'The agent service is not answering right now (it may be restarting) — nothing was sent. Try again in a few seconds.';
async function work(id, body) {
  let r;
  try { r = await fetch(apiUrl(`/api/cats/${id}/work`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...agentAuth(), ...body }) }); } catch { throw Object.assign(new Error(DOWN), { down: true }); }
  const j = await r.json().catch(() => ({}));
  if (r.status >= 502 && r.status <= 504) throw Object.assign(new Error(DOWN), { down: true });
  if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`);
  return j;
}

function useOnScreen(ref) {
  const [on, setOn] = useState(true);
  useEffect(() => { const el = ref.current; if (!el || typeof IntersectionObserver === 'undefined') return undefined;
    const io = new IntersectionObserver(([e]) => setOn(e.isIntersecting), { threshold: 0.05 }); io.observe(el); return () => io.disconnect(); }, [ref]);
  return on;
}

function Window({ w, catId, tick, onGo, onLogin, busy }) {
  const ref = useRef(null); const seen = useOnScreen(ref);
  const [p, pcls] = PROV[w?.provider] || ['…', ''];
  const human = w?.status === 'human' && w?.human; const [big, setBig] = useState(false);
  const i = w?.i ?? 0; const working = w?.status === 'working';
  // 🪟 the live window wears the demo's chrome (owner 2026-10-30: "the window design is perfected — users should see exactly that, bigger")
  return <article ref={ref} className={`agd-win cwb-win w${i % 2} s-${w?.status || 'idle'}`} data-testid={`cwb-win-${i}`}>
    <span className={`agd-bar${working ? ' is-go' : ''}`} data-tip="red = idle · yellow = needs you · green = working"><i /><i /><i /><b>MIND {'AB'[i] || i + 1}</b>
      <small data-tip={w?.goal ? `Its half: ${w.goal}` : 'Waiting for the plan'}>{w?.model ? String(w.model).split('/').pop() : 'model'}{w?.goal ? ` · ${w.goal}` : ''}</small>
      <em className={`cwb-prov ${pcls}`} data-tip={w?.note || (w?.provider === 'reader' ? 'No live browser right now — it reads pages as text so it keeps working' : 'A browser in the cloud — nothing runs on your device')}>{p}</em>
      <em className={`agd-live${working ? '' : ' is-off'}`}>● {working ? 'LIVE' : String(w?.status || 'idle').toUpperCase()}</em></span>
    <div className="agd-browser is-rec cwb-browser">
    <span className="agd-url" title={w?.url || ''}><i aria-hidden="true">🔒</i><b>{w?.url ? String(w.url).replace(/^https?:\/\//, '') : 'about:blank'}</b>{working ? <u className="agd-caret" aria-hidden="true" /> : null}{working ? <em className="agd-rec">● REC</em> : <small className="m-num">{usd(w?.cost || 0)}</small>}</span>
    <div className="agd-screen cwb-view">
      {w?.coin?.pair && seen ? <div className="cwb-chart" data-testid="cwb-chart"><Suspense fallback={<span className="cwb-chart-load">loading ${w.coin.symbol} on FEELESS…</span>}>
        <PriceChart key={w.coin.pair} pair={{ chainId: 'solana', pairAddress: w.coin.pair, baseToken: { address: w.coin.mint, symbol: w.coin.symbol } }} interval="1m" metric="price" showVolume={false} /></Suspense>
        <em className="cwb-chart-tag">FEELESS · ${w.coin.symbol}</em></div>
        : w?.live && seen ? <iframe className={`cwb-live${w.hand ? ' is-hand' : ''}`} src={w.live} tabIndex={w.hand ? 0 : -1} title={`${w.model} browser`} sandbox="allow-scripts allow-same-origin allow-forms allow-popups" allow="clipboard-read; clipboard-write" data-testid="cwb-live" />
        : w?.shot && seen ? <img className="cwb-shot" src={apiUrl(`/api/cats/${catId}/work/shot/${w.i}?${agentAuthQuery()}&t=${tick}`)} alt={`${w.model} window`} data-testid="cwb-shot" />
          : <ol className="cwb-steps" data-testid="cwb-steps">{w?.provider === 'reader' && w?.note ? <li className="cwb-idle" data-testid="cwb-noview"><span>no live browser · {w.note}</span></li> : null}{(w?.steps || []).length ? w.steps.map((s, i) => <li key={i} style={{ '--i': i }}><b>{s.action}</b><span>{s.thought}</span>{s.detail ? <small>{s.detail}</small> : null}</li>)
            : <li className="cwb-idle"><span>{w?.status === 'done' ? (w?.answer ? 'done — its answer is in the chat' : 'done') : 'ready — ask below'}</span></li>}</ol>}
      {w?.hand && w?.live ? <button type="button" className="m-btn cwb-big" onClick={() => setBig(true)} data-tip="It needs you: open its window big to click / sign in yourself" data-testid="cwb-big">⤢ Big</button> : null}
      {big && w?.hand && w?.live ? <AgentDesktop cat={{ id: catId }} live={{ live: w.live, site: w?.human?.site, title: `MIND ${'AB'[i] || i + 1} needs you${w?.human?.why ? ` — ${w.human.why}` : ''}` }} onClose={() => setBig(false)} /> : null}
      {w?.bubble && w?.status !== 'idle' ? <p className={`agd-done is-on cwb-say at-${i % 2 ? 'right' : 'left'}`} key={w.bubble} data-testid="cwb-bubble">MIND {'AB'[i] || i + 1} · {w.bubble}</p> : null}
      {human && w.human.kind === 'login' ? <div className="cwb-human cwb-signin" role="alertdialog" aria-label={`Sign in to ${w.human.site}`} data-testid="cwb-login">
        <b>🔑 {w.human.site} needs a sign-in</b><small>It goes in the credentials drawer, sealed — the AI models never see it.</small>
        <span><button type="button" className="m-btn m-go" disabled={busy} onClick={() => onLogin?.(w.human.site)} data-tip="Opens the credentials drawer with this site filled in" data-testid="cwb-login-go">Click to sign in</button>
          <button type="button" className="m-btn" disabled={busy} onClick={() => onGo('stop_window', w.i)}>Stop</button></span></div>
      : human ? <div className="cwb-human" role="alertdialog" aria-label="A person is needed" data-testid="cwb-human"><b>✋ needs you</b><small>{w.human.why}</small>
        <span><button type="button" className="m-btn m-go" disabled={busy} onClick={() => onGo('continue', w.i)} data-testid="cwb-continue">I did it — continue</button>
          <button type="button" className="m-btn" disabled={busy} onClick={() => onGo('stop_window', w.i)} data-testid="cwb-stopwin">Stop</button></span></div> : null}
    </div></div>
  </article>;
}

// 🧠 a general mind's vitals beside the chat: what its window is doing right now (owner 2026-10-30: "model vitals on each side")
// 🕷→🐱 WHAT IT'S DOING NOW (the crawl idea, our way): one terminal line — its handle › the site its busiest window is on: what it's doing
export function NowLine({ cat, wins, live }) {
  const w = wins.find(x => x.status === 'human') || wins.find(x => x.status === 'working') || wins.find(x => x.url);
  const host = String(w?.url || '').replace(/^https?:\/\//, '').split('/')[0];
  const what = !live || !w ? 'idle — waiting for your ask' : w.status === 'human' ? `waiting on you at ${host}` : `${host ? `on ${host}: ` : ''}${String(w.bubble || w.steps?.at(-1)?.thought || 'thinking').replace(/^✋ needs you: /, '')}`;
  return <p className={`cwb-now${live ? ' is-live' : ''}`} data-testid="cwb-now" aria-live="polite"><b>{cat.handle || 'agent'}</b><i aria-hidden="true">›</i><span key={what}>{what}</span></p>;
}
// ⚡ EARN MODE (owner 2026-10-30): when nobody is asking, it plans what its money could earn on FEELESS — open price gaps that beat their
// costs, then compounding (Night Vault), then the busiest bands — for YOUR risk. It never signs: each play opens its Launch › Pools tab.
const EARN_ICON = { gap: '⚡', vault: '🌙', range: '🤖', pool: '🌊' };
export function EarnCard({ cat }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);
  const load = useCallback(() => fetch(apiUrl(`/api/cats/${cat.id}/earn?${agentAuthQuery()}`)).then(r => r.json().then(j => (r.ok ? (setD(j), setErr('')) : setErr(j.detail || `HTTP ${r.status}`)))).catch(e => setErr(e.message)), [cat.id]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, 60000); return () => clearInterval(t); }, [load]);
  const e = d?.earn || { on: false, risk: 'safe', budgetUsd: 25 };
  const save = async next => { setBusy(true); setErr('');
    try { const r = await fetch(apiUrl(`/api/cats/${cat.id}/action`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...agentAuth(), action: 'earn', earn: { ...e, ...next } }) });
      const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`); await load(); } catch (er) { setErr(er.message); } finally { setBusy(false); } };
  const plays = d?.plays || [];
  return <section className={`cwb-earn${e.on ? ' is-on' : ''}`} data-testid="cwb-earn">
    <header><button type="button" className={`cwb-earn-sw${e.on ? ' is-on' : ''}`} role="switch" aria-checked={e.on} disabled={busy} onClick={() => save({ on: !e.on })}
      data-tip={e.on ? 'Earn Mode ON: when you are not asking it anything, it keeps this plan fresh — you sign each play' : 'Turn on Earn Mode: it plans what its money could earn on FEELESS when idle'} data-testid="cwb-earn-sw"><i aria-hidden="true" />⚡ EARN MODE <b>{e.on ? 'ON' : 'OFF'}</b></button>
      <div className="m-seg" role="radiogroup" aria-label="Earn risk">{['safe', 'mid', 'risky'].map(k => <button key={k} type="button" role="radio" aria-checked={e.risk === k} className={e.risk === k ? 'active' : ''} disabled={busy} onClick={() => save({ risk: k })}
        data-tip={k === 'safe' ? 'Gaps, staking, stables, lending, big pools without impermanent loss' : k === 'mid' ? '+ auto-compound vaults and mid pools' : '+ loops, small pools, 100%+ APY'} data-testid={`cwb-earn-${k}`}>{k.toUpperCase()}</button>)}</div>
      <label className="cwb-earn-amt" data-tip="The $ it plans with (its wallet + yours) — the $/day below is on this amount"><em>$</em><input className="m-input" type="number" min="1" step="1" defaultValue={e.budgetUsd} key={e.budgetUsd} onBlur={x => Number(x.target.value) !== e.budgetUsd && save({ budgetUsd: Number(x.target.value) })} aria-label="Dollars to plan with" data-testid="cwb-earn-amt" /></label></header>
    {plays.length ? <ol className="cwb-earn-list">{plays.map((p, i) => <li key={`${p.kind}-${p.title}`} style={{ '--i': i }} className={`t-${p.tier}`}><span className="cwb-earn-ico" aria-hidden="true">{EARN_ICON[p.kind]}</span>
      <span className="cwb-earn-what"><b>{p.title}</b><small>{p.sub}</small></span><span className="cwb-earn-num"><b className="m-num">+${p.dayUsd < 0.01 ? p.dayUsd.toFixed(4) : p.dayUsd.toFixed(2)}</b><small>{p.kind === 'gap' ? 'once' : `/day · ${p.apy}%`}</small></span>
      <a className="m-btn" href={`/terminal/launch?mode=pools&tab=${p.tab}`} data-tip={`${p.why} — opens Launch › Pools`} data-testid={`cwb-earn-go-${i}`}>Open ↗</a></li>)}</ol>
      : <p className="cwb-cloud-empty">{d ? `Nothing worth it at ${e.risk.toUpperCase()} right now${d.gapsOpen ? '' : ' — no price gap beats its costs'}.` : 'Reading gaps, vaults and pools…'}</p>}
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}</section>;
}
// 🏦 ITS TREASURY (owner 2026-10-31): its own coin's creator fees, read on-chain now (pump.fun's vault, PumpSwap's after it graduates), and how
// they split — the Pass holder · its model credit · a capped buyback of its own coin (fees only, shown here). Claiming + paying out from its
// wallet is the next step, tested live by the owner first.
const SPLIT_PRESETS = [['Balanced', { holder: 50, credit: 30, buyback: 20 }], ['Holder first', { holder: 70, credit: 20, buyback: 10 }], ['Self-funding', { holder: 30, credit: 60, buyback: 10 }], ['Momentum', { holder: 40, credit: 20, buyback: 40 }]];
// 🔑 the API drawer as a cabinet slot (owner 2026-10-31): its own keys, sealed on the server — only the last 4 ever come back
function ApiSlot({ cat }) {
  const [rows, setRows] = useState(cat?.apiDrawer || []); const [draft, setDraft] = useState({}); const [busy, setBusy] = useState(false); const [err, setErr] = useState('');
  const send = async (provider, secret) => { setBusy(true); setErr('');
    try { const r = await fetch(apiUrl(`/api/cats/${cat.id}/action`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...agentAuth(), action: 'api_key', provider, secret }) });
      const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`); setRows(j.cat?.apiDrawer || []); setDraft(x => ({ ...x, [provider]: '' })); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  return <div data-testid="cwb-api"><ApiDrawer start rows={rows} draft={draft} busy={busy} onDraft={(k, v) => setDraft(x => ({ ...x, [k]: v.trim() }))} onSave={send} onDrop={k => send(k, '')} />
    {err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}</div>;
}
export function TreasuryDrawer({ cat }) {
  const px = useSolPrice(); const [t, setT] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false); const [mint, setMint] = useState('');
  const load = useCallback(() => fetch(apiUrl(`/api/cats/${cat.id}/treasury?${agentAuthQuery()}`)).then(r => r.json().then(j => (r.ok ? (setT(j), setMint(j.mint || '')) : setErr(j.detail || `HTTP ${r.status}`)))).catch(e => setErr(e.message)), [cat.id]);
  useEffect(() => { load(); const id = setInterval(() => { if (!document.hidden) load(); }, 60000); return () => clearInterval(id); }, [load]);
  const save = async next => { setBusy(true); setErr('');
    try { const r = await fetch(apiUrl(`/api/cats/${cat.id}/action`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...agentAuth(), action: 'treasury', treasury: { mint, split: t?.split, ...next } }) });
      const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`); await load(); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  const sol = l => `${(Number(l || 0) / 1e9).toFixed(4)} SOL${px ? ` ($${((Number(l || 0) / 1e9) * px).toFixed(2)})` : ''}`;
  const sp = t?.split || { holder: 50, credit: 30, buyback: 20 };
  return <div className="cwb-tre" data-testid="cwb-treasury">
    <b className="cwb-pass-num">🏦 ITS TREASURY</b>
    <small>Its own coin's creator fees land here. You set how they split; buybacks come from these fees only, capped at {t?.buybackMax ?? 50}%.</small>
    <label className="cwb-tre-mint"><em>ITS COIN</em><input className="m-input" value={mint} onChange={e => setMint(e.target.value.trim())} placeholder="its coin address — or ask it: launch my coin" aria-label="Its coin address" data-testid="cwb-tre-mint" />
      <button type="button" className="m-btn" disabled={busy || mint === (t?.mint || '')} onClick={() => save({ mint })}>Save</button></label>
    <div className="cwb-tre-fees" data-tip="Read on-chain now from its creator vaults (pump.fun + PumpSwap)"><em>FEES WAITING</em><b className="m-num" data-testid="cwb-tre-total">{t ? sol(t.fees?.total) : '…'}</b>
      <small>{t?.creator ? `for its wallet ${t.creator.slice(0, 4)}…${t.creator.slice(-4)}` : 'give it its own wallet first (👛 Wallet)'}</small></div>
    <div className="m-seg cwb-tre-presets" role="radiogroup" aria-label="How its fees split">{SPLIT_PRESETS.map(([l, v]) => { const on = v.holder === sp.holder && v.credit === sp.credit && v.buyback === sp.buyback;
      return <button key={l} type="button" role="radio" aria-checked={on} className={on ? 'active' : ''} disabled={busy} onClick={() => save({ split: v })} data-testid={`cwb-tre-${l}`}
        data-tip={`${v.holder}% to the Pass holder · ${v.credit}% model credit · ${v.buyback}% buyback`}>{l}</button>; })}</div>
    <div className="cwb-tre-split">{[['holder', '🎫 PASS HOLDER'], ['credit', '🧠 MODEL CREDIT'], ['buyback', '🔁 BUYBACK']].map(([k, l]) => <span key={k} className={`k-${k}`}>
      <em>{l}</em><b className="m-num">{sp[k]}%</b><u aria-hidden="true"><s style={{ transform: `scaleX(${sp[k] / 100})` }} /></u><small>{t ? sol(t.plan?.[k]) : '…'}</small></span>)}</div>
    <p className="m-note"><b>Next</b>Claiming these fees from its wallet and paying out the split comes after your live test.</p>
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}</div>;
}
// 🎫 ITS AGENT PASS (owner 2026-10-31): a numbered NFT of this agent, minted to YOUR wallet after its recovery PIN — the mint fee (HQ; default
// 2× Solana's cost) and a 10% resale royalty go to FEELESS, the fee wallet keeps the royalty locked in. FEELESS records it only after checking it on-chain.
export function PassDrawer({ cat }) {
  const { wallet, signMessage, provider } = useWallet() || {}; const px = useSolPrice();
  const [r, setR] = useState(null); const [stage, setStage] = useState(''); const [err, setErr] = useState(''); const [done, setDone] = useState(cat?.pass || null);
  useEffect(() => { let on = true; fetch(apiUrl('/api/reputation/agent-pass/rules')).then(x => (x.ok ? x.json() : null)).then(j => on && j && setR(j)).catch(() => {}); return () => { on = false; }; }, []);
  const sol = l => (Number(l || 0) / 1e9).toFixed(4); const usdOf = l => (px ? ` ($${((Number(l || 0) / 1e9) * px).toFixed(2)})` : '');
  const mint = async () => { setErr('');
    try {
      const addr = wallet?.address; if (!addr) throw new Error('Connect the owner wallet first.');
      setStage('Signing you in…'); const session = await getChatSession(addr, signMessage, { own: true });
      setStage('Drawing its picture…'); const { blob } = await svgPngBlob(document.querySelector('.kd-stage svg'));
      const dataUrl = await new Promise((ok, no) => { const f = new FileReader(); f.onload = () => ok(f.result); f.onerror = () => no(new Error('Its picture could not be read.')); f.readAsDataURL(blob); });
      const post = async (path, body) => { const x = await fetch(apiUrl(path), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); const j = await x.json().catch(() => ({})); if (!x.ok) throw new Error(j.detail || `HTTP ${x.status}`); return j; };
      setStage('Uploading its picture…'); const up = await post('/api/reputation/uploads', { dataUrl });
      setStage('Numbering its Pass…'); const prep = await post(`/api/reputation/agent-pass/${cat.id}/prepare`, { address: addr, session, image: up.url });
      const { coreMintPass } = await import('../../lib/metaplexCore');
      const m = await coreMintPass({ provider, owner: addr, name: prep.name, uri: prep.uri, feeWallet: prep.feeWallet, feeLamports: prep.feeLamports, royaltyBps: prep.royaltyBps, onStatus: setStage });
      setStage('Checking it on-chain…'); const c = await post(`/api/reputation/agent-pass/${cat.id}/confirm`, { address: addr, session, signature: m.signature, asset: m.asset });
      setDone({ number: c.number, asset: c.asset }); setStage('');
    } catch (e) { setErr(e.message || 'The mint did not finish — nothing was recorded.'); setStage(''); } };
  if (done?.asset) return <div className="cwb-pass is-minted" data-testid="cwb-pass"><b className="cwb-pass-num">🎫 AGENT PASS #{String(done.number || 0).padStart(4, '0')}</b>
    <small>In your wallet · 10% of every resale goes to FEELESS</small><a className="m-btn" href={`https://explorer.solana.com/address/${done.asset}`} target="_blank" rel="noopener noreferrer">See it on-chain ↗</a></div>;
  const blocked = !cat?.recoveryConfirmedAt ? 'Confirm its recovery PIN first (👛 Wallet tab) — the Pass comes after its safe-keeping.' : r && !r.ready ? r.why : '';
  return <div className="cwb-pass" data-testid="cwb-pass"><b className="cwb-pass-num">🎫 MINT ITS AGENT PASS</b>
    <small>A numbered NFT of this agent, minted to your wallet. Whoever holds it holds the agent — sell it later on the FEELESS marketplace or any Core marketplace.</small>
    {r ? <div className="cwb-pass-kv"><span><em>MINT FEE</em><b className="m-num">{sol(r.feeLamports)} SOL{usdOf(r.feeLamports)}</b></span><span><em>SOLANA'S COST</em><b className="m-num">{sol(r.providerLamports)} SOL</b></span>
      <span><em>RESALE ROYALTY</em><b className="m-num">{(r.royaltyBps || 0) / 100}% → FEELESS</b></span></div> : <small>Reading the mint fee…</small>}
    {blocked ? <p className="m-note warn" data-testid="cwb-pass-blocked">{blocked}</p>
      : <button type="button" className="m-btn m-go" disabled={!r || !!stage} onClick={mint} data-tip="Your wallet signs once: the Pass + its mint fee in one transaction" data-testid="cwb-pass-mint">{stage || 'Mint its Agent Pass'}</button>}
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}</div>;
}
// 💵 the last money it made — stays until a newer one lands
function LastMoney({ m }) {
  const px = useSolPrice();
  if (m && m.usd == null && m.sol != null && px) m = { ...m, usd: Number(m.sol) * px };
  if (!m) return <div className="cwb-money is-none" data-testid="cwb-money" data-tip="The last money it made shows here until a newer one lands"><em>LAST MONEY MADE</em><b className="m-num">—</b><small>nothing yet</small></div>;
  const up = Number(m.usd ?? m.sol) >= 0;
  return <div className={`cwb-money ${up ? 'is-up' : 'is-dn'}`} key={m.at} data-testid="cwb-money" data-tip={`${m.what || 'trade'} · ${new Date((m.at || 0) * 1000).toLocaleString()}`}><em>LAST MONEY MADE</em>
    <b className="m-num">{m.usd == null ? '…' : `${up ? '+' : '−'}$${Math.abs(Number(m.usd)).toFixed(2)}`}</b><small>{m.sol != null ? `${up ? '+' : ''}${Number(m.sol).toFixed(4)} SOL · ` : ''}{m.what || 'trade'}</small></div>;
}
// pure: the same line again and again (a retry, a cap stop) folds into one row with ×N — newest time kept (owner 2026-10-30: "collapse the repeated")
export const squash = (out, x) => { const last = out[out.length - 1]; const key = r => `${r.f || r.by}|${String(r.text).replace(/\$[\d.]+/g, '$')}`;
  if (last && key(last) === key(x)) { last.n = (last.n || 1) + 1; return out; } out.push({ ...x }); return out; };
const BUDGET_STOP = /budget reached/i;
const SUGGEST = ["Find today's top coin on pump.fun and tell me why", 'Read X for $SOL news in the last hour', 'Check a coin on RugCheck + Solscan and report'];
// 💬 one chat message, the way a work chat shows it (owner 2026-10-31: "not corporate looking"): avatar · who · tags · time · cost, then the text.
// The server's prefixes ("🛟 Backup model…:", "💳 Paid $…:") become small tags instead of walls of words in front of the answer.
const MSG_TAGS = [[/^🛟 Backup model, free \(OpenRouter has no credit\):\s*/, 'free backup'], [/^💳 Paid \$([\d.]+) from its wallet:\s*/, 'paid from its wallet'], [/^⚡ from memory · /, 'from memory']];
export function chatParts(text) {
  let t = String(text || ''); const tags = [];
  for (let n = 0; n < 3; n += 1) { const hit = MSG_TAGS.find(([re]) => re.test(t)); if (!hit) break; tags.push(hit[1]); t = t.replace(hit[0], ''); }
  return { text: t, tags };
}
// ✍ the newest answer writes itself in once (≈0.7 s), like a live reply — never under reduced motion / fx-lite, never on old messages
function useTypeIn(text, on) {
  const [n, setN] = useState(on ? 0 : text.length); const born = useRef(Date.now());
  useEffect(() => {
    const calm = document.body.classList.contains('fx-lite') || window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;
    if (!on || calm || Date.now() - born.current > 1500) { setN(text.length); return undefined; }
    let raf = 0; const t0 = performance.now(); const step = t => { const k = Math.min(1, (t - t0) / 700); setN(Math.ceil(k * text.length)); if (k < 1) raf = requestAnimationFrame(step); };
    raf = requestAnimationFrame(step); return () => cancelAnimationFrame(raf); }, [text, on]);
  return text.slice(0, n);
}
function ChatMsg({ m, name, fresh = false }) {
  const you = m.by === 'you'; const parts = useMemo(() => chatParts(m.text), [m.text]); const tags = parts.tags;
  const text = useTypeIn(parts.text, fresh && !!m.at && Date.now() / 1000 - m.at < 20);
  return <li className={`cwb-msg ${you ? 'is-you' : 'is-cats'}`}><i className="cwb-av" aria-hidden="true">{you ? 'YOU' : '🧠'}</i>
    <div><header><b>{you ? 'You' : (name || 'Its minds')}</b>{tags.map(t => <em key={t} className="cwb-tag">{t}</em>)}{m.at ? <time>{ago(m.at)} ago</time> : null}{m.cost != null && !you ? <small className="m-num">{usd(m.cost)}</small> : null}</header>
      <p>{text}{m.n > 1 ? <em className="cwb-x"> ×{m.n}</em> : null}</p></div></li>;
}
const DESK_TIPS = [['[data-testid="cwb-now"]', 'What it is doing', 'Live: the site each window is on and the step it is taking.'],
  ['[data-testid="cwb-plus"]', 'Attach', 'Drop images or clips — they ride with your next ask (kept 24 h; ☁ Keep saves one to your own cloud).'],
  ['[data-testid="cwb-gear"]', 'Chat settings', 'How its minds work, who you talk to, the $ a task may spend, its job + tools.'],
  ['[data-testid="cwb-go"]', 'Let it go', 'ON: long tasks and queued asks run back to back until a person is needed.'],
  ['[data-testid="agent-log"] .ck-folders', 'Its file cabinet', 'Credentials, storage, earn plays and every log line — a drawer each; hide the ones you never use.']];
// pure: the general cat's log — your asks + answers (tasks), each window's steps (thoughts), its files, the cloud, every refusal (guards)
export function genLog(d) {
  const now = Date.now() / 1000;
  return [...(d?.chat || []).map(m => ({ f: 'tasks', at: m.at, text: `${m.by === 'you' ? 'You' : '🧠🧠'}: ${m.text}`, tone: m.by === 'you' ? 'acc' : 'up' })),
    ...(d?.windows || []).flatMap(w => (w.steps || []).map((s, k) => ({ f: 'thoughts', at: now - ((w.steps.length - k) * 5), text: `${String(w.model || '').split('/').pop()} · ${s.action}: ${s.thought}${s.detail ? ` (${s.detail})` : ''}`, tone: s.action === 'refused' ? 'warn' : s.action === 'handoff' ? 'up' : 'mute' }))),
    ...Object.entries(d?.minds || {}).flatMap(([m, xs]) => xs.map(c => ({ f: 'cloud', at: c.at, text: `☁ ${m.split('/').pop()} · ${c.text}`, tone: 'mute' }))),
    ...(d?.artifacts || []).map(a => ({ f: 'files', at: now, text: `${a.kind}: ${a.title}`, tone: 'acc' })),
    ...(d?.cloud || []).map(c => ({ f: 'cloud', at: c.at, text: c.text || `${c.word} $${c.sym}`, tone: 'acc' })),
    ...(d?.refusals || []).map(r => ({ f: 'guards', at: r.at || now, text: r.why, tone: 'warn' }))].filter(x => x.text).sort((p, q) => (q.at || 0) - (p.at || 0)).reduce(squash, []);
}

// 👀 a visitor (from the leaderboard) sees its minds + what both agreed on — its live windows and chat stay private to its owner
export function CatWorkbench({ cat, readOnly = false }) {
  return readOnly ? <PublicMinds cat={cat} /> : <WorkbenchLive cat={cat} />;
}
// 🖥 fits a dash to the screen under whatever sits above it (a visitor's view never scrolls — owner 2026-10-30)
function useFit(ref, below = 76) {
  useLayoutEffect(() => {
    const fit = () => { const r = ref.current; const st = r?.querySelector('.cwb-stage'); if (!st) return;
      if (window.innerWidth <= 900) { r.style.removeProperty('--cwb-h'); return; }
      const top = st.getBoundingClientRect().top + window.scrollY; let h = Math.round(Math.max(240, Math.min(720, window.innerHeight - top - below)));
      r.style.setProperty('--cwb-h', `${h}px`);
      const over = (r.closest('.kd.is-theater') ? r : r.closest('.kd') || r).getBoundingClientRect().bottom + window.scrollY - window.innerHeight + 24;   // then trim what the chrome around it adds
      if (over > 0) { h = Math.max(240, h - Math.ceil(over)); r.style.setProperty('--cwb-h', `${h}px`); } };
    fit(); window.addEventListener('resize', fit); return () => window.removeEventListener('resize', fit);
  }, [ref, below]);
}
// 👀 A VISITOR's view of someone's agent (no scroll): its two windows as they work — the site's host, the kind of step and how far — never the page
// 👀 one mind's side rail for a visitor (owner 2026-10-31: "more vitals on the sides, like Live Activity"): status, where, steps as a ring
export function MindRail({ w, side, d }) {
  const go = w?.status === 'working'; const pct = Math.min(1, (w?.steps || 0) / 30);
  return <aside className={`cwb-rail at-${side}${go ? ' is-go' : ''}`} data-testid={`cwb-rail-${side}`}>
    <b className="cwb-rail-h">MIND {'AB'[w?.i ?? (side === 'left' ? 0 : 1)]}</b><small title={w?.model}>{w?.model || '—'}</small>
    <span className="cwb-ring" style={{ '--p': pct }} data-tip="Steps this task (stops at 30)"><svg viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="16" /><circle cx="20" cy="20" r="16" className="on" style={{ strokeDashoffset: 100.5 * (1 - pct) }} /></svg><b className="m-num" key={w?.steps}>{w?.steps || 0}</b></span>
    <dl className="cwb-rail-kv"><div><dt>STATUS</dt><dd className={go ? 'is-up' : ''}>{go ? 'LIVE' : String(w?.status || 'idle').toUpperCase()}</dd></div><div><dt>ON</dt><dd>{w?.host || '—'}</dd></div>
      <div><dt>DOING</dt><dd>{w?.action ? w.action.toUpperCase() : '—'}</dd></div>
      {side === 'left' ? <div><dt>LEVEL</dt><dd className="m-num">{d?.level ?? '—'}</dd></div> : <div><dt>W / L</dt><dd className="m-num">{d ? `${d.wins || 0} / ${d.losses || 0}` : '—'}</dd></div>}
      {side === 'left' ? <div><dt>STORED</dt><dd className="m-num" key={d?.stored}>{d?.stored ?? 0}</dd></div> : <div><dt>P/L</dt><dd className={`m-num ${Number(d?.pnlSol) < 0 ? 'is-dn' : 'is-up'}`}>{d?.pnlSol != null ? `${Number(d.pnlSol) >= 0 ? '+' : ''}${Number(d.pnlSol).toFixed(3)} SOL` : '—'}</dd></div>}</dl>
  </aside>;
}
// 🗄 when it stores something a drawer slides out of its cabinet, the new file glows, then the drawer shuts (visitors watch it file things away)
export function StoredPop({ item }) {
  const [shown, setShown] = useState(null); const first = useRef(true);
  useEffect(() => { if (!item) return undefined; if (first.current) { first.current = false; return undefined; } setShown(item); const t = setTimeout(() => setShown(null), 3600); return () => clearTimeout(t); }, [item?.text, item?.at]); // eslint-disable-line react-hooks/exhaustive-deps
  return shown ? <div className="cwb-stored" role="status" data-testid="cwb-stored"><span className="cwb-stored-box" aria-hidden="true"><u /></span>
    <span className="cwb-stored-file"><em>🗄 FILED IN ITS CLOUD</em><b>{shown.text}</b></span></div> : null;
}
function PublicMinds({ cat }) {
  const ref = useRef(null); useFit(ref, 24); const seen = useOnScreen(ref);
  const [d, setD] = useState(null);
  useEffect(() => { if (!seen) return undefined; let on = true; const go = () => { if (document.hidden) return; Promise.resolve().then(() => fetch(apiUrl(`/api/cats/${cat.id}/live`))).then(r => (r?.ok ? r.json() : null)).then(x => on && x && setD(x)).catch(() => {}); };
    go(); const t = setInterval(go, 4000); return () => { on = false; clearInterval(t); }; }, [cat.id, seen]);
  const brains = cat.brainsCfg?.brains || [];
  const wins = d?.windows?.length ? d.windows : brains.slice(0, 2).map((m, i) => ({ i, model: String(m).split('/').pop(), status: 'idle', host: '', steps: 0 }));
  const live = d?.status === 'working' || wins.some(w => w.status === 'working');
  const agreed = d?.lastStored || (cat.brainsCfg?.cloud || []).at(-1);
  return <section ref={ref} className="cwb kd-card cwb-dash cwb-public" data-testid="cwb-public">
    <NowLine cat={cat} wins={wins.map(w => ({ ...w, url: w.host ? `https://${w.host}` : '', bubble: w.action ? `${w.action} · step ${w.steps}` : '' }))} live={live} />
    <div className="cwb-theater"><MindRail w={wins[0]} side="left" d={d} />
    <div className="cwb-stage agd-wins">{wins.map(w => { const go = w.status === 'working'; const i = w.i ?? 0;
      return <article key={i} className={`agd-win cwb-win w${i % 2} s-${w.status}`} data-testid={`cwb-pub-${i}`}>
        <span className={`agd-bar${go ? ' is-go' : ''}`}><i /><i /><i /><b>MIND {'AB'[i] || i + 1}</b><small>{w.model || 'model'}</small><em className={`agd-live${go ? '' : ' is-off'}`}>● {go ? 'LIVE' : String(w.status).toUpperCase()}</em></span>
        <div className="agd-browser is-rec cwb-browser"><span className="agd-url"><i aria-hidden="true">🔒</i><b>{w.host || 'about:blank'}</b>{go ? <em className="agd-rec">● LIVE</em> : null}</span>
          <div className="agd-screen cwb-view cwb-pubscreen"><span className="cwb-pub-host" key={w.host}>{w.host || (go ? 'thinking…' : 'idle')}</span>
            <span className="cwb-pub-step">{w.action ? <>{w.action.toUpperCase()} · step <b className="m-num" key={w.steps}>{w.steps}</b></> : 'waiting for its owner\'s ask'}</span>
            <u className="cwb-pub-bar" aria-hidden="true"><s style={{ transform: `scaleX(${Math.min(1, (w.steps || 0) / 30)})` }} /></u>
            <small className="cwb-pub-note">🔒 the page itself is private to its owner</small>
            {go ? <p className={`agd-done is-on cwb-say at-${i % 2 ? 'right' : 'left'}`}>MIND {'AB'[i]} · {w.action || 'working'} on {w.host || '…'}</p> : null}</div></div>
        <ol className="cwb-trail" aria-label={`Mind ${'AB'[i]} live activity`} data-testid={`cwb-trail-${i}`}><li className="cwb-trail-h">LIVE ACTIVITY</li>
          {(w.trail || []).length ? w.trail.map((x, j) => <li key={`${x.at}-${j}`} style={{ '--i': j }}><b>{String(x.action || '').toUpperCase()}</b><span>{x.host || ''}</span><small>{x.at ? `${ago(x.at)} ago` : ''}</small></li>)
            : <li className="cwb-trail-none">no moves yet — waiting for its owner's ask</li>}</ol>
      </article>; })}</div>
    <MindRail w={wins[1] || { i: 1, status: 'idle' }} side="right" d={d} /></div>
    {agreed ? <p className="cwb-agreed" data-tip="What both minds agreed on last — kept in its cloud">☁ {agreed.text || `${agreed.word} $${agreed.sym}`}</p> : null}
    <StoredPop item={d?.lastStored} />
  </section>;
}

// 🔐 THE CREDENTIALS DRAWER (owner 2026-10-30): site names only — stream-safe; a click unhides ONE login for 15 s. You add a site's login here
// (a window's 🔑 card opens it with the site filled in), sealed on the server; its windows get it there and type it blind ({{username}} / {{password}}).
// No account yet? Sign up opens the site in a new tab — come back and save it here.
function CredRow({ cat, r, onDrop }) {
  const [pw, setPw] = useState(null); const [why, setWhy] = useState(''); const { signMessage } = useWallet() || {};
  useEffect(() => { if (pw == null) return undefined; const t = setTimeout(() => setPw(null), 15000); return () => clearTimeout(t); }, [pw]);
  const show = async () => { if (pw != null) { setPw(null); return; } setWhy('');   // 🔐 every reveal = its own wallet signature (a stolen session alone shows nothing)
    try { const ts = Math.floor(Date.now() / 1000); const sig = await signMessage(revealMessage(cat.id, r.site, ts)); setPw((await work(cat.id, { op: 'reveal', text: r.site, job: r.user, ts, sig })).password); } catch (e) { setWhy(e.message || 'Not shown'); } };
  return <li data-testid={`cwb-cred-${r.site}`}><b>{r.site}</b>
    {pw != null ? <span className="cwb-cred-open"><span className="cwb-pw is-open">{r.user}</span><span className="cwb-pw is-pw is-open">{pw}</span></span> : null}
    <span className="cwb-cred-acts"><button type="button" className="m-btn" onClick={show} aria-pressed={pw != null} data-tip={pw != null ? 'Hide it now (it hides itself in 15 s)' : 'Sign once with your wallet to unhide this login for 15 s — hidden by default so a stream never shows it'} data-testid={`cwb-reveal-${r.site}`}>{pw != null ? '🙈 Hide' : '👁 Show'}</button>
      <button type="button" className="m-btn cwb-cred-x" onClick={() => onDrop(r)} aria-label={`Forget the ${r.site} login`} data-tip="Forget this login">✕</button></span>{why ? <small className="kd-err" role="alert">⚠ {why}</small> : null}</li>;
}
const VAULT_WORD = { 'signed in': '🔓 signed in', 'signed out': '🔒 signed out', saved: '🔐 saved', used: '🤖 signed in with', revealed: '👁 revealed', forgot: '✕ forgot', 'cloud connected': '☁ connected', 'cloud disconnected': '☁ disconnected' };
function Credentials({ cat, rows, ask, onSaved, log = [] }) {
  const box = useRef(null); const [site, setSite] = useState(''); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);
  useEffect(() => { if (!ask?.site) return; setSite(ask.site); if (box.current) { box.current.open = true; box.current.scrollIntoView({ behavior: 'smooth', block: 'center' }); setTimeout(() => box.current?.querySelector('input[name="u"]')?.focus({ preventScroll: true }), 400); } }, [ask]);
  const host = site.trim().toLowerCase().replace(/^https?:\/\//, '').split('/')[0];
  const save = async e => { e.preventDefault(); const f = new FormData(e.currentTarget); const form = e.currentTarget; setErr(''); setBusy(true);
    try { const j = await work(cat.id, { op: 'save_login', text: host, user: String(f.get('u') || ''), secret: String(f.get('p') || '') }); form.reset(); setSite(''); onSaved?.(j.logins); } catch (er) { setErr(er.message); } finally { setBusy(false); } };
  const drop = async r => { try { onSaved?.((await work(cat.id, { op: 'unlogin', text: r.site, job: r.user })).logins); } catch (er) { setErr(er.message); } };
  return <details ref={box} className="cwb-vault" open data-testid="cwb-vault"><summary data-tip="Logins its windows may use — sealed on the server, the AI models never see them">🔐 CREDENTIALS <b className="m-num">{rows?.length || 0}</b></summary>
    {rows?.length ? <ul>{rows.map(r => <CredRow key={`${r.site}|${r.user}`} cat={cat} r={r} onDrop={drop} />)}</ul> : null}
    <form className="cwb-login cwb-cred-add" onSubmit={save} autoComplete="off" data-testid="cwb-cred-add">
      <input className="m-input" name="s" value={site} onChange={e => setSite(e.target.value)} placeholder="site (e.g. dropbox.com)" aria-label="Site" required data-testid="cwb-cred-site" />
      <input className="m-input" name="u" autoComplete="off" placeholder="email or username" aria-label="Email or username" required data-testid="cwb-login-user" />
      <input className="m-input" name="p" type="password" autoComplete="new-password" placeholder="password" aria-label="Password" required data-testid="cwb-login-pass" />
      <span><button type="submit" className="m-btn m-go" disabled={busy || !host} data-testid="cwb-cred-save">{busy ? 'Sealing…' : 'Save sealed'}</button>
        {host ? <a className="m-btn cwb-signup" href={`https://${host}`} target="_blank" rel="noopener noreferrer" data-tip={`No account on ${host}? Sign up in a new tab, then come back and save it here`} data-testid="cwb-signup">No account? Sign up ↗</a> : null}</span>
      {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}</form>
    {log.length ? <ol className="cwb-vlog" data-testid="cwb-vault-log" aria-label="Who used the vault">{log.slice().reverse().slice(0, 6).map((x, i) => <li key={`${x.at}-${i}`} style={{ '--i': i }}><span>{VAULT_WORD[x.what] || x.what}</span><b>{x.site || ''}</b><time className="m-num">{ago(x.at)}</time></li>)}</ol> : null}</details>;
}
// 🖥 YOUR PRIVATE DESKTOP (owner 2026-10-31: "make it one window designed like the others — a real desktop: minimize the app, a Windows folder with
// the whole drawer to work in"): a desktop over the page — the live window (a sign-in, or a window handed to you) is an app window you move ·
// minimize · maximize; 🔐 Vault opens like a PC folder (Credentials · Sealed · Signed-in sites · API keys); a taskbar with the clock. Your
// screen only. The Vault asks "somewhere safe?" first, and every item still needs its own signature to open.
const STEEL_MS = 15 * 60 * 1000;   // a cloud window lives 15 min (Steel's free tier) — the title bar counts it down
const VAULT_TABS = [['creds', '🔐', 'Credentials', d => (d?.logins || []).length], ['sealed', '🔏', 'Sealed', d => (d?.secrets || []).length],
  ['sites', '🔓', 'Signed-in sites', d => (d?.signedIn || []).length], ['api', '🔑', 'API keys', () => null]];
const mmss = ms => `${Math.floor(ms / 60000)}:${String(Math.floor(ms / 1000) % 60).padStart(2, '0')}`;
function DeskWin({ k, title, s, top, set, onTop, onClose, tools, children }) {
  const drag = useRef(null);
  const down = e => { onTop(); if (s.max || e.button !== 0 || e.target.closest('button, a')) return; drag.current = { x: e.clientX - s.x, y: e.clientY - s.y }; e.currentTarget.setPointerCapture?.(e.pointerId); };
  const move = e => { if (drag.current) set(k, { x: e.clientX - drag.current.x, y: Math.max(0, e.clientY - drag.current.y) }); };
  return <section className={`dsk-win${s.max ? ' is-max' : ''}${top ? ' is-top' : ''}`} style={s.max ? undefined : { transform: `translate(${s.x}px, ${s.y}px)` }} onPointerDown={onTop} aria-label={title} data-testid={`dsk-win-${k}`}>
    <header className="dsk-title" onPointerDown={down} onPointerMove={move} onPointerUp={() => { drag.current = null; }} onDoubleClick={() => set(k, { max: !s.max })}>
      <span className="dsk-dots"><button type="button" className="is-x" onClick={onClose} aria-label={`Close ${title}`} data-tip="Close" />
        <button type="button" className="is-min" onClick={() => set(k, { min: true })} aria-label={`Minimize ${title}`} data-tip="Minimize — it waits in the taskbar" data-testid={`dsk-min-${k}`} />
        <button type="button" className="is-max" onClick={() => set(k, { max: !s.max })} aria-label={s.max ? 'Restore' : 'Maximize'} data-tip={s.max ? 'Restore' : 'Maximize'} /></span>
      <b>{title}</b><span className="dsk-tools">{tools}</span></header>
    <div className="dsk-body">{children}</div></section>;
}
export function AgentDesktop({ cat, live = null, onClose, onReopen, actions = null }) {
  const [w, setW] = useState(() => ({ live: { open: !!live, min: false, max: false, x: 24, y: 12 }, vault: { open: false, min: false, max: false, x: 120, y: 60 } }));
  const [top, setTop] = useState('live'); const [tab, setTab] = useState('creds'); const [d, setD] = useState(null); const [ask, setAsk] = useState(false); const [now, setNow] = useState(Date.now());
  const set = useCallback((k, p) => setW(x => ({ ...x, [k]: { ...x[k], ...p } })), []);
  const openVault = useCallback(() => { if (!safeOk()) { setAsk(true); return; } set('vault', { open: true, min: false }); setTop('vault'); }, [set]);
  useEffect(() => { let on = true; work(cat.id, { op: 'state' }).then(j => { if (on) setD(j); }).catch(() => {}); return () => { on = false; }; }, [cat.id]);
  useEffect(() => { if (!live) openVault(); }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(t); }, []);
  useEffect(() => { const k = e => { if (e.key === 'Escape' && !ask) onClose(); }; window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [onClose, ask]);
  const left = live?.at ? Math.max(0, STEEL_MS - (now - live.at)) : null;
  const pane = { creds: <Credentials cat={cat} rows={d?.logins} log={d?.vaultLog || []} onSaved={logins => setD(x => ({ ...x, logins }))} />,
    sealed: <SealedVault cat={cat} rows={d?.secrets} onSaved={secrets => setD(x => ({ ...x, secrets }))} />,
    sites: <SignedSites cat={cat} rows={d?.signedIn} nested onSaved={(signedIn, secrets) => setD(x => ({ ...x, signedIn, ...(secrets ? { secrets } : {}) }))} />,
    api: <ApiSlot cat={cat} /> }[tab];
  const tasks = [...(live ? [['live', '🌐', live.site || 'Live window']] : []), ['vault', '📁', 'Vault']].filter(([k]) => w[k].open);
  return createPortal(<div className="dsk" role="dialog" aria-modal="true" aria-label="Your private desktop" data-testid="cwb-pop">
    <div className="dsk-wall" aria-hidden="true"><i /><b>FEELESS</b><small>private desktop · only you see this</small></div>
    <nav className="dsk-icons" aria-label="Desktop">
      <button type="button" className="dsk-ico" onClick={openVault} data-tip="Your agent's drawer — logins, sealed recovery files, signed-in sites, API keys" data-testid="dsk-vault">
        <svg viewBox="0 0 48 40" aria-hidden="true"><path d="M3 8a3 3 0 0 1 3-3h12l4 4h20a3 3 0 0 1 3 3v3H3z" fill="#e2b13c" /><rect x="3" y="13" width="42" height="24" rx="3" fill="#f5c542" /><rect x="18" y="20" width="12" height="10" rx="2" fill="#7a5a12" /><circle cx="24" cy="25" r="2" fill="#f5c542" /></svg><span>Vault</span></button>
      {live ? <button type="button" className="dsk-ico" onClick={() => { set('live', { open: true, min: false }); setTop('live'); }} data-tip="The live window" data-testid="dsk-live-ico">
        <svg viewBox="0 0 48 40" aria-hidden="true"><rect x="3" y="4" width="42" height="32" rx="4" fill="#0d1a13" stroke="#45e486" strokeWidth="2" /><rect x="3" y="4" width="42" height="7" rx="3" fill="#15d16a" /><circle cx="24" cy="24" r="7" fill="none" stroke="#45e486" strokeWidth="2" /><path d="M17 24h14M24 17c3 3 3 11 0 14M24 17c-3 3-3 11 0 14" stroke="#45e486" strokeWidth="1.4" fill="none" /></svg><span>{live.site || 'Live window'}</span></button> : null}
    </nav>
    {live && w.live.open && !w.live.min ? <DeskWin k="live" title={`🌐 ${live.title || `sign in to ${live.site || 'the site'} yourself`}`} s={w.live} top={top === 'live'} set={set} onTop={() => setTop('live')} onClose={onClose}
      tools={<>{left != null ? <em className={`dsk-left${left < 120000 ? ' is-hot' : ''}`} data-tip="A cloud window lives 15 minutes — save before it closes">{left ? `closes in ${mmss(left)}` : 'closed'}</em> : null}{actions}
        <a className="m-btn" href={live.live} target="_blank" rel="noopener noreferrer" data-tip="Open this live window in its own browser tab">↗ Tab</a></>}>
      {left === 0 ? <div className="dsk-gone" data-testid="dsk-gone"><b>This cloud window closed</b><span>It lives 15 minutes. Whatever you saved is kept; open it again to carry on.</span>
        {onReopen ? <button type="button" className="m-btn m-go" onClick={onReopen} data-testid="dsk-reopen">Open it again</button> : null}</div>
        : <iframe title={live.title || 'Live window'} src={live.live} referrerPolicy="no-referrer" sandbox="allow-scripts allow-same-origin allow-forms allow-popups" allow="clipboard-read; clipboard-write" data-testid="cwb-pop-frame" />}
    </DeskWin> : null}
    {w.vault.open && !w.vault.min ? <DeskWin k="vault" title={`📁 Vault — ${cat.name || 'your agent'}`} s={w.vault} top={top === 'vault'} set={set} onTop={() => setTop('vault')} onClose={() => set('vault', { open: false })}>
      <div className="dsk-explorer"><aside className="dsk-side" aria-label="Vault folders">{VAULT_TABS.map(([k, ic, l, n]) => <button key={k} type="button" className={tab === k ? 'active' : ''} aria-pressed={tab === k} onClick={() => setTab(k)} data-testid={`dsk-tab-${k}`}>
        <i aria-hidden="true">{ic}</i><span>{l}</span>{n(d) != null ? <b className="m-num">{n(d)}</b> : null}</button>)}</aside>
        <div className="dsk-pane"><p className="dsk-path">Vault <i>›</i> {VAULT_TABS.find(t => t[0] === tab)[2]}</p><div key={tab} className="dsk-pull">{pane}</div></div></div>
    </DeskWin> : null}
    <footer className="dsk-bar"><span className="dsk-start"><i aria-hidden="true" />FEELESS</span>
      {tasks.map(([k, ic, l]) => <button key={k} type="button" className={`dsk-task${!w[k].min && top === k ? ' is-on' : ''}`} onClick={() => { if (w[k].min || top !== k) { set(k, { min: false }); setTop(k); } else set(k, { min: true }); }} data-testid={`dsk-task-${k}`}>{ic} {l}</button>)}
      <time className="m-num">{new Date(now).toTimeString().slice(0, 5)}</time>
      <button type="button" className="m-btn dsk-exit" onClick={onClose} data-tip="Back to the agent desk (Esc)" data-testid="cwb-pop-close">Exit desktop</button></footer>
    {ask ? <SafeGate label="The Vault" onYes={() => { setAsk(false); set('vault', { open: true, min: false }); setTop('vault'); }} onNo={() => setAsk(false)} /> : null}
  </div>, document.body);
}

// 🗄 A TRADER'S FILE CABINET (owner 2026-10-31: "trader agents need sign-in etc in their drawer" — they research X / CoinGecko too): the same
// Credentials + signed-in sites + API keys drawers a general agent has, over its log. Owner only (CatDesk passes canEdit).
export function TraderCabinet({ cat, items }) {
  const [d, setD] = useState(null);
  useEffect(() => { let on = true; work(cat.id, { op: 'state' }).then(j => { if (on) setD(j); }).catch(() => {}); return () => { on = false; }; }, [cat.id]);
  const [desk, setDesk] = useState(false);
  return <><button type="button" className="m-btn cwb-hbtn" onClick={() => setDesk(true)} data-tip="Your private desktop: work in its Vault, sign in to sites, keep recovery files — only you see it" data-testid="cwb-desk-open">🖥 Private desktop</button>
    <AgentLog title="ITS FILE CABINET" items={items} cabinet={keyDrawers(cat, d, setD)} />{desk ? <AgentDesktop cat={cat} onClose={() => setDesk(false)} /> : null}</>;
}
// 🔐 + 🔑 the key drawers every agent's cabinet shares (general + trader): sealed logins, signed-in sites, API keys
function keyDrawers(cat, d, setD, ask = null) {
  return [['creds', '🔐', 'Credentials', (d?.logins || []).length + (d?.signedIn || []).length + (d?.secrets || []).length, <><Credentials cat={cat} rows={d?.logins} log={d?.vaultLog || []} ask={ask} onSaved={logins => setD(x => ({ ...x, logins }))} />
      <SealedVault cat={cat} rows={d?.secrets} onSaved={secrets => setD(x => ({ ...x, secrets }))} />
      <SignedSites cat={cat} rows={d?.signedIn} onSaved={(signedIn, secrets) => setD(x => ({ ...x, signedIn, ...(secrets ? { secrets } : {}) }))} /></>, { guard: true }],
    ['api', '🔑', 'API keys', (cat?.apiDrawer || []).filter(r => r.saved).length, <ApiSlot cat={cat} />]];
}

// 🔏 SEALED (owner 2026-10-31: "a recovery phrase I download — where does it go? keep it in the agent's drawer, or I paste it and nobody ever sees
// it"): a file you download in a window you used lands here by itself (sealed, then deleted from the cloud browser); paste a phrase to seal it.
// The list shows labels only; Open = a fresh wallet signature — a note shows 15 s, a file downloads straight to YOUR device.
const kb = n => (n >= 1048576 ? `${(n / 1048576).toFixed(1)} MB` : n >= 1024 ? `${Math.round(n / 1024)} KB` : `${n} chars`);
function SealedVault({ cat, rows = [], onSaved }) {
  const { signMessage } = useWallet() || {}; const [shown, setShown] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState('');
  useEffect(() => { if (!shown) return undefined; const t = setTimeout(() => setShown(null), 15000); return () => clearTimeout(t); }, [shown]);
  const open = async r => { if (shown?.id === r.id) { setShown(null); return; } setErr(''); setBusy(r.id);
    try { const ts = Math.floor(Date.now() / 1000); const sig = await signMessage(revealMessage(cat.id, r.id, ts)); const j = await work(cat.id, { op: 'unseal', text: r.id, ts, sig });
      if (j.kind === 'file') { const bin = Uint8Array.from(atob(j.b64), c => c.charCodeAt(0)); const url = URL.createObjectURL(new Blob([bin]));
        const a = document.createElement('a'); a.href = url; a.download = j.name || 'sealed-file'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 2000); }
      else setShown({ id: r.id, text: j.text }); } catch (e) { setErr(e.message || 'Not opened'); } finally { setBusy(''); } };
  const drop = async r => { try { onSaved?.((await work(cat.id, { op: 'drop_secret', text: r.id })).secrets); } catch (e) { setErr(e.message); } };
  const seal = async e => { e.preventDefault(); const form = e.currentTarget; const f = new FormData(form); setErr(''); setBusy('seal');
    try { onSaved?.((await work(cat.id, { op: 'seal', job: String(f.get('l') || ''), text: String(f.get('s') || ''), secret: String(f.get('n') || '') })).secrets); form.reset(); } catch (er) { setErr(er.message); } finally { setBusy(''); } };
  return <section className="cwb-signed cwb-sealed" data-testid="cwb-sealed"><b className="cwb-signed-h">🔏 SEALED <em className="m-num">{rows.length}</em></b>
    <small>Recovery phrases + files. A file you download in a window you used lands here by itself — sealed, and deleted from the cloud browser.</small>
    {rows.length ? <ul>{rows.map(r => <li key={r.id} data-testid={`cwb-secret-${r.id}`}><span><b>{r.kind === 'file' ? '📄' : '📝'} {r.label}</b><small>{kb(r.size || 0)} · {ago(r.at)} ago · sealed</small>
      {shown?.id === r.id ? <code className="cwb-sealed-open" data-testid="cwb-secret-text">{shown.text}</code> : null}</span>
      <span className="cwb-cred-acts"><button type="button" className="m-btn" disabled={busy === r.id} onClick={() => open(r)} data-tip={r.kind === 'file' ? 'Sign once with your wallet — it downloads to THIS device' : shown?.id === r.id ? 'Hide it now (it hides itself in 15 s)' : 'Sign once with your wallet to show it for 15 s'} data-testid={`cwb-secret-open-${r.id}`}>{busy === r.id ? '…' : r.kind === 'file' ? '⬇ Download' : shown?.id === r.id ? 'Hide' : '👁 Open'}</button>
        <button type="button" className="m-btn cwb-cred-x" onClick={() => drop(r)} aria-label={`Delete ${r.label}`} data-tip="Delete it for good">✕</button></span></li>)}</ul> : null}
    <form className="cwb-signed-add cwb-sealed-add" onSubmit={seal} autoComplete="off" data-testid="cwb-seal-add">
      <span className="cwb-sealed-row"><input className="m-input" name="l" placeholder="label, e.g. Proton recovery phrase" aria-label="Label" required maxLength={80} />
        <input className="m-input" name="s" placeholder="site (optional)" aria-label="Site" maxLength={80} /></span>
      <textarea className="m-input cwb-sealed-note" name="n" rows={2} placeholder="paste it here — hidden as you type, sealed on Save" aria-label="Secret to seal" required maxLength={8000} spellCheck={false} autoComplete="off" data-testid="cwb-seal-text" />
      <button type="submit" className="m-btn m-go" disabled={busy === 'seal'} data-testid="cwb-seal-save">{busy === 'seal' ? 'Sealing…' : '🔏 Seal it'}</button></form>
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}
  </section>;
}

// 🔓 SIGNED-IN SITES (owner 2026-10-31): a site that blocks bots, or your agent's own email — open it here, sign in yourself in the live window,
// Save: its windows start signed in from then on (cookies sealed on the server, never sent to a page). A site that re-checks asks you again.
const SIGNIN_PICKS = [['x.com', '𝕏 X'], ['proton.me', '📧 Proton Mail'], ['accounts.google.com', '📧 Google'], ['discord.com', '💬 Discord'], ['web.telegram.org', '✈ Telegram'],
  ['github.com', '🐙 GitHub'], ['dexscreener.com', '📈 DexScreener'], ['coingecko.com', '🦎 CoinGecko'], ['solscan.io', '🔎 Solscan'], ['pump.fun', '💊 Pump'], ['tradingview.com', '📊 TradingView'], ['reddit.com', '👽 Reddit']];
export function SignedSites({ cat, rows = [], onSaved, nested = false }) {
  const [site, setSite] = useState(''); const [live, setLive] = useState(null); const [busy, setBusy] = useState(''); const [err, setErr] = useState(''); const [big, setBig] = useState(true);
  const run = async (op, text) => { setBusy(op); setErr('');
    try { const j = await work(cat.id, { op, text }); if (op === 'signin_open') { setLive({ ...j, at: Date.now() }); setBig(!nested); } else { setLive(null); onSaved?.(j.signedIn || [], j.secrets); } } catch (e) { setErr(e.message); } finally { setBusy(''); } };
  return <section className="cwb-signed" data-testid="cwb-signed"><b className="cwb-signed-h">🔓 SIGNED-IN SITES <em className="m-num">{rows.length}</em></b>
    <small>Blocked by a bot check, or your agent's own email? Sign in once here — its windows open signed in.</small>
    {rows.length ? <ul>{rows.map(r => <li key={r.site}><span><b>{r.site}</b><small data-tip="Only this site's own, newest, unexpired cookies are kept — trackers, other sites and stale logins are cut on every save and every load, then sealed with this agent's key">{ago(r.at)} ago · {r.n} cookies{r.dropped ? ` · ${r.dropped} cleaned out` : ''} · sealed</small></span>
      <button type="button" className="m-btn" disabled={!!busy} onClick={() => run('signin_drop', r.site)} data-tip={`Sign its windows out of ${r.site}`} data-testid={`cwb-signed-drop-${r.site}`}>Sign out</button></li>)}</ul> : null}
    {live ? <div className="cwb-signed-live"><span><em>LIVE · sign in to {live.site} yourself</em><button type="button" className="m-btn" onClick={() => setBig(true)} data-tip="Open the sign-in window big" data-testid="cwb-signed-big">⤢ Big</button>
      <button type="button" className="m-btn m-go" disabled={!!busy} onClick={() => run('signin_save')} data-testid="cwb-signed-save">{busy === 'signin_save' ? 'Saving…' : '✓ Signed in — save'}</button></span>
      {big ? <AgentDesktop cat={cat} live={live} onClose={() => setBig(false)} onReopen={() => run('signin_open', live.site)}
        actions={<button type="button" className="m-btn m-go" disabled={!!busy} onClick={() => run('signin_save')} data-tip="Keep this sign-in for its windows (and seal anything you downloaded)" data-testid="cwb-pop-save">{busy === 'signin_save' ? 'Saving…' : '✓ Signed in — save'}</button>} />
        : <iframe title={`Sign in to ${live.site}`} src={live.live} referrerPolicy="no-referrer" sandbox="allow-scripts allow-same-origin allow-forms allow-popups" data-testid="cwb-signed-frame" />}</div>
      : <form className="cwb-signed-add" onSubmit={e => { e.preventDefault(); if (site.trim()) run('signin_open', site.trim()); }}>
        <span className="m-seg">{SIGNIN_PICKS.map(([h, l]) => <button key={h} type="button" className={site === h ? 'active' : ''} onClick={() => setSite(h)} data-tip={`Sign its windows in to ${h}`}>{l}</button>)}</span>
        <input className="m-input" value={site} onChange={e => setSite(e.target.value)} placeholder="any site, e.g. x.com" aria-label="Site to sign in to" data-testid="cwb-signed-site" />
        <button type="submit" className="m-btn m-go" disabled={!site.trim() || !!busy} data-testid="cwb-signed-open">{busy === 'signin_open' ? 'Opening…' : 'Open + sign in'}</button></form>}
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}
  </section>;
}
const ago = t => { const s = Math.max(0, Date.now() / 1000 - (t || 0)); return s < 3600 ? `${Math.round(s / 60)}m` : s < 86400 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`; };
// ☁ ITS CLOUD = ITS OWNER'S (owner 2026-10-30: "FEELESS will not fund any storage"): connect your own Google Drive or Dropbox with their own
// sign-in — FEELESS keeps a sealed pass, never the password. The bar is YOUR space left there; its 5 newest files in your FEELESS folder;
// chat attachments (+) wait 24 h on FEELESS for its browser, ☁ keeps one in your cloud.
export function CloudDrawer({ cat, attachments }) {
  const [c, setC] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState('');
  const load = useCallback(() => fetch(apiUrl(`/api/cats/${cat.id}/cloud?${agentAuthQuery()}`)).then(r => r.json().then(j => (r.ok ? setC(j) : setErr(j.detail || `HTTP ${r.status}`)))).catch(e => setErr(e.message)), [cat.id]);
  useEffect(() => { load(); }, [load]);
  const post = async (path, body = {}) => { const r = await fetch(apiUrl(`/api/cats/${cat.id}/${path}`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...agentAuth(), ...body }) });
    const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`); return j; };
  const run = async (k, fn) => { setBusy(k); setErr(''); try { await fn(); } catch (e) { setErr(e.message); } finally { setBusy(''); } };
  const connect = p => run(p, async () => { window.location.assign((await post('cloud/connect', { provider: p })).url); });
  const link = c?.link; const used = Number(c?.used || 0); const total = Number(c?.total || 0); const files = attachments?.files || [];
  return <details className="cwb-vault cwb-cloudd" open data-testid="cwb-cloud-drawer"><summary data-tip="Its storage lives in YOUR cloud — FEELESS keeps none">☁ CLOUD {link ? <em className="m-chip ok">{link.label}</em> : <em className="m-chip warn">not connected</em>}</summary>
    {!link ? <div className="cwb-cloud-pick" data-testid="cwb-cloud-pick"><p className="m-note"><b>Connect your own cloud</b>Its files go to a FEELESS folder in your account. You sign in on Google / Dropbox — FEELESS never sees that password.</p>
      {(c?.providers || []).map(p => <button key={p.key} type="button" className={`m-btn${p.ready ? ' m-go' : ''}`} disabled={!p.ready || !!busy} onClick={() => connect(p.key)}
        data-tip={p.ready ? `Sign in to ${p.label} (${p.free}) — opens their page` : `${p.label} isn't set up on FEELESS yet`} data-testid={`cwb-cloud-${p.key}`}>{busy === p.key ? 'Opening…' : `Connect ${p.label}`} <small>{p.ready ? p.free : 'soon'}</small></button>)}</div> : <>
      <div className="cwb-meters cwb-cloud-bar" data-tip={total ? `${fileMb(used)} used of ${fileMb(total)} in your ${link.label}` : 'Your space'}><span><em>{link.label.toUpperCase()}</em>
        <b className="m-num" data-testid="cwb-cloud-left">{total ? `${fileMb(Math.max(0, total - used))} left` : '—'}</b><u aria-hidden="true"><s className={total && used > total * 0.8 ? 'is-hot' : ''} style={{ transform: `scaleX(${total ? Math.min(1, used / total) : 0})` }} /></u></span></div>
      {(c?.recent || []).length ? <div className="cwb-media-strip" data-testid="cwb-cloud-latest">{c.recent.map(f => <a key={f.id} href={f.link} target="_blank" rel="noopener noreferrer" data-tip={`${f.name} · ${fileMb(f.size)} — opens in your ${link.label}`}>
        {f.thumb ? <img src={f.thumb} alt={f.name} loading="lazy" referrerPolicy="no-referrer" /> : <span className="cwb-cloud-ico" aria-hidden="true">📄</span>}<small>{f.name}</small></a>)}</div>
        : <p className="cwb-cloud-empty">Nothing kept yet — ☁ a chat attachment below, or ask it to save something.</p>}
      <button type="button" className="m-btn cwb-cred-x" disabled={!!busy} onClick={() => run('off', async () => { await post('cloud/disconnect'); await load(); })} data-tip="Disconnect — FEELESS forgets the sealed pass">Disconnect</button></>}
    {files.length ? <ul className="cwb-cloud-files" data-testid="cwb-cloud-files" aria-label="Chat attachments (24 h)">{files.map((f, i) => <li key={f.id} style={{ '--i': i }}><span className="cwb-cloud-ico" aria-hidden="true">{f.mime?.startsWith('video/') ? '🎞' : '🖼'}</span>
      <b>{f.name}</b><span className="m-num">{fileMb(f.size)}</span>{link ? <button type="button" className="m-btn" disabled={!!busy} onClick={() => run(f.id, async () => { await post(`files/${f.id}/keep`); await load(); })} data-tip={`Keep it in your ${link.label} (attachments leave FEELESS after 24 h)`} data-testid={`cwb-keep-${f.id}`}>{busy === f.id ? '…' : '☁ Keep'}</button> : <span className="m-chip">24 h</span>}</li>)}</ul> : null}
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}</details>;
}

// 🖼 its media drawer: what it saved for a campaign, a slide strip, cleaned after 7 days on its own
function MediaDrawer({ items }) {
  if (!items?.length) return null;
  return <section className="cwb-media" data-testid="cwb-media"><b>🖼 MEDIA <small>{items.length} · cleaned after 7 days</small></b>
    <div className="cwb-media-strip">{items.map(m => <a key={m.url} href={m.url} target="_blank" rel="noopener noreferrer" data-tip={m.title || m.url}>
      {m.kind === 'video' ? <video src={m.url} muted loop playsInline preload="metadata" /> : <img src={m.url} alt={m.title || ''} loading="lazy" />}<small>{m.title || 'untitled'}</small></a>)}</div></section>;
}

// ☁ its own storage (owner 2026-10-31): the + beside the chat puts images / GIFs in the agent's storage (1 GB, cleaned 7 days after last use);
// the attached ones ride with the next ask — the agent reads their names and its live browser can upload one (e.g. a coin image on pump.fun)
const fileMb = n => (n >= 1024 ** 3 ? `${(n / 1024 ** 3).toFixed(1)} GB` : n >= 1024 ** 2 ? `${(n / 1024 ** 2).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);
const readAsDataUrl = f => new Promise((ok, no) => { const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = () => no(new Error('That file could not be read.')); r.readAsDataURL(f); });
export async function addFile(catId, file) {
  if (!/^image\/(png|jpeg|webp|gif)$/.test(file?.type || '')) throw new Error('Images only: PNG, JPEG, WebP or GIF.');
  if (file.size > (file.type === 'image/gif' ? 40 : 15) * 1024 * 1024) throw new Error(file.type === 'image/gif' ? 'GIFs up to 40 MB.' : 'Images up to 15 MB.');
  const r = await fetch(apiUrl(`/api/cats/${catId}/files`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...agentAuth(), dataUrl: await readAsDataUrl(file), name: file.name }) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`);
  return j;
}
function AttachChips({ files, store, onDrop }) {
  if (!files.length) return null;
  const pct = store ? Math.min(1, store.used / store.quota) : 0;
  return <div className="cwb-files" data-testid="cwb-files">{files.map((f, i) => <span key={f.id} className="cwb-file" style={{ '--i': i }} data-tip={`${f.name} · ${fileMb(f.size)} — goes with your next ask`}>
    <img src={apiUrl(f.url)} alt="" /><b>{f.name}</b><small className="m-num">{fileMb(f.size)}</small>
    <button type="button" onClick={() => onDrop(f.id)} aria-label={`Take ${f.name} off this ask`} data-tip="Take it off this ask (it stays in its storage until cleaned)" data-testid={`cwb-file-x-${f.id}`}>✕</button></span>)}
    {store ? <span className="cwb-store" data-tip={`Attachments: ${fileMb(store.used)} of ${fileMb(store.quota)} — they leave FEELESS 24 h after last use (☁ Keep one in your own cloud)`} data-testid="cwb-store">
      <em>☁ STORAGE</em><u aria-hidden="true"><s style={{ transform: `scaleX(${pct})` }} /></u><small className="m-num">{fileMb(store.used)} / {fileMb(store.quota)}</small></span> : null}</div>;
}

function WorkbenchLive({ cat }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [text, setText] = useState(''); const [busy, setBusy] = useState(false); const [tick, setTick] = useState(0);
  const [files, setFiles] = useState([]); const [store, setStore] = useState(null); const [upping, setUpping] = useState(false); const pick = useRef(null);   // ☁ attached to the next ask
  const attach = async e => { const list = Array.from(e.target.files || []).slice(0, 4); e.target.value = ''; if (!list.length) return; setUpping(true); setErr('');
    try { for (const f of list) { const j = await addFile(cat.id, f); setFiles(x => [...x, j.file].slice(-4)); setStore({ used: j.used, quota: j.quota }); } } catch (er) { setErr(er.message); } finally { setUpping(false); } };
  const [signIn, setSignIn] = useState(null);   // 🔑 a window's sign-in card → the credentials drawer, this site filled in
  const [to, setTo] = useState('both'); const [jobs, setJobs] = useState(['', '']);   // 🧠 talk to both minds, or ONE of them (it works the whole task in its own window)
  const [down, setDown] = useState(false);
  const load = useCallback(() => work(cat.id, { op: 'state' }).then(x => { setD(x); setErr(''); setDown(false); }).catch(e => { setErr(e.message); setDown(!!e.down); }), [cat.id]);
  const status = d?.task?.status;
  const live = !down && (LIVE_STATES.includes(status) || status === 'human' || (d?.windows || []).some(w => w.status === 'human' || w.status === 'working'));   // the service down = never a stale "Working"
  useEffect(() => { load(); }, [load]);
  useEffect(() => { const t = setInterval(() => { if (!document.hidden) { load(); setTick(x => x + 1); } }, live ? 1500 : 8000); return () => clearInterval(t); }, [load, live]);
  const act = async (op, extra = {}) => { setBusy(true); setErr(''); try { const r = await work(cat.id, { op, ...extra }); setD(x => ({ ...x, ...r })); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  const go = !!d?.go; const queue = d?.queue || [];   // 🏇 let it go (owner Q1): long tasks, asks queue up and run one after another until a human is needed
  const way = d?.workMode || 'plan';
  const send = e => { e?.preventDefault?.(); if (busy) return;
    if (way === 'jobs' && wins.length > 1) { const [a, b] = jobs.map(x => x.trim()); if (!a && !b) return; setJobs(['', '']); act('ask', { text: [a && `A: ${a}`, b && `B: ${b}`].filter(Boolean).join('\n'), to: 'both' }); return; }   // one job is fine: that mind owns it, the other supports
    const t = text.trim(); if (!t) return; setText(''); const ids = files.map(f => f.id); setFiles([]); act('ask', { text: t, to, ...(ids.length ? { files: ids } : {}) }); };
  const setWay = async k => { setBusy(true); try { await work(cat.id, { op: 'mode', job: k }); await load(); } catch (er) { setErr(er.message); } finally { setBusy(false); } };
  const wins = d?.windows?.length ? d.windows : (cat.brainsCfg?.brains || ['', '']).slice(0, 8).map((m, i) => ({ i, model: m, status: 'idle' }));
  const credit = Number(d?.credit ?? cat.brainsCfg?.credit ?? 0); const cap = Number(d?.cap ?? 0.05); const spent = Number(d?.task?.cost || 0);
  const [gear, setGear] = useState(false); const log = useMemo(() => genLog(d), [d]); const [flip, setFlip] = useState(false); const [desk, setDesk] = useState(false); const [old, setOld] = useState(false);
  useEffect(() => { if (!gear && !flip) return undefined; const k = e => { if (e.key === 'Escape') { setGear(false); setFlip(false); } }; window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [gear, flip]);
  useEffect(() => { if (signIn) setFlip(true); }, [signIn]);   // a window asked for a login → the chat flips to the cabinet, on Credentials
  const msgs = useMemo(() => (d?.chat || []).slice(-24).filter(m => !(m.by !== 'you' && BUDGET_STOP.test(m.text))).reduce(squash, []), [d?.chat]);
  const lastYou = msgs.map(m => m.by).lastIndexOf('you'); const cut = lastYou > 0 ? lastYou : Math.max(0, msgs.length - 4);   // 🗂 this run up front; earlier runs fold away
  const doing = wins.find(w => w.status === 'working')?.bubble || (live ? 'working on it' : '');
  const dash = useRef(null);
  return <section ref={dash} className="cwb kd-card cwb-dash" data-testid="cat-workbench">
    <header className="cwb-head"><span><b>🧠🧠 ITS MINDS</b><small>{(d?.providers || []).filter(x => x !== 'reader').length ? `browsers in the cloud · ${d.providers.join(' → ')}` : 'reading pages as text (no hosted browser key yet)'}</small></span>
      <button type="button" className={`cwb-go${go ? ' is-on' : ''}`} aria-pressed={go} disabled={busy} onClick={() => act('go', { on: !go })} data-testid="cwb-go"
        data-tip={go ? 'ON: up to 30 steps a window, asks queue and run back to back — it stops only when done, at the $ cap, or for a sign-in / CAPTCHA / card payment' : 'Let it go: it works long tasks on its own and takes queued asks one after another until a person is needed'}>
        <i aria-hidden="true" />🏇 LET IT GO <b>{go ? 'ON' : 'OFF'}</b></button>
      <button type="button" className="m-btn cwb-hbtn" onClick={() => setDesk(true)} data-tip="Your private desktop: work in its Vault, sign in to sites, keep recovery files — only you see it" data-testid="cwb-desk-open">🖥 Desktop</button>
      <span className="cwb-meters">
        <span data-tip="Model credit left: every answer and browsing step is paid from it. Add more in its wallet panel"><em>CREDIT</em><b className="m-num">{usd(credit)}</b><u aria-hidden="true"><s style={{ transform: `scaleX(${Math.min(1, credit / 10)})` }} /></u></span>
        <span data-tip="This task's spend against its cap — it stops at the cap with what it has"><em>THIS TASK</em><b className="m-num">{usd(spent)} / {usd(cap)}</b><u aria-hidden="true"><s className={spent >= cap * 0.8 ? 'is-hot' : ''} style={{ transform: `scaleX(${Math.min(1, spent / (cap || 1))})` }} /></u></span>
      </span></header>
    <NowLine cat={cat} wins={wins} live={live} />
    <div className="cwb-stage agd-wins">{wins.map(w => <Window key={w.i} w={w} catId={cat.id} tick={tick} busy={busy} onGo={(op, i) => act(op, { i })} onLogin={site => setSignIn({ site, at: Date.now() })} />)}</div>
    <div className={`cwb-under cwb-flip${flip ? ' is-back' : ''}`}><div className="cwb-flip-in">
        <div className="cwb-talk cwb-face" data-testid="cwb-cockpit" inert={flip}>
    <header className="cwb-talk-h"><span className={`cwb-status${live ? ' is-live' : ''}`}><i aria-hidden="true" />{live ? 'Working' : 'Ready'}</span>
      <b>Chat with {cat.name || 'its minds'}</b>
      <button type="button" className="cwb-flip-btn" onClick={() => setFlip(true)} aria-label="Flip to its file cabinet" data-tip="Flip to its file cabinet — every file, logins, sealed recovery files, storage, earnings" data-testid="cwb-flip">
        <svg viewBox="0 0 20 20" aria-hidden="true"><rect x="3" y="3" width="14" height="5" rx="1.5" /><rect x="3" y="10" width="14" height="7" rx="1.5" /><path d="M8 5.5h4M8 13.5h4" /></svg><span>Files</span><b className="m-num">{log.length}</b></button></header>
    {d?.task?.answer || status === 'stopped' || status === 'error' || status === 'parked' ? <p className={`cwb-answer s-${status}`} data-testid="cwb-answer">{d.task.fast ? '⚡ from memory · ' : ''}{d.task.answer || d.task.why}</p> : null}
    <ol className="cwb-chat" aria-label="Chat with its models" aria-live="polite">
      {cut > 0 ? <li className="cwb-earlier"><button type="button" onClick={() => setOld(o => !o)} aria-expanded={old} data-testid="cwb-earlier">{old ? 'Hide earlier' : `Earlier · ${cut} message${cut === 1 ? '' : 's'}`}</button></li> : null}
      {(old ? msgs : msgs.slice(cut)).map((m, i, a) => <ChatMsg key={`${m.at || i}-${String(m.text).slice(0, 24)}`} m={m} name={cat.name} fresh={i === a.length - 1 && m.by !== 'you'} />)}
      {live ? <li className="cwb-msg is-cats is-typing" data-testid="cwb-typing"><i className="cwb-av" aria-hidden="true">🧠</i><div><header><b>{cat.name || 'Its minds'}</b><em className="cwb-tag">working</em></header>
        <p><span className="cwb-dots" aria-hidden="true"><i /><i /><i /></span>{doing}</p></div></li> : null}
      {!msgs.length && !live ? <li className="cwb-empty" data-testid="cwb-empty"><b>What should it do?</b><span>Ask in plain words. It works in its own cloud browsers and reports back here.</span>
        <span className="cwb-sugg">{SUGGEST.map(t => <button key={t} type="button" onClick={() => setText(t)}>{t}</button>)}</span></li> : null}
    </ol>
    {BUDGET_STOP.test((d?.chat || []).filter(m => m.by !== 'you').at(-1)?.text || '') ? <p className="m-note warn cwb-topup" role="status" data-testid="cwb-topup"><b>💸 Out of budget for that ask</b>
      <span>Its next step could pass the $ cap you set. Raise the cap, or add model credit in Wallet.</span><button type="button" className="m-btn m-go" onClick={() => setGear(true)} data-testid="cwb-topup-cap">Raise the cap</button></p> : null}
    {queue.length ? <ol className="cwb-queue" aria-label="Queued asks" data-testid="cwb-queue">{queue.map((q, i) => <li key={i} style={{ '--i': i }}><b className="m-num">{i + 1}</b><span>{q.text}</span>
      <button type="button" onClick={() => act('unqueue', { i })} aria-label="Drop this ask" data-tip="Drop it from the queue" data-testid={`cwb-unq-${i}`}>✕</button></li>)}</ol> : null}
    {(d?.parked || []).length ? <ol className="cwb-queue is-parked" aria-label="Filed to come back to" data-testid="cwb-parked">{d.parked.map((q, i) => <li key={`${q.at}-${i}`} style={{ '--i': i }}><b className="m-num">⏸</b><span data-tip={`Nobody answered for 5 min, so it moved on: ${q.why}`}>{q.text}</span>
      <button type="button" disabled={busy || live} onClick={async () => { await act('unpark', { i }); act('ask', { text: q.text, to: 'both' }); }} aria-label="Resume it now" data-tip={live ? 'Resume once the current task is done' : 'Ask it again now — you are here to help this time'} data-testid={`cwb-resume-${i}`}>▶</button>
      <button type="button" onClick={() => act('unpark', { i })} aria-label="Drop it" data-tip="Drop it" data-testid={`cwb-unpark-${i}`}>✕</button></li>)}</ol> : null}
    <AttachChips files={files} store={store} onDrop={id => setFiles(x => x.filter(f => f.id !== id))} />
    <div className={`cwb-pop${gear ? ' is-open' : ''}`} id="cwb-settings" role="dialog" aria-label="Chat settings" data-testid="cwb-settings" aria-hidden={!gear}>
      {live ? <small className="m-note" data-testid="cwb-locked">🔒 Locked while it works — press ■ Stop to change these</small> : null}
      <em>HOW ITS MINDS WORK</em>
    <div className="m-seg cwb-way" role="radiogroup" aria-label="How its minds work">{WAYS.map(([k, l, tip]) => <button key={k} type="button" role="radio" aria-checked={way === k}
      className={way === k ? 'active' : ''} disabled={live || busy} onClick={() => setWay(k)} data-tip={tip} data-testid={`cwb-way-${k}`}>{l}</button>)}</div>
      <em>WHO YOU TALK TO</em>
    {way !== 'jobs' ? <div className="m-seg cwb-to" role="radiogroup" aria-label="Who you are talking to">{[['both', '🧠 ALL MINDS'], ...wins.map(w => [String(w.i), `🧠 ${String(w.model || `mind ${w.i + 1}`).split('/').pop()}`])].map(([k, l]) =>
      <button key={k} type="button" role="radio" aria-checked={to === k} className={to === k ? 'active' : ''} disabled={live} onClick={() => setTo(k)} data-testid={`cwb-to-${k}`}
        data-tip={k === 'both' ? 'Both minds: they split the task, each in its own window, then merge' : 'Only this mind: it takes the whole task in its own window'}>{l}</button>)}</div> : null}
      <em>MOST A TASK MAY SPEND</em>
    <div className="m-seg cwb-cap" role="radiogroup" aria-label="The most one task may spend">{CAPS.map(c => <button key={c} type="button" role="radio" aria-checked={Math.abs(cap - c) < 1e-9} className={Math.abs(cap - c) < 1e-9 ? 'active' : ''} onClick={() => act('cap', { cap: c })} data-tip={`A task stops at $${c}`} data-testid={`cwb-cap-${c}`}>${c}</button>)}</div>
      <em>JOB + TOOLS</em>
    <div className="cwb-tools"><label>Job<select className="m-input" aria-label="Cat job" value={d?.job || 'agent'} disabled={live || busy} onChange={e => act('tools', { job: e.target.value })}>{Object.keys(d?.toolkits || { agent: [] }).map(j => <option key={j}>{j}</option>)}</select></label><div className="m-seg">{Object.entries(d?.tools || {}).map(([k, on]) => <button key={k} type="button" aria-pressed={on} disabled={live || busy} className={on ? 'active' : ''} data-tip={`Allow this cat to use ${k}`} onClick={() => act('tools', { tools: { ...d.tools, [k]: !on } })}>{k} · {on ? 'ON' : 'OFF'}</button>)}</div></div>
    </div>
    <form className="cwb-ask cwb-compose" onSubmit={send}>
      <div className="cwb-fields">
      {way === 'jobs' && wins.length > 1 && !live ? <span className="cwb-jobs">{[0, 1].map(i => <label key={i} className="cwb-field"><em className={`cwb-chip m${i}`}>{'AB'[i]} · {String(wins[i]?.model || '').split('/').pop()}</em>
        <input className="m-input" value={jobs[i]} onChange={e => setJobs(j => (i ? [j[0], e.target.value] : [e.target.value, j[1]]))} placeholder={i ? `Mind B's job — e.g. make 5 posts for X from it` : `Mind A's job — e.g. write a 30 s video script on SOL`} data-testid={`cwb-job-${i}`} aria-label={`Mind ${'AB'[i]} job`} /></label>)}</span> : null}
      <input hidden={way === 'jobs' && wins.length > 1 && !live} className="m-input" value={text} onChange={e => setText(e.target.value)} placeholder={live ? (go ? 'Working… type the next ask — it queues' : 'Working… press Stop to ask again') : `Message ${cat.name || 'your agent'}…`} disabled={live && !go} aria-label="Ask the cat" data-testid="cwb-input" />
      </div>
      <div className="cwb-bar">
      <button type="button" className={`cwb-plus${upping ? ' is-busy' : ''}`} onClick={() => pick.current?.click()} disabled={upping || files.length >= 4} aria-label="Attach images for it"
        data-tip="Attach images or GIFs (up to 4) — they go in its own storage and ride with your next ask; it can upload them to a site, e.g. a coin image" data-testid="cwb-plus"><i aria-hidden="true" /></button>
      <button type="button" className={`cwb-gear${gear ? ' is-on' : ''}`} aria-expanded={gear} aria-controls="cwb-settings" onClick={() => setGear(g => !g)} aria-label="Chat settings"
        data-tip="Settings: how its minds work, who you talk to, the $ cap, its job + tools" data-testid="cwb-gear"><i aria-hidden="true" /></button>
      <input ref={pick} type="file" accept="image/png,image/jpeg,image/webp,image/gif,video/mp4,video/webm" multiple hidden onChange={attach} data-testid="cwb-file-input" />
      <small className="cwb-hint">{way === 'jobs' && wins.length > 1 && !live ? 'one job each · Enter ↵ sends both' : to === 'both' ? 'both minds · Enter ↵ to send' : `only ${String(wins[Number(to)]?.model || '').split('/').pop()} · Enter ↵`}</small>
      {live && go && text.trim() ? <button type="submit" className="m-btn m-go" disabled={busy} data-testid="cwb-queue-add">＋ Queue ↵</button>
        : live ? <button type="button" className="m-btn" onClick={() => act('stop')} disabled={busy} data-testid="cwb-stop">■ Stop</button>
        : <button type="submit" className="m-btn m-go cwb-send" disabled={busy || (way === 'jobs' && wins.length > 1 ? !(jobs[0].trim() || jobs[1].trim()) : !text.trim())} data-testid="cwb-send">Send <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 8h11M9 4l4 4-4 4" /></svg></button>}
      </div>
    </form>
    </div>
    <aside className="cwb-face cwb-back cwb-tools-rail" aria-label="Its file cabinet" inert={!flip} data-testid="cwb-sheet">
    <header className="cwb-talk-h"><b>Its file cabinet</b>
      <button type="button" className="cwb-flip-btn" onClick={() => setFlip(false)} aria-label="Flip back to the chat" data-tip="Back to the chat (Esc)" data-testid="cwb-flip-back">
        <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 5h12v8H9l-4 3v-3H4z" /></svg><span>Chat</span></button></header>
    <LastMoney m={d?.lastMoney} />
    <AgentLog title="FILES" items={log} open={signIn ? { key: 'creds', at: signIn.at } : null} cabinet={[
      ...keyDrawers(cat, d, setD, signIn),
      ['storage', '☁', 'Storage', (d?.storage?.files || []).length, <CloudDrawer cat={cat} attachments={d?.storage} />],
      ['earn', '⚡', 'Earn', (d?.lastMoney ? 1 : 0), <EarnCard cat={cat} />],
      ['treasury', '🏦', 'Treasury', 0, <TreasuryDrawer cat={cat} />],
      ['pass', '🎫', 'Agent Pass', cat?.pass?.asset ? 1 : 0, <PassDrawer cat={cat} />],
      ['notes', '🧠', 'Main cloud', (d?.cloud || []).length, <div className="cwb-cloud" data-testid="cwb-cloud">{(d?.cloud || []).slice(-6).reverse().map((c, i) => <span key={i} style={{ '--i': i }}>{c.text || `${c.word} $${c.sym}`}</span>)}</div>],
      ...((d?.media || []).length ? [['media', '🖼', 'Media', d.media.length, <MediaDrawer items={d.media} />]] : []),
      ...((d?.artifacts || []).length ? [['builds', '🛠', 'Builds', d.artifacts.length, <div className="cwb-builds">
      {(d?.artifacts || []).map((a, i) => <details className="cwb-artifact" key={i}><summary>{a.title} · {a.kind}</summary>{a.kind === 'build' ? <iframe title={a.title} sandbox="allow-scripts" referrerPolicy="no-referrer" srcDoc={'<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'unsafe-inline\'; style-src \'unsafe-inline\'; img-src data:; connect-src \'none\'; form-action \'none\'; base-uri \'none\'">' + a.content} /> : <pre>{a.content}</pre>}</details>)}
      </div>]] : [])]} />
    </aside></div></div>
    {desk ? <AgentDesktop cat={cat} onClose={() => setDesk(false)} /> : null}
    <FirstTips id="agent-desk" tips={DESK_TIPS} />
    {d && !d.live ? <p className="cwb-note" data-testid="cwb-off">Model calls are switched off on this server — asking sends and charges nothing until the owner turns them on.</p> : null}
    {err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}
  </section>;
}

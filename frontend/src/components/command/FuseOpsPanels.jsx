import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { Countdown } from '../RunnersPanel';
import '../../styles/fusePage.css';
import { toast } from 'sonner';
import { RiskDial, DialBoard } from '../RiskDial';

// Cmd Ctr › Fuse › ⚔ Arena ops: the live battlefield (pairs, move since the bell, time left), the last results, what's
// on the stage (by kind) and this week's season board. Read-only views of the public Arena + Season data (60s).
const pct = v => `${v >= 0 ? '+' : ''}${Number(v || 0).toFixed(1)}%`;
const KIND = { scenario: '🧪 Engine', auto: '🤖 Auto card', mega: '⚛️ Cmd Ctr', user: '👤 Trader', lit: '🔥 Lit runners', round: '⏳ Proving', feecat: '🐱 FeeCat' };

function useJson(path, ms = 60000) {
  const [d, setD] = useState(null);
  useEffect(() => {
    let alive = true; const load = first => (first || !document.hidden) && fetch(apiUrl(path)).then(r => r.json()).then(x => alive && setD(x)).catch(() => {});
    load(true); const t = setInterval(() => load(false), ms);
    return () => { alive = false; clearInterval(t); };
  }, [path, ms]);
  return d;
}

export function ArenaOps() {
  const a = useJson('/api/reputation/fuses/arena');
  const s = useJson('/api/reputation/fuses/season');
  if (!a || !s) return <div className="fl-row is-ghost" />;
  const b = a.battles || { pairs: [], log: [] };
  const kinds = (a.mega || []).reduce((m, c) => ({ ...m, [c.kind]: (m[c.kind] || 0) + 1 }), {});
  return <section className="m-card fops" data-testid="arena-ops"><DialBoard dials={a.dials} />
    <div className="fops-row">
      <div className="fops-tile"><small>STAGE</small><b className="m-num">{(a.mega || []).length}</b><em>{Object.entries(kinds).map(([k, n]) => `${KIND[k] || k} ${n}`).join(' · ') || 'empty'}</em></div>
      <div className="fops-tile"><small>BATTLES</small><b className="m-num">{b.pairs.length}</b><em>{b.endsAt ? <>bell in <Countdown at={b.endsAt} /></> : 'pairing on next tick'}</em></div>
      <div className="fops-tile"><small>SEASON · THIS WEEK</small><b className="m-num">{s.cards}</b><em>cards · ends {new Date(s.endsAt * 1000).toLocaleDateString(undefined, { weekday: 'short' })}</em></div>
      <div className="fops-tile" data-tip="FeeCat's average trade this week — cards above it are marked and win the challenge"><small>🐱 FEECAT WEEK</small><b className={`m-num ${(s.feecat?.pct || 0) >= 0 ? 'm-pos' : 'm-neg'}`}>{s.feecat?.pct == null ? '—' : pct(s.feecat.pct)}</b><em>beat her: +{s.feecat?.winPts} score</em></div>
    </div>
    <div className="fops-cols">
      <div className="fops-box"><header><b>⚔ Live battles</b><small className="m-dim">bigger move since the bell wins</small></header>
        {b.pairs.length ? b.pairs.map(p => <div key={p.a.key + p.b.key} className="fops-fight"><span className={p.a.now >= p.b.now ? 'lead' : ''}>{p.a.emoji} {p.a.name} <b className="m-num">{pct(p.a.now)}</b></span><i>vs</i>
          <span className={p.b.now > p.a.now ? 'lead' : ''}>{p.b.emoji} {p.b.name} <b className="m-num">{pct(p.b.now)}</b></span></div>) : <p className="m-dim">Needs 2+ cards on the stage.</p>}
        {b.log?.length > 0 && <ul className="fops-log">{b.log.map((x, i) => <li key={i}>{x.draw ? `🤝 ${x.a} = ${x.b}` : `🏆 ${x.winner} beat ${x.winner === x.a ? x.b : x.a}`} <small className="m-dim">{pct(x.aMove)} vs {pct(x.bMove)}</small></li>)}</ul>}</div>
      <div className="fops-box"><header><b>🏆 Season board</b><small className="m-dim">real P&L % · cards opened this week</small></header>
        {s.board.length ? <ol className="fops-board">{s.board.map(r => <li key={r.id}><b>{r.rank}</b><span>{r.name || 'Card'} <small className="m-dim">{r.handle}{r.beatsCat ? ' · 🐱 beat FeeCat' : ''}</small></span><em className={`m-num ${r.pnlPct >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(r.pnlPct)}</em></li>)}</ol>
          : <p className="m-dim">No cards this week yet.</p>}
        {s.past?.length > 0 && <small className="m-dim">Last crowned: {s.past.map(w => (w.top || []).slice(0, 1).map(t => t.name).join('')).filter(Boolean).join(' · ') || '—'}</small>}</div>
    </div>
    <small className="m-dim">Battle length, auto-card coins/pools and season boost live in ⚡ Engine and 🃏 Card rules.</small>
  </section>;
}

// Cmd Ctr › Fuse › ⛓ Contract status: what is on-chain-ready and what is not. Static by design — nothing here deploys.
const PROGRAMS = [
  ['fuse_vault', 'FUSE Vault', 'SOL in → shares at NAV, mgmt + performance fees to the vault fee wallet, pause never blocks exits.',
    [['Custody, shares, fees, admin, pause', true], ['NAV = SOL held (no value reporting)', true], ['Pool adapters (Raydium / Orca / Meteora)', false], ['Rebalance crank', false]],
    'cargo test -p fuse_vault --lib && anchor test --skip-local-validator'],
  ['fuse_card', 'FUSE Card', 'One account per card, coins held by the card. Rules hard-coded (3+3 / 12 admin, profit levels, TP/SL ranges).',
    [['Owner-only toggles + withdraw any time', true], ['Keeper returns coins ONLY to the owner, only when auto is on', true],
      ['v0.2 keeper SELLS / BUYS: on-chain trigger from pool reserves, whitelisted swap program, capped slippage, balance check', true],
      ['Stop modes: pay out · park & rebuy at entry · hold; compound only into coins on the card', true], ['Localnet tests: 14 passing (mock AMM)', true],
      ['Audited venue adapter (Raydium CPMM) + TWAP / oracle bound', false], ['Devnet run → external audit → owner deploy (multisig)', false]],
    'cargo test -p fuse_card --lib && anchor test --skip-local-validator'],
];
// ⛓ Go-live checklist: every gate between localnet and real money, recorded by the owner with proof. READY only when all pass.
const GOLIVE = [['adapter', '1 · Real exchange adapter', 'Raydium CPMM adapter replaces the mock exchange (same constant-product math), wired as config.swap_program.', 'PR / commit link'],
  ['twap', '2 · Time-averaged price check', 'TWAP / oracle bound next to the spot check — spot reserves can be pushed inside one transaction.', 'PR / commit link'],
  ['devnet', '3 · Devnet run', 'Full card life on devnet with real pools: open, deposit, TP sell, park + rebuy, withdraw, close.', 'devnet tx / explorer link'],
  ['audit', '4 · External audit', 'An independent auditor reviews fuse_card + the adapter; every finding fixed or accepted in writing.', 'audit report link'],
  ['multisig', '5 · Multisig + caps', 'Upgrade authority on a multisig, small per-card caps for launch, keeper key in an HSM.', 'multisig address']];
export function GoLiveChecklist({ call }) {
  const [g, setG] = useState(null); const [proof, setProof] = useState({});
  useEffect(() => { call?.('/admin/contract/golive').then(setG).catch(() => {}); }, [call]);
  if (!call || !g) return null;
  const set = (step, done) => call('/admin/contract/golive', { method: 'POST', body: JSON.stringify({ step, done, proof: proof[step] ?? g.steps[step]?.proof ?? '' }) })
    .then(x => { setG(x); toast.success(done ? 'Gate marked passed' : 'Gate reopened'); }).catch(e => toast.error(e.message));
  return <section className={`m-card fops golive ${g.ready ? 'is-ready' : ''}`} data-testid="golive"><div className="m-row"><span className="m-label">🚦 REAL-MONEY GO-LIVE</span>
    <b className={g.ready ? 'm-pos' : 'm-neg'} data-testid="golive-verdict">{g.ready ? '✓ READY for a capped mainnet launch' : `NOT READY · ${GOLIVE.filter(([k]) => !g.steps[k]?.done).length} gates open`}</b></div>
    <ol className="golive-list">{GOLIVE.map(([k, t, why, ph]) => { const st = g.steps[k] || {}; return <li key={k} className={st.done ? 'ok' : ''}>
      <div><b>{st.done ? '✓' : '⏳'} {t}</b><small className="m-dim">{why}</small></div>
      <input className="m-input" placeholder={ph} value={proof[k] ?? st.proof ?? ''} onChange={e => setProof(p => ({ ...p, [k]: e.target.value }))} aria-label={`${t} proof`} />
      <button type="button" className={`m-btn ${st.done ? '' : 'primary'}`} onClick={() => set(k, !st.done)} data-testid={`golive-${k}`}>{st.done ? 'Reopen' : 'Mark passed'}</button></li>; })}</ol>
    <small className="m-dim">Only the creator wallet can mark a gate passed (audited). Workaround until then: real-money tests run through normal one-click Fuse cards — your wallet signs every trade.</small></section>;
}

export function ContractStatus({ call }) {
  return <section className="m-card fops" data-testid="contract-status"><GoLiveChecklist call={call} />
    <div className="m-note warn"><b>LOCALNET ONLY · NOT AUDITED · NOT DEPLOYED</b><span>Nothing here can hold real money. Order of work: adapters → devnet run → external audit → deploy with the owner's keys + a multisig upgrade authority.</span></div>
    <div className="fops-cols">{PROGRAMS.map(([id, name, what, steps, cmd]) => <div key={id} className="fops-box"><header><b>⛓ {name}</b><code>contracts/fuse_vault/programs/{id}</code></header>
      <p className="m-dim fops-what">{what}</p>
      <ul className="fops-steps">{steps.map(([t, ok]) => <li key={t} className={ok ? 'ok' : ''}><i>{ok ? '✓' : '⏳'}</i>{t}</li>)}</ul>
      <small className="m-dim">Test: <code>{cmd}</code></small></div>)}</div>
  </section>;
}

// Cmd Ctr › ⚡ Engine: ONE dial sets the runner engine (gates + lanes) — Safe / Balanced (recommended) / Degen. Fine-tune below.
export function EngineDial({ call }) {
  const [c, setC] = useState(null);
  const load = () => call('/admin/runners/config').then(setC).catch(() => {});
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  if (!c?.dials) return null;
  const pick = dial => call('/admin/runners/config', { method: 'POST', body: JSON.stringify({ dial }) })
    .then(r => { toast.success(`Engine: ${c.dials[dial].label} — ${c.dials[dial].why}`); setC(x => ({ ...x, dial: r.dial, cfg: r.cfg })); window.dispatchEvent(new Event('feeless:runners')); }).catch(e => toast.error(e.message));
  return <section className="m-card fops" data-testid="engine-dial"><div className="m-row"><span className="m-label">🎚 ENGINE DIAL</span><small className="m-dim">one choice sets every gate + lane exit · fine-tune below makes it Custom</small></div>
    <RiskDial value={c.dial || 'custom'} onChange={pick} dials={c.dials} noProof testid="engine" />
    <label className="m-toggle" data-tip="Every runner round the engine switches to the dial with the PROVEN better record (8+ rounds, avg > 0, ≥2 pts ahead). Logged in the audit log + your inbox."><input type="checkbox" checked={c.autoTune !== false} onChange={e => call('/admin/runners/autotune', { method: 'POST', body: JSON.stringify({ on: e.target.checked }) }).then(r => setC(x => ({ ...x, autoTune: r.autoTune }))).catch(err => toast.error(err.message))} data-testid="engine-autotune" /><span>🔧 Auto-strength every round</span></label></section>;
}

// Cmd Ctr › Fee 🐱: FeeCat tunes the engine in ONE click — she reads the dial proof (which Safe/Balanced/Degen engine actually
// paid over the last rounds) + the stronger-config finder, then applies both (the server audits every change).
export const bestDial = dials => Object.entries(dials || {}).filter(([, p]) => p.rounds >= 8 && p.avgPct > 0)
  .sort((a, b) => b[1].avgPct * (b[1].winRate || 1) - a[1].avgPct * (a[1].winRate || 1))[0] || null;
export function FeeCatTune({ call }) {
  const [s, setS] = useState(null); const [a, setA] = useState(null); const [busy, setBusy] = useState(false);
  const load = () => Promise.all([call('/admin/runners/suggest').then(setS).catch(() => {}), fetch(apiUrl('/api/reputation/fuses/arena')).then(r => r.json()).then(setA).catch(() => {})]);
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  if (!s && !a) return <div className="fl-row is-ghost" />;
  const best = bestDial(a?.dials); const sug = s?.suggestions || [];
  const nothing = !sug.length && (!best || best[0] === a?.engineDial);
  const tune = async () => {
    setBusy(true);
    try {
      if (best && best[0] !== a?.engineDial) await call('/admin/runners/config', { method: 'POST', body: JSON.stringify({ dial: best[0] }) });
      if (sug.length) await call('/admin/runners/config', { method: 'POST', body: JSON.stringify({ cfg: Object.fromEntries(sug.map(x => [x.key, x.to])) }) });
      toast.success(`🐱 FeeCat tuned the engine${best ? ` · ${best[0]} dial (${best[1].avgPct >= 0 ? '+' : ''}${best[1].avgPct}% avg over ${best[1].rounds} rounds)` : ''}${sug.length ? ` · ${sug.length} settings` : ''}`);
      window.dispatchEvent(new Event('feeless:runners')); load();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  return <section className="m-card m-live fops" data-testid="feecat-tune"><div className="m-row"><span className="m-label">🐱 FEECAT · ENGINE TUNE</span><small className="m-dim">she learns from the dial proof + every settled round · you click once</small></div>
    <div className="fops-row">
      <div className="fops-tile" data-tip="The engine dial with the best average round (≥8 rounds, avg > 0)"><small>BEST PROVEN DIAL</small><b className="m-num">{best ? best[0] : '—'}</b><em>{best ? `${best[1].avgPct >= 0 ? '+' : ''}${best[1].avgPct}% avg · ${best[1].winRate}% won · ${best[1].rounds} rounds` : 'not enough rounds yet'}</em></div>
      <div className="fops-tile"><small>RUNNING NOW</small><b className="m-num">{a?.engineDial || 'custom'}</b><em>engine dial</em></div>
      <div className="fops-tile" data-tip={sug.map(x => `${x.key}: ${x.now} → ${x.to} (${x.why})`).join('\n') || 'Nothing stronger found'}><small>STRONGER SETTINGS</small><b className="m-num">{sug.length}</b><em>{sug[0]?.why || 'engine is up to date'}</em></div>
    </div>
    <FeeCatBrain />
    <button type="button" className="m-btn primary m-go" disabled={busy || nothing} onClick={tune} data-testid="feecat-tune-go">{nothing ? '✓ Engine already at FeeCat\'s best' : busy ? 'Tuning…' : '🐱 Let FeeCat tune the engine'}</button></section>;
}

// 🧪 Engine playground overview: every scenario the engines run (strategy runs, bloodline, dial proofs per window, top-tier
// cards, runner rounds, lit cards), the auto-tune log, and the READY-for-Arena list with the evidence for each.
export function EnginePlayground({ call }) {
  const [p, setP] = useState(null); const [pick, setPick] = useState(null);
  useEffect(() => { let alive = true; const load = () => call('/admin/fuses/playground').then(x => alive && setP(x)).catch(() => {});
    load(); const t = setInterval(() => !document.hidden && load(), 60000); return () => { alive = false; clearInterval(t); }; }, [call]);
  if (!p) return <div className="fl-row is-ghost" />;
  // ⭐ a winning scenario card → a published Cmd Ctr Fuse staged on the Arena (its exits in the tagline; edit in this panel below)
  const publishScenario = sc => call('/admin/fuses', { method: 'POST', body: JSON.stringify({ name: (sc.name || '').split(' ').slice(1).join(' ') || `${sc.label} · ${sc.window}`.slice(0, 40), emoji: (sc.name || '🧪').split(' ')[0], creatorBps: 0, enabled: true, arena: true,
    dial: sc.dial || '', cfg: sc.cfg || null, fromScenario: sc.id,
    tagline: `Engine scenario: TP +${sc.tp}% / stop −${sc.sl}% · avg ${sc.avgPct >= 0 ? '+' : ''}${sc.avgPct}% over ${sc.rounds} rounds`, legs: sc.legs.map(l => ({ chainId: 'solana', pairAddress: l.pairAddress, weight: l.weight })) }) })
    .then(() => toast.success(`⭐ ${sc.name || sc.label} published to the Arena stage`)).catch(e => toast.error(e.message));
  const c = p.counts; const fmt = v => `${v >= 0 ? '+' : ''}${Number(v || 0).toFixed(1)}%`;
  const tiles = [['🏟 Strategy runs', c.arenaRuns, `${c.settled} settled · ${c.open} live`], ['🧬 Bloodline', c.bloodline, 'saved champions seed new breeds'],
    ['🎚 Dial scenarios', c.dialScenarios, 'rounds × dials × 6h/24h/72h'], ['🏃 Runner rounds', c.runnerRounds, `${c.litCards} lit cards`], ['⭐ Tier cards', c.tierCards, 'fully auto, paper'], ['📣 Published', c.published, 'on Trade + Arena when staged']];
  return <section className="m-card m-live fops pg" data-testid="engine-playground">
    <div className="m-row"><span className="m-label">🧪 ENGINE PLAYGROUND · v.001</span><small className="m-dim">engine dial <b>{p.engineDial}</b> · auto-strength {p.autoTune ? 'on' : 'off'}</small></div>
    <div className="pg-tiles">{tiles.map(([l, n, sub], i) => <div key={l} className="pg-tile" style={{ '--i': i }}><small>{l}</small><b className="m-num fl-tick" key={n}>{Number(n || 0).toLocaleString()}</b><em>{sub}</em></div>)}</div>
    <div className="pg-cols">
      <div className="pg-box is-ready"><header><b>✅ Ready for the Arena</b><small>{p.ready.length}</small></header>{p.ready.length ? p.ready.map((r, i) => <div key={i} className="pg-row"><i>{r.kind}</i><b>{r.name}</b><small>{r.why}</small></div>) : <p className="m-dim">Nothing proven yet — the engines keep testing.</p>}</div>
      <div className="pg-box"><header><b>⏳ Still proving</b><small>{p.proving.length}</small></header>{p.proving.slice(0, 10).map((r, i) => <div key={i} className="pg-row"><i>{r.kind}</i><b>{r.name}</b><small>{r.why}</small></div>)}</div>
    </div>
    {p.scenarioCards?.length > 0 && <div className="pg-box is-ready"><header><b>🏆 Best scenarios → cards</b><small>this round's gated runners + a SOL anchor, played with each winning exit plan · auto-updated every round</small></header>
      <div className="pg-cards">{p.scenarioCards.map((sc, i) => <article key={sc.id} className="pg-card" style={{ '--i': i }} data-testid={`pg-card-${sc.id}`}>
        <b className="pg-name">{i === 0 ? '👑 ' : ''}{sc.name || sc.label}{sc.dial && <em className={`pg-dial dl-${sc.dial}`}>{sc.dial}</em>}</b><small>{sc.label} · {sc.window}{sc.cfg ? ` · ⟳ ${sc.cfg.rotateHours}h · ${sc.cfg.slMode}` : ''}</small>
        <b className="m-num m-pos">{fmt(sc.avgPct)} <em>avg / round</em></b>
        <span className="pg-legs">{sc.legs.map(l => <i key={l.pairAddress} className={l.role === 'anchor' ? 'is-anchor' : ''}>{l.role === 'anchor' ? '⚓' : '🏃'} ${l.symbol} {Math.round(l.weight)}%</i>)}</span>
        <small className="m-dim">TP +{sc.tp}% · stop −{sc.sl}% per runner · {sc.rounds} rounds · {sc.winRate}% won · $1 → ${Number(sc.per1 || 1).toFixed(2)}</small>
        <button type="button" className="m-btn primary m-go" onClick={() => publishScenario(sc)} data-testid={`pg-pub-${sc.id}`}>⭐ Publish to Arena</button></article>)}</div></div>}
    {p.scenarios?.length > 0 && <div className="pg-box"><header><b>🃏 Engine-cycled scenarios · {p.scenarios.length}</b><small>every runner round replayed under each exit plan · tap a card</small></header>
      <div className="pg-scen">{p.scenarios.map((sc, i) => <button key={sc.id} type="button" className={`pg-sc ${pick === sc.id ? 'is-on' : ''} ${sc.avgPct > 0 ? 'up' : sc.avgPct < 0 ? 'down' : ''}`} style={{ '--i': Math.min(i, 20) }} onClick={() => setPick(pick === sc.id ? null : sc.id)} data-testid={`pg-sc-${sc.id}`}>
        <small>{i === 0 && sc.rounds ? '👑 BEST · ' : ''}{sc.kind === 'dial' ? 'DIAL' : 'EXITS'} · {sc.window}</small><b>{sc.label}</b>
        <em className={`m-num ${sc.avgPct >= 0 ? 'm-pos' : 'm-neg'}`}>{sc.rounds ? fmt(sc.avgPct) : '—'}</em>
        {pick === sc.id && <span className="pg-sc-more">{sc.rounds || 0} rounds · {sc.winRate || 0}% won · $1 → ${Number(sc.per1 || 1).toFixed(2)}<br />take-profit +{sc.tp}% · stop −{sc.sl}% on every pick of every round, real prices after the round.</span>}</button>)}</div></div>}
    <div className="pg-box"><header><b>🎚 Dials across windows</b><small>same dial must win ≥ 2 windows before auto-strength switches</small></header>
      <table className="vd-table"><thead><tr><th>Dial</th>{Object.keys(p.dials).map(w => <th key={w}>{w}</th>)}</tr></thead><tbody>{Object.keys(Object.values(p.dials)[0] || {}).map(d => <tr key={d}><td>{d}</td>
        {Object.keys(p.dials).map(w => { const v = p.dials[w][d] || {}; return <td key={w} className={v.avgPct > 0 ? 'm-pos' : v.avgPct < 0 ? 'm-neg' : ''}>{v.rounds ? `${fmt(v.avgPct)} · ${v.rounds}r` : '—'}</td>; })}</tr>)}</tbody></table></div>
    {p.board.length > 0 && <div className="pg-box"><header><b>🏟 Strategies</b><small>$5 paper runs, settled after 24h</small></header>{p.board.map(r => <div key={r.style} className="pg-row"><b>{r.style}</b><small>{r.runs} runs · {r.winRate}% won</small><em className={r.avgPct >= 0 ? 'm-pos' : 'm-neg'}>{fmt(r.avgPct)}</em></div>)}</div>}
    {p.gateRegret?.length > 0 && <div className="pg-box"><header><b>💡 Gate regret</b><small>coins a gate stopped that later ran 3×+ — a high rate means that ONE gate may be too strict</small></header>
      {p.gateRegret.slice(0, 6).map(g => <div key={g.gate} className="pg-row"><b>{g.gate}</b><small>{g.ran} of {g.stopped} ran 3×+{g.examples?.length ? ` · ${g.examples.join(', ')}` : ''}</small><em className={g.rate >= 20 ? 'm-neg' : 'm-dim'}>{g.rate}%</em></div>)}</div>}
    {p.autoLog.length > 0 && <div className="pg-box"><header><b>🔧 Engine changes</b><small>auto + manual, newest first</small></header>{p.autoLog.map((a, i) => <div key={i} className="pg-row"><small>{new Date(a.at * 1000).toLocaleString()}</small><b>{a.admin === 'engine-auto' ? '🤖 auto' : '👤'}</b><small>{String(a.detail).slice(0, 110)}</small></div>)}</div>}
  </section>;
}


// 🐱 FeeCat's OWN auto-strength (feecat_service: entry tuning + exit learning), live — she tightens on bad days, eases in a
// drought, and loosens exits she cut too early. Read-only: she may only ever make herself trade LESS.
const MODE = { warming: '🌡 warming up', tightening: '🔒 tightening', holding: '⏸ holding', 'drought-relax': '🌊 easing (drought)', normal: '✓ steady' };
export function FeeCatBrain() {
  const [b, setB] = useState(null);
  useEffect(() => { fetch(apiUrl('/api/cats/brain')).then(r => r.json()).then(setB).catch(() => {}); }, []);
  if (!b) return null;
  const moved = Object.entries(b.entry || {}).filter(([, v]) => v.now !== v.default);
  return <div className="fc-brain" data-testid="feecat-brain"><div className="m-row"><b>🐱 Her own auto-strength</b><span className="m-chip">{MODE[b.mode] || b.mode}</span><small className="m-dim">{b.good} good exits · {b.missed} cut early</small></div>
    {moved.length > 0 && <div className="fc-moved">{moved.map(([k, v]) => <span key={k} className="m-chip" data-tip={`default ${v.default}`}>{k} {v.default} → <b>{v.now}</b></span>)}</div>}
    {b.log?.length > 0 && <ul className="fc-log">{b.log.slice(0, 4).map((l, i) => <li key={i}><small className="m-dim">{new Date(l.at * 1000).toLocaleString()}</small> {l.symbol ? `$${l.symbol} · ` : ''}{l.note}</li>)}</ul>}</div>;
}

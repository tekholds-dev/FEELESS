import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { Countdown } from '../RunnersPanel';
import '../../styles/fusePage.css';
import { toast } from 'sonner';
import { RiskDial, DialBoard } from '../RiskDial';

// Cmd Ctr › Fuse › ⚔ Arena ops: the live battlefield (pairs, move since the bell, time left), the last results, what's
// on the stage (by kind) and this week's season board. Read-only views of the public Arena + Season data (60s).
const pct = v => `${v >= 0 ? '+' : ''}${Number(v || 0).toFixed(1)}%`;
const KIND = { auto: '🤖 Auto card', mega: '⚛️ Cmd Ctr', user: '👤 Trader', lit: '🔥 Lit runners', round: '⏳ Proving', feecat: '🐱 FeeCat' };

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
export function ContractStatus() {
  return <section className="m-card fops" data-testid="contract-status">
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
    <RiskDial value={c.dial || 'custom'} onChange={pick} dials={c.dials} noProof testid="engine" /></section>;
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
    <button type="button" className="m-btn primary m-go" disabled={busy || nothing} onClick={tune} data-testid="feecat-tune-go">{nothing ? '✓ Engine already at FeeCat\'s best' : busy ? 'Tuning…' : '🐱 Let FeeCat tune the engine'}</button></section>;
}

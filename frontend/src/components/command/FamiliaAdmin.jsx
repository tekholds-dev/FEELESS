import { FamiliaOverwatch } from './FamiliaOverwatch';
import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import '../../styles/familiaAdmin.css';
import { shaped } from '../../lib/shape';
const FAMILIA = shaped({ rules: {}, economy: { cities: [], families: 0, members: 0, raids: 0, raidsLive: 0, bankMp: 0, houseMp: 0, topBankMp: 0 }, range: {} });

// 🏙 HQ › Build › Familia — the creator's control center (owner, 2026-10-21: "a huge FEELESS creator-wallet-only control center in Familia so I
// can sort the real logic out"). The economy right now (families, MP banks, the house, raids, every city's plots), the LIVE rules the engine
// uses this second, the PLANNED real-money prices (stored, applied once custody is picked) and a paid-hit calculator on the same math as the
// server (family_world.paid_hit_payout).
const n = x => Math.round(Number(x) || 0).toLocaleString('en-US');
const LIVE = [['blockMp', '🧱 PLOT PRICE', 'MP for a plot at ×1 (outer cities scale by tier, every extra plot +60 %)'],
  ['feeTier', '👑 FEE CITY ×', 'Fee City plots: price AND production multiplier'], ['turfMax', '🗺 TURF CAP', 'Plots a family may hold beyond home'],
  ['moveMp', '🚚 MOVE HOME', 'MP to move the home block (×tier, the gas station cuts it)'], ['fuseMinMp', '⚔ FAMILY FUSE MIN', 'MP a family needs in the bank for an MP Family Fuse']];
const PLANNED = [['familiesPerWallet', '👥 FAMILIES / WALLET', ''], ['createUsd', '💵 START A FAMILY $', ''], ['createFeeUsd', '🏦 OF IT TO FEE $', ''],
  ['hitMinUsd', '🎯 MIN PAID HIT $', ''], ['hitRate', '📐 HIT RATE', 'share of the stake a won hit takes'], ['hitCapUsd', '🧢 HIT CAP $', 'never more than this per hit']];

// pure: the same payout the server computes — stake × rate, nudged by the size gap (√ of target ÷ sender, 0.05–2), capped, ≤ 0.01 % of the target
export function hitPayout(stake, sender, target, rate, cap) {
  const gap = Math.sqrt(Math.min(2, Math.max(0.05, Math.max(0, target) / Math.max(0.01, sender))));
  return Math.round(Math.min(cap, Math.max(0, stake) * rate * gap, Math.max(0, target) * 0.0001) * 1e6) / 1e6;
}

function Field({ k, label, tip, val, range, onChange, live }) {
  const [lo, hi] = range || [0, 1e9];
  return <label className={`fad-f ${live ? 'is-live' : ''}`} data-tip={tip || label}><em>{label}</em>
    <input className="m-input" type="number" step="any" min={lo} max={hi} value={val ?? ''} onChange={e => onChange(k, e.target.value)} data-testid={`fad-${k}`} /></label>;
}

export function FamiliaAdmin({ call }) {
  const [d, setD] = useState(null); const [r, setR] = useState({}); const [busy, setBusy] = useState(false);
  const [sim, setSim] = useState({ stake: 5, sender: 100, target: 1000 });
  const load = () => call('/admin/familia/rules').then(x => { const y = FAMILIA(x); setD(y); setR(y.rules); }).catch(e => toast.error(e.message));
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) call('/admin/familia/rules').then(x => setD(FAMILIA(x))).catch(() => {}); }, 20000); return () => clearInterval(t); }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  const set = (k, v) => setR(x => ({ ...x, [k]: v }));
  const save = async () => { setBusy(true); try { const x = await call('/admin/familia/rules', { method: 'POST', body: JSON.stringify(r) }); const y = FAMILIA(x); setD(y); setR(y.rules); toast.success('Familia rules saved — live ones apply now'); } catch (e) { toast.error(e.message); } setBusy(false); };
  if (!d) return <p className="cc-empty">Reading the city…</p>;
  const e = d.economy; const pay = hitPayout(+sim.stake, +sim.sender, +sim.target, +r.hitRate || 0, +r.hitCapUsd || 0);
  return <section className="fad m-stack" data-testid="familia-admin">
    <FamiliaOverwatch call={call} />
    <div className="fad-kpis m-card m-live">{[['FAMILIES', e.families], ['MEMBERS', e.members], ['MP IN BANKS', e.bankMp], ['TOP BANK', e.topBankMp], ['🏦 THE HOUSE', e.houseMp], ['RAIDS LIVE', e.raidsLive], ['RAIDS 24H', e.raids24h]]
      .map(([k, v], i) => <span key={k} style={{ '--i': i }}><b key={v} className="m-num">{n(v)}</b><em>{k}</em></span>)}</div>
    <div className="fad-cities m-card"><span className="m-label">🗺 PLOTS HELD PER CITY</span>{e.cities.map((c, i) => <p key={c.key} className={c.key === 'fee' ? 'is-fee' : ''} style={{ '--i': i }}>
      <b>{c.name}</b><u><s style={{ transform: `scaleX(${c.plots ? Math.max(0.02, c.held / c.plots) : 0})` }} /></u><em key={c.held}>{c.held}/{c.plots}</em><small>{n(d.blockPrice[c.key] || 0)} MP</small></p>)}</div>
    <div className="fad-grid">
      <div className="m-card fad-box"><header><span className="m-label">⚡ LIVE RULES · the engine uses these now</span></header>
        <div className="fad-fields">{LIVE.map(([k, l, t]) => <Field key={k} k={k} label={l} tip={t} val={r[k]} range={d.range[k]} onChange={set} live />)}</div>
        <p className="m-note">A Fee City plot costs <b>{n((+r.blockMp || 0) * (+r.feeTier || 0))} MP</b> at ×1 · an MP Family Fuse needs <b>{n(r.fuseMinMp)} MP</b>.</p></div>
      <div className="m-card fad-box is-planned"><header><span className="m-label">💵 REAL MONEY · priced now, live after the custody pick</span></header>
        <div className="fad-fields">{PLANNED.map(([k, l, t]) => <Field key={k} k={k} label={l} tip={t} val={r[k]} range={d.range[k]} onChange={set} />)}</div>
        <p className="m-note">Start a family: <b>${(+r.createUsd || 0).toFixed(2)}</b> → <b>${(+r.createFeeUsd || 0).toFixed(2)}</b> to FEE + <b>${Math.max(0, (+r.createUsd || 0) - (+r.createFeeUsd || 0)).toFixed(2)}</b> into the new family wallet.</p></div>
      <div className="m-card fad-box fad-sim"><header><span className="m-label">🎯 PAID-HIT CALCULATOR</span></header>
        {[['stake', 'HIT STAKE $'], ['sender', 'SENDER WALLET $'], ['target', 'TARGET WALLET $']].map(([k, l]) => <label key={k} className="fad-f"><em>{l}</em>
          <input className="m-input" type="number" min="0" step="any" value={sim[k]} onChange={ev => setSim(s => ({ ...s, [k]: ev.target.value }))} data-testid={`fad-sim-${k}`} /></label>)}
        <div className="fad-pay"><em>A WON HIT TAKES</em><b key={pay} data-testid="fad-pay">${pay.toFixed(6)}</b><small>{+sim.target > +sim.sender ? `punching up ×${(+sim.target / Math.max(0.01, +sim.sender)).toFixed(1)}` : 'bullying a smaller family pays less'} · cap ${(+r.hitCapUsd || 0).toFixed(2)}</small></div></div>
    </div>
    <button type="button" className="m-btn m-go fad-save" disabled={busy} onClick={save} data-testid="fad-save" data-tip="Saves every rule; the live ones change the game at once">{busy ? 'Saving…' : 'Save Familia rules'}</button>
  </section>;
}

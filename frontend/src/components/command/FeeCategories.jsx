import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import NumInput from '../NumInput';
import '../../styles/feeCats.css';

// 💲 HQ › Core › FEES BY CATEGORY (owner, 2026-10-30: "the fees tab needs categories for the different things we charge for — agents, families,
// trading…"). One segmented bar, one panel per product: 💱 Trading (the swap fee editor + money flows + the fee book) · 🤖 Agents (FEELESS's
// one-time cut from a cat's first funding; agent swaps pay the trading fee; staff-owned agents pay none) · 🧬 Fuse (every Fuse fee) ·
// 👨‍👩‍👧 Families (start a family, +5 seats, what they've paid). Each panel reads the live config and saves through the same admin routes.
export const FEE_CATS = [['trading', '💱 Trading', 'Every swap: the FEELESS fee, tiers, promo, engine, the fee book'], ['agents', '🤖 Agents', 'FeeCat agents: the one-time funding cut and how their swaps are charged'],
  ['fuse', '🧬 Fuse', 'Fuse cards: first buys, card swaps / sells, round packs'], ['families', '👨‍👩‍👧 Families', 'Familia: start a family, add seats, what families paid']];
const KEY = 'feeless.hq.feeCat';
const pct = bps => `${((Number(bps) || 0) / 100).toFixed(2)}%`;
const usd = v => `$${(Number(v) || 0).toFixed(2)}`;

function useFees(call) {
  const [d, setD] = useState(null);
  const load = useCallback(() => call('/admin/fees').then(setD).catch(() => setD({ fees: {} })), [call]);
  useEffect(() => { load(); }, [load]);
  return [d, load];
}

export function AgentFees({ call }) {
  const [d, load] = useFees(call); const [cut, setCut] = useState(''); const [tradeFee, setTradeFee] = useState(''); const [otherFee, setOtherFee] = useState('');
  useEffect(() => { if (d?.fees) { setCut(String(d.fees.catFeeUsd ?? 2)); setTradeFee(String(d.fees.agentTradeFeeUsd ?? 0.05)); setOtherFee(String(d.fees.agentOtherFeeUsd ?? 0.1)); } }, [d]);
  if (!d) return <p className="cc-empty">Loading agent fees…</p>;
  const f = d.fees || {}; const n = Number(cut);
  const save = async () => {
    try { await call('/admin/fees', { method: 'POST', body: JSON.stringify({ ...f, catFeeUsd: Math.max(0, Math.min(100, n || 0)), agentTradeFeeUsd: Math.max(0, Math.min(10, Number(tradeFee) || 0)), agentOtherFeeUsd: Math.max(0, Math.min(10, Number(otherFee) || 0)) }) }); toast.success('Agent fees saved'); load(); }
    catch (e) { toast.error(e.message); }
  };
  return <section className="m-card m-live fct-panel" data-testid="fee-cat-agents">
    <header className="m-row"><span className="m-label">🤖 AGENTS · WHAT A CAT PAYS</span><small className="m-dim">fee rules apply to its own wallet</small></header>
    <div className="fct-meters">
      <span className="fct-meter"><em>ONE-TIME CUT</em><b className="m-num">{usd(f.catFeeUsd ?? 2)}</b><i><u style={{ transform: `scaleX(${Math.min(1, (Number(f.catFeeUsd ?? 2)) / 10)})` }} /></i><small>out of a first funding (≥ $10)</small></span>
      <span className="fct-meter"><em>EACH TRADE</em><b className="m-num">${Number(f.agentTradeFeeUsd ?? 0.05).toFixed(2)}</b><i><u style={{ transform: `scaleX(${Math.min(1, Number(f.agentTradeFeeUsd ?? 0.05))})` }} /></i><small>flat, per swap or trench trade</small></span>
      <span className="fct-meter"><em>EVERYTHING ELSE</em><b className="m-num">${Number(f.agentOtherFeeUsd ?? 0.1).toFixed(2)}</b><i><u style={{ transform: `scaleX(${Math.min(1, Number(f.agentOtherFeeUsd ?? 0.1))})` }} /></i><small>flat, per finished task</small></span>
      <span className="fct-meter is-free"><em>STAFF-OWNED</em><b className="m-num">0%</b><i><u style={{ transform: 'scaleX(1)' }} /></i><small>agents your wallets own trade free</small></span>
      <span className="fct-meter"><em>TOP-UPS</em><b className="m-num">$0</b><i><u style={{ transform: 'scaleX(0.02)' }} /></i><small>no cut after the first funding</small></span>
    </div>
    <label className="fct-edit"><span>One-time cut · $</span><NumInput className="m-input" type="number" min="0" max="100" step="0.5" value={cut} onChange={e => setCut(e.target.value)} aria-label="Agent one-time cut in dollars" data-testid="fct-cat-cut" />
      <span>Each trade · $</span><NumInput className="m-input" type="number" min="0" max="10" step="0.01" value={tradeFee} onChange={e => setTradeFee(e.target.value)} aria-label="Agent fee per trade in dollars" data-testid="fct-agent-trade" />
      <span>Everything else · $</span><NumInput className="m-input" type="number" min="0" max="10" step="0.01" value={otherFee} onChange={e => setOtherFee(e.target.value)} aria-label="Agent fee per task in dollars" data-testid="fct-agent-other" />
      <button type="button" className="m-btn m-go" onClick={save} disabled={!Number.isFinite(n) || (n === Number(f.catFeeUsd ?? 2) && Number(tradeFee) === Number(f.agentTradeFeeUsd ?? 0.05) && Number(otherFee) === Number(f.agentOtherFeeUsd ?? 0.1))} data-testid="fct-cat-save" data-tip="Applies to the next charge">Save</button></label>
    <p className="m-note">Model calls are separate: a cat runs on its FEELESS model credit, or on its owner's own OpenRouter key from its 🔐 API drawer (they pay OpenRouter; no FEELESS credit). Agent wallets pay these flat fees instead of the % swap fee set in 💱 Trading.</p>
  </section>;
}

export function FamilyFees({ call }) {
  const [d, load] = useFees(call); const [rev, setRev] = useState(null); const [v, setV] = useState({ createUsd: '', packUsd: '' });
  useEffect(() => { call('/admin/crews/revenue').then(setRev).catch(() => setRev(null)); }, [call]);
  useEffect(() => { const c = d?.fees?.crews || {}; setV({ createUsd: String(c.createUsd ?? ''), packUsd: String(c.packUsd ?? '') }); }, [d]);
  if (!d) return <p className="cc-empty">Loading family fees…</p>;
  const c = d.fees?.crews || {};
  const save = async () => {
    try { await call('/admin/fees/crews', { method: 'POST', body: JSON.stringify({ createUsd: Number(v.createUsd) || 0, packUsd: Number(v.packUsd) || 0 }) }); toast.success('Family prices saved'); load(); }
    catch (e) { toast.error(e.message); }
  };
  return <section className="m-card m-live fct-panel" data-testid="fee-cat-families">
    <header className="m-row"><span className="m-label">👨‍👩‍👧 FAMILIES · WHAT A FAMILY PAYS</span><small className="m-dim">the creator sets these</small></header>
    <div className="fct-meters">
      <span className="fct-meter"><em>START A FAMILY</em><b className="m-num">{usd(c.createUsd)}</b><i><u style={{ transform: `scaleX(${Math.min(1, (Number(c.createUsd) || 0) / 100)})` }} /></i><small>5 seats incl. the owner</small></span>
      <span className="fct-meter"><em>+5 SEATS</em><b className="m-num">{usd(c.packUsd)}</b><i><u style={{ transform: `scaleX(${Math.min(1, (Number(c.packUsd) || 0) / 50)})` }} /></i><small>per seat pack</small></span>
      <span className="fct-meter is-gold"><em>FAMILIES PAID</em><b className="m-num">{rev ? usd(rev.totalUsd) : '—'}</b><i><u style={{ transform: `scaleX(${rev ? Math.min(1, (rev.totalUsd || 0) / 1000) : 0.02})` }} /></i><small>{rev ? `${rev.payments} payments · ${rev.crews} families` : 'reading…'}</small></span>
    </div>
    <div className="fct-edit">
      <label><span>Start · $</span><NumInput className="m-input" type="number" min="0" max="500" step="1" value={v.createUsd} onChange={e => setV(x => ({ ...x, createUsd: e.target.value }))} aria-label="Start a family price" data-testid="fct-fam-create" /></label>
      <label><span>+5 seats · $</span><NumInput className="m-input" type="number" min="0" max="500" step="1" value={v.packUsd} onChange={e => setV(x => ({ ...x, packUsd: e.target.value }))} aria-label="Seat pack price" data-testid="fct-fam-pack" /></label>
      <button type="button" className="m-btn m-go" onClick={save} data-testid="fct-fam-save" data-tip="Creator only — applies to the next family">Save</button></div>
  </section>;
}

export function FeeCategories({ call, Trading, Fuse }) {
  const [cat, setCat] = useState(() => { try { const k = localStorage.getItem(KEY); return FEE_CATS.some(c => c[0] === k) ? k : 'trading'; } catch { return 'trading'; } });
  const pick = k => { setCat(k); try { localStorage.setItem(KEY, k); } catch { /* private window */ } };
  return <div className="fct" data-testid="fee-categories">
    <nav className="m-seg fct-seg" role="tablist" aria-label="Fee categories">{FEE_CATS.map(([k, l, tip], i) => <button key={k} type="button" role="tab" aria-selected={cat === k}
      className={cat === k ? 'is-on' : ''} style={{ '--i': i }} onClick={() => pick(k)} data-tip={tip} data-testid={`fct-${k}`}>{l}</button>)}</nav>
    {cat === 'trading' ? Trading : cat === 'agents' ? <AgentFees call={call} /> : cat === 'fuse' ? Fuse : <FamilyFees call={call} />}
  </div>;
}

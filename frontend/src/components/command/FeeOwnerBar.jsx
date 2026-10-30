import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Panther, COATS } from '../Panther';
import { LOOK } from './CatLook';
import { PATTERNS } from './CatBuilder';
import { CatReal, realView } from './CatReal';
import { useAdmin } from '../../lib/adminCall';
import { useWallet } from '../../hooks/useWallet';
import { getChatSession } from '../../lib/chatSession';
import '../../styles/feeOwner.css';

// 👑 THE CREATOR'S FEE (owner, 2026-10-23: "creator controls Fee — coat / gear / eyes / name" · "I can't find where to link / fund Fee's
// wallet"): two lit pills, shown ONLY to a FEELESS owner wallet (the server re-checks the signed wallet on every write — fee_owner_real):
//   🎨 STYLE FEE   → a pop-out studio: coat · pattern · gear · eyes · aura · her name + title, live on the panther, saved for every viewer
//   👛 FEE'S WALLET → a pop-out with her REAL switch (link your wallet · per-buy budget · go real · sign her proposals)
// Same bar on the public FeeCat page (stage) and HQ › FeeCat (Fee's desk).
export const FEE_DEFAULT = { coat: 'black', pattern: 'stripes', gear: 'none', eyes: 'classic', aura: 'royal', name: 'Fee', title: '' };
export const AURA_HEX = { none: 'transparent', royal: '#b48cff', gold: '#ffcf5c', ice: '#7fe0ff', blaze: '#ff7a3d', nebula: '#e08cff', toxic: '#7dff5c' };
export const feeLook = cat => ({ ...FEE_DEFAULT, ...(cat?.look || {}), name: cat?.look?.name || cat?.name || 'Fee', title: cat?.look?.title || cat?.title || '' });
export const walletWord = cat => { const v = realView(cat); return v.real ? `REAL · ${v.pending ? `${v.pending} to sign` : 'live'}` : 'PAPER · go real'; };

async function post(action, extra) {
  const r = await fetch('/api/cats/leader/action', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action, ...extra }) });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.detail || `HTTP ${r.status}`);
  return d.cat;
}

function Pop({ title, onClose, children, k }) {
  useEffect(() => { const esc = e => e.key === 'Escape' && onClose(); window.addEventListener('keydown', esc); return () => window.removeEventListener('keydown', esc); }, [onClose]);
  return createPortal(<div className="fob-back" onClick={e => e.target === e.currentTarget && onClose()} data-testid={`fob-pop-${k}`}>
    <section className={`fob-pop is-${k}`} role="dialog" aria-modal="true" aria-label={title}>
      <header><b>{title}</b><button type="button" className="fob-x" onClick={onClose} aria-label="Close" data-tip="Close (Esc)">✕</button></header>
      {children}</section></div>, document.body);
}

function Row({ label, k, opts, l, set }) {
  return <div className="fob-row"><em>{label}</em><div className="fob-opts" role="radiogroup" aria-label={label}>
    {opts.map(([key, word, icon]) => <button key={key} type="button" role="radio" aria-checked={l[k] === key} className={l[k] === key ? 'on' : ''} onClick={() => set(k, key)}
      style={k === 'aura' ? { '--d': AURA_HEX[key] } : k === 'coat' ? { '--d': COATS[key]?.fur, '--d2': COATS[key]?.glow } : undefined} data-tip={word} data-testid={`fob-${k}-${key}`}>
      {k === 'coat' || k === 'aura' ? <i aria-hidden="true" /> : null}<span>{icon ? `${icon} ` : ''}{word}</span></button>)}</div></div>;
}

function Studio({ cat, onSaved, devAddress }) {
  const { wallet, signMessage } = useWallet() || {};
  const addr = devAddress || wallet?.address || '';
  const [l, setL] = useState(() => feeLook(cat)); const [busy, setBusy] = useState(false); const [msg, setMsg] = useState(null);
  const set = (k, v) => setL(x => ({ ...x, [k]: v }));
  const save = async () => {
    setBusy(true); setMsg(null);
    try { const session = devAddress ? 'dev' : await getChatSession(addr, signMessage, { own: true });
      onSaved(await post('look', { address: addr, session, look: l })); window.dispatchEvent(new CustomEvent('feeless:fee-look', { detail: l })); setMsg({ ok: true, text: `✓ ${l.name} wears it now — every viewer sees it` }); }
    catch (e) { setMsg({ ok: false, text: e.message || 'Not saved' }); } finally { setBusy(false); }
  };
  return <div className="fob-studio">
    <div className="fob-stage" style={{ '--aura': AURA_HEX[l.aura] || 'transparent' }} aria-hidden="true"><i className="fob-glow" /><Panther size={170} coat={l.coat} pattern={l.pattern} gear={l.gear} eyes={l.eyes} gesture="wave" />
      <b className="fob-name">{l.name}</b>{l.title ? <small>{l.title}</small> : null}</div>
    <div className="fob-picks">
      <Row l={l} set={set} label="COAT" k="coat" opts={Object.entries(COATS).map(([k, c]) => [k, c.name])} />
      <Row l={l} set={set} label="PATTERN" k="pattern" opts={PATTERNS} />
      <Row l={l} set={set} label="GEAR" k="gear" opts={LOOK.gear} />
      <Row l={l} set={set} label="EYES" k="eyes" opts={LOOK.eyes} />
      <Row l={l} set={set} label="AURA" k="aura" opts={LOOK.aura} />
      <label className="fob-in"><em>NAME</em><input className="m-input" maxLength={24} value={l.name} onChange={e => set('name', e.target.value)} data-testid="fob-name" /></label>
      <label className="fob-in"><em>TITLE</em><input className="m-input" maxLength={48} value={l.title} onChange={e => set('title', e.target.value)} placeholder="The Leader of the FEELESS Cats" data-testid="fob-title" /></label>
      <button type="button" className="m-btn m-go" disabled={busy || !addr || !l.name.trim()} onClick={save} data-testid="fob-save"
        data-tip="One signature (no transaction) proves the creator wallet — then Fee wears it for everyone">{busy ? 'Saving…' : !addr ? 'Connect the creator wallet' : `🎨 Dress ${l.name || 'Fee'}`}</button>
      {msg ? <small className={`m-note ${msg.ok ? '' : 'warn'}`} data-testid="fob-msg">{msg.text}</small> : null}
    </div>
  </div>;
}

export function FeeOwnerBar({ cat: cat0, devOwner = false, devAddress = '' }) {
  const { isAdmin } = useAdmin();
  const [cat, setCat] = useState(cat0); const [open, setOpen] = useState(null);
  useEffect(() => { if (cat0) setCat(cat0); }, [cat0]);   // the shared 15 s poll; a save shows at once (setCat) until it catches up
  if (!(isAdmin || devOwner) || !cat) return null;
  const v = realView(cat);
  const act = async (action, extra = {}) => setCat(await post(action, extra));
  return <div className="fob" data-testid="fee-owner-bar">
    <span className="fob-crown" aria-hidden="true">👑</span><small className="fob-h">CREATOR</small>
    <button type="button" className="fob-pill is-style" onClick={() => setOpen('style')} data-testid="fob-style" data-tip="Dress Fee — coat, pattern, gear, eyes, aura, her name. Every viewer sees it">🎨 STYLE FEE</button>
    <button type="button" className={`fob-pill is-wallet ${v.real ? 'is-real' : ''}`} onClick={() => setOpen('wallet')} data-testid="fob-wallet"
      data-tip="Fee's wallet: assign one you already have or give her a fresh one, fund it once — she trades from it on her own (you never sign each trade)">
      <i className="fob-dot" aria-hidden="true" />👛 FEE'S WALLET <b>{walletWord(cat)}</b>{v.pending ? <u className="fob-ping" aria-hidden="true" /> : null}</button>
    {open === 'style' ? <Pop k="style" title="🎨 STYLE FEE — every viewer sees her" onClose={() => setOpen(null)}><Studio cat={cat} onSaved={setCat} devAddress={devAddress} /></Pop> : null}
    {open === 'wallet' ? <Pop k="wallet" title="👛 FEE'S WALLET — fund it once, she trades from it" onClose={() => setOpen(null)}><CatReal cat={cat} onAct={act} devAddress={devAddress} /></Pop> : null}
  </div>;
}

import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useWallet } from '../hooks/useWallet';
import { apiUrl } from '../lib/api';
import { getChatSession } from '../lib/chatSession';
import { LOCAL_LOOKS, keepLocalLook, localLook } from '../lib/looks';
import { applyTheme } from './HolderTheme';
import '../styles/lookPicker.css';

// 🎨 LOOKS (owner 2026-11-11): pick how all of FEELESS looks. Tapping a look shows it at once; Save keeps it on your wallet (signed in)
// or on this device. Advanced looks unlock with $1,000+ held across $FEE coins (staff always): their colours come from the server only then.
const FALLBACK = Object.values(LOCAL_LOOKS).map(l => ({ id: l.id, name: l.name, tier: l.tier || 'free', line: '', ambient: l.ambient, swatch: [l.tokens.accent, l.tokens.tail, l.tokens.third, l.tokens.bg], tokens: l.tokens, locked: false }));
export function LookPicker({ compact = false }) {
  const { wallet, signMessage } = useWallet() || {};
  const [cat, setCat] = useState({ looks: FALLBACK, eligible: false, minUsd: 1000 });
  const [on, setOn] = useState(() => localLook()?.id || 'plasma'); const [busy, setBusy] = useState(false);
  useEffect(() => {
    let live = true; const a = wallet?.address && wallet.chain !== 'evm' ? wallet.address : '';
    fetch(apiUrl(`/api/reputation/looks${a ? `?address=${encodeURIComponent(a)}` : ''}`)).then(r => (r.ok ? r.json() : null)).then(j => { if (live && j?.looks) setCat(j); }).catch(() => {});
    if (a) fetch(apiUrl(`/api/reputation/theme/${a}`)).then(r => r.json()).then(d => { if (live && d?.theme?.look?.id) setOn(d.theme.look.id); }).catch(() => {});
    return () => { live = false; };
  }, [wallet?.address, wallet?.chain]);
  const pick = l => { if (l.locked) return; setOn(l.id); applyTheme({ look: { id: l.id, ambient: l.ambient, tokens: l.tokens } }); };   // a look replaces a custom colour (saving keeps only the look)
  const save = async () => {
    const l = cat.looks.find(x => x.id === on); if (!l || l.locked) return;
    setBusy(true);
    try {
      if (wallet?.address && wallet.chain !== 'evm') {
        const session = await getChatSession(wallet.address, signMessage);
        const r = await fetch(apiUrl('/api/reputation/theme'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: wallet.address, session, look: on }) });
        const d = await r.json(); if (!r.ok) throw new Error(d.detail || `HTTP ${r.status}`);
      }
      keepLocalLook(on); toast.success(`${l.name} is your FEELESS look.`);
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const free = cat.looks.filter(l => l.tier === 'free'); const elite = cat.looks.filter(l => l.tier === 'elite'); const adv = cat.looks.filter(l => l.tier !== 'free' && l.tier !== 'elite');
  const card = (l, i) => <button key={l.id} type="button" className={`lkp-card${on === l.id ? ' is-on' : ''}${l.locked ? ' is-locked' : ''}`} style={{ '--i': i, '--c1': l.swatch[0], '--c2': l.swatch[1], '--c3': l.swatch[2], '--c4': l.swatch[3] }}
    onClick={() => pick(l)} aria-pressed={on === l.id} disabled={busy} data-tip={l.locked ? `Unlocks at $${(cat.minUsd || 1000).toLocaleString()} held across $FEE coins` : l.line || l.name} data-testid={`look-${l.id}`}>
    <span className="lkp-sky" aria-hidden="true"><i /><i /><i /></span>
    <b>{l.name}</b>{l.line ? <small>{l.line}</small> : null}
    <span className="lkp-dots" aria-hidden="true">{l.swatch.map((c, i) => <i key={`${i}${c}`} style={{ background: c }} />)}</span>
    {l.locked ? <em className="lkp-lock">🔒 ADVANCED</em> : on === l.id ? <em className="lkp-on">WEARING</em> : null}</button>;
  return <section className={`lkp${compact ? ' is-compact' : ''}`} data-testid="look-picker">
    <header><span><b>Looks</b><small>How all of FEELESS looks for you. Tap to see it, then save.</small></span>
      <button type="button" className="m-btn m-go" disabled={busy || !cat.looks.find(x => x.id === on && !x.locked)} onClick={save} data-testid="look-save">{busy ? 'Saving…' : wallet?.address ? 'Save to my wallet' : 'Save on this device'}</button></header>
    <div className="lkp-grid">{free.map(card)}</div>
    {elite.length ? <><h4 className="lkp-h" data-testid="lkp-elite">ELITE EDITION<small>grown-up looks · line icons · plain type</small></h4><div className="lkp-grid">{elite.map((l, i) => card(l, free.length + i))}</div></> : null}
    {adv.length ? <><h4 className="lkp-h">ADVANCED LOOKS<small>{cat.eligible ? 'unlocked for you' : `unlock at $${(cat.minUsd || 1000).toLocaleString()} held across $FEE coins`}</small></h4><div className="lkp-grid">{adv.map((l, i) => card(l, i + free.length))}</div></> : null}
  </section>;
}

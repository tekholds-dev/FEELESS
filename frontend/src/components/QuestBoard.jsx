import React, { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { useWallet } from '../hooks/useWallet';
import { getChatSession } from '../lib/chatSession';
import { BadgeArt } from './BadgeArt';

const SETS = [['feeless', 'FEELESS'], ['frsv', 'FEE RESERVE · FRSV'], ['earned', 'Earned']];
const left = at => { const s = Math.max(0, Math.round(at - Date.now() / 1000)); const h = Math.floor(s / 3600); return h >= 24 ? `${Math.floor(h / 24)}d ${h % 24}h` : `${h}h ${Math.floor((s % 3600) / 60)}m`; };
const fmt = v => (v >= 1000 ? `${(v / 1000).toFixed(v >= 10000 ? 0 : 1)}K` : String(Math.round(v * 100) / 100));

export function useQuests(address) {
  const [d, setD] = useState(null);
  const load = React.useCallback(() => {
    if (!address) { setD(null); return; }
    fetch(apiUrl(`/api/reputation/quests/${address}`)).then(r => (r.ok ? r.json() : null)).then(x => x && setD(x)).catch(() => {});
  }, [address]);
  useEffect(() => { load(); const t = setInterval(() => !document.hidden && load(), 60000); window.addEventListener('feeless:trade-confirmed', load); return () => { clearInterval(t); window.removeEventListener('feeless:trade-confirmed', load); }; }, [load]);
  return [d, load];
}

function Quests({ title, block }) {
  return <div className="m-card qb-quests"><div className="m-row"><span className="m-label">{title}</span><small className="m-dim">resets in {left(block.resetsAt)}</small></div>
    {block.tasks.map(t => <div key={t.id} className={`qb-task ${t.done ? 'done' : ''}`} data-testid={`quest-${t.id}`}>
      <span>{t.done ? '✅' : '◻️'} {t.label}</span><b className="m-num sm">{fmt(Math.min(t.have, t.target))}/{fmt(t.target)}</b><em>+{t.xp} XP</em>
      <i className="qb-bar"><i style={{ transform: `scaleX(${Math.min(1, t.have / t.target)})` }} /></i></div>)}</div>;
}

export function BadgeDetail({ b, rarity, onClose }) {
  return <div className="qb-detail m-pop" role="dialog" aria-label={b.name} data-testid="badge-detail" onPointerDown={e => e.target === e.currentTarget && onClose()}>
    <div className="m-card"><button type="button" className="m-btn qb-x" onClick={onClose} aria-label="Close">✕</button>
      <BadgeArt art={b.art} name={b.name} live size="lg" locked={!b.earned} />
      <div className="m-row"><b className="qb-name">{b.name}</b><span className={`m-chip tier-${b.tier}`}>{b.tier}</span><span className="m-chip">+{b.xp} XP</span>{rarity != null && <span className="m-chip">held by {rarity}%</span>}</div>
      <p className="m-dim">{b.earned ? (b.granted ? 'Granted by FEELESS HQ.' : 'Earned. It shows next to your name in chat (pick it in chat ⚙).') : 'Finish every task to unlock it.'}</p>
      {b.tasks.map(t => <div key={t.id} className={`qb-task ${t.done ? 'done' : ''}`}><span>{t.done ? '✅' : '◻️'} {t.label}</span><b className="m-num sm">{fmt(Math.min(t.have, t.target))}/{fmt(t.target)}</b>
        <i className="qb-bar"><i style={{ transform: `scaleX(${t.pct / 100})` }} /></i></div>)}
    </div></div>;
}

// The badges tab: level + streak, one-tap daily check-in, daily/weekly quests, "next up", and both badge sets.
export function QuestBoard() {
  const { wallet, signMessage, connect } = useWallet() || {};
  const [d, reload] = useQuests(wallet?.address);
  const [set, setSet] = useState('feeless');
  const [open, setOpen] = useState(null);
  const [busy, setBusy] = useState(false);
  const shown = useMemo(() => (d?.badges || []).filter(b => (set === 'earned' ? b.earned : b.set === set)), [d, set]);
  if (!wallet?.address) return <section className="m-card qb-empty" data-testid="quest-board"><span className="m-label">BADGES · QUESTS</span><h2>40 animated badges. Every one earned on-chain.</h2><button type="button" className="m-btn primary m-go" onClick={() => connect?.('solana')}>Connect wallet to start</button></section>;
  if (!d) return <section className="m-card" data-testid="quest-board"><span className="loader" /> Loading your quests…</section>;
  const checkin = async () => {
    setBusy(true);
    try {
      const session = await getChatSession(wallet.address, signMessage);
      const r = await fetch(apiUrl('/api/reputation/quests/checkin'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: wallet.address, session }) });
      const x = await r.json(); if (!r.ok) throw new Error(x.detail || 'Check-in failed.');
      toast.success(x.fresh ? `🔥 Checked in · ${x.streak}-day streak` : 'Already checked in today'); reload();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const lv = d.level; const pct = lv.next ? Math.min(100, (lv.xp / lv.next) * 100) : 100;
  const checked = d.quests.daily.tasks.find(t => t.id === 'checkin')?.done;
  return <section className="quest-board" data-testid="quest-board">
    <div className="m-card m-live qb-hero">
      <div><span className="m-label">LEVEL {lv.level} · {lv.name.toUpperCase()}</span><div className="m-num">{lv.xp.toLocaleString()} XP</div>
        <i className="qb-bar big"><i style={{ transform: `scaleX(${pct / 100})` }} /></i><small className="m-dim">{lv.next ? `${(lv.next - lv.xp).toLocaleString()} XP to the next level` : 'Max level'}</small></div>
      <div className="qb-stats"><div className="m-stat"><small>STREAK</small><b className="m-num">🔥 {d.metrics.streak}</b></div><div className="m-stat"><small>BADGES</small><b className="m-num">{d.earned}/{d.total}</b></div>
        <button type="button" className={`m-btn ${checked ? '' : 'primary m-go'}`} disabled={busy || checked} onClick={checkin} data-testid="quest-checkin">{checked ? '✓ Checked in today' : busy ? 'Signing…' : '🔥 Daily check-in'}</button></div>
    </div>
    <div className="m-grid"><Quests title="DAILY QUESTS" block={d.quests.daily} /><Quests title="WEEKLY QUESTS" block={d.quests.weekly} /></div>
    {d.next?.length > 0 && <div className="m-card"><span className="m-label">NEXT UP · closest to unlocking</span><div className="qb-next">{d.next.map(id => d.badges.find(b => b.id === id)).filter(Boolean).map(b =>
      <button type="button" key={b.id} className="qb-tile" onClick={() => setOpen(b)}><BadgeArt art={b.art} name={b.name} locked size="sm" /><span><b>{b.name}</b><small>{b.pct}% · {b.tasks.find(t => !t.done)?.label}</small></span></button>)}</div></div>}
    <div className="m-seg" role="tablist" aria-label="Badge set">{SETS.map(([id, label]) => <button key={id} type="button" role="tab" aria-selected={set === id} className={set === id ? 'active' : ''} data-testid={`badge-set-${id}`} onClick={() => setSet(id)}>{label}</button>)}</div>
    <div className="qb-grid">{shown.map(b => <button type="button" key={b.id} className={`qb-badge tier-${b.tier} ${b.earned ? 'is-earned' : ''}`} data-testid={`badge-${b.id}`} onClick={() => setOpen(b)}>
      <BadgeArt art={b.art} name={b.name} locked={!b.earned} /><b>{b.name}</b><small>{b.earned ? '✓ earned' : `${b.pct}%`}{d.rarity?.[b.id] != null ? ` · ${d.rarity[b.id]}% hold` : ''}</small>
      {!b.earned && <i className="qb-bar"><i style={{ transform: `scaleX(${b.pct / 100})` }} /></i>}</button>)}
      {!shown.length && <p className="m-dim">Nothing here yet — finish a quest above.</p>}</div>
    {open && <BadgeDetail b={open} rarity={d.rarity?.[open.id]} onClose={() => setOpen(null)} />}
  </section>;
}

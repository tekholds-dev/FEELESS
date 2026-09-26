import React, { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { Sparkles, Clock, Camera, Gift } from 'lucide-react';
import { shortAddress, formatUSD } from '../../lib/dexscreener';

const DAY = 86400;
const PRESETS = [
  { id: 'top10', label: '🏆 Top 10 holders', f: { top: 10 } },
  { id: 'diamond6', label: '💎 6-month diamond hands', f: { months: 6 } },
  { id: 'og', label: '🦴 OGs (12 mo+)', f: { months: 12 } },
  { id: 'top10-6mo', label: '👑 Top 10 held 6 mo+', f: { top: 10, months: 6 } },
  { id: 'minnows', label: '🐟 Every small holder ($1+)', f: { minUsd: 1, maxPct: 1 } },
  { id: 'loyal', label: '🔒 Held since snapshot', f: { snapshot: true } },
];
const MODES = [
  ['equal', 'Equal', 'Everyone gets the same.'],
  ['pro', 'Pro-rata', 'Split by how much they hold.'],
  ['sqrt', 'Square-root', 'Pro-rata but whales get less of an edge — fairest for communities.'],
  ['rank', 'Rank tiers', '#1 gets the most, sliding down by rank.'],
  ['loyalty', 'Loyalty', 'Holding × months held — rewards the patient.'],
];

export function AirdropStudio({ call, asset, holders, selected, onScheduled }) {
  const [f, setF] = useState({ top: '', months: 0, minUsd: '', maxPct: '', excludePools: true, excludeBlocked: true, excludeHq: true, snapshot: false, useSelection: false });
  const [since, setSince] = useState(null);
  const [loadingAges, setLoadingAges] = useState(false);
  const [snaps, setSnaps] = useState([]);
  const [snapId, setSnapId] = useState('');
  const [diamond, setDiamond] = useState(null);
  const [mode, setMode] = useState('sqrt');
  const [total, setTotal] = useState('');
  const [name, setName] = useState('');
  const [when, setWhen] = useState(() => new Date(Date.now() + DAY * 1000).toISOString().slice(0, 16));
  const set = (k, v) => setF(x => ({ ...x, [k]: v }));

  useEffect(() => { call('/admin/snapshots').then(d => { setSnaps(d.snaps || []); if (d.snaps?.[0]) setSnapId(d.snaps[0].id); }).catch(() => {}); }, [call]);
  const needAges = f.months > 0 || mode === 'loyalty';
  useEffect(() => {
    if (!needAges || since) return;
    setLoadingAges(true);
    call(`/admin/holders/ages?asset=${asset}`).then(d => setSince(d.since || {})).catch(e => toast.error(e.message)).finally(() => setLoadingAges(false));
  }, [needAges, since, call, asset]);
  useEffect(() => { setSince(null); }, [asset]);
  useEffect(() => {
    if (!f.snapshot || !snapId) { setDiamond(null); return; }
    call(`/admin/snapshots/${snapId}/diff`).then(d => setDiamond(new Set(d.diamondHands))).catch(e => toast.error(e.message));
  }, [f.snapshot, snapId, call]);

  const now = Date.now() / 1000;
  const monthsHeld = o => (since?.[o] ? (now - since[o]) / (30 * DAY) : 0);
  const recipients = useMemo(() => {
    let rows = holders.filter(r => !(f.excludePools && r.likelyPool) && !(f.excludeBlocked && r.blocked) && !(f.excludeHq && r.isAdmin));
    if (f.useSelection) rows = rows.filter(r => selected.includes(r.owner));
    if (f.minUsd) rows = rows.filter(r => (r.usd || 0) >= Number(f.minUsd));
    if (f.maxPct) rows = rows.filter(r => r.pct <= Number(f.maxPct));
    if (f.months > 0) rows = rows.filter(r => monthsHeld(r.owner) >= f.months);
    if (f.snapshot && diamond) rows = rows.filter(r => diamond.has(r.owner));
    if (Number(f.top) > 0) rows = rows.slice(0, Number(f.top));
    const n = rows.length; const T = Number(total) || 0;
    const w = rows.map((r, i) => mode === 'equal' ? 1 : mode === 'pro' ? r.amount : mode === 'sqrt' ? Math.sqrt(r.amount) : mode === 'rank' ? n - i : r.amount * Math.max(0.25, monthsHeld(r.owner)));
    const W = w.reduce((a, b) => a + b, 0) || 1;
    return rows.map((r, i) => ({ ...r, months: monthsHeld(r.owner), give: mode === 'equal' ? T / Math.max(1, n) : T * (w[i] / W) }));
  }, [holders, f, selected, since, diamond, mode, total]); // eslint-disable-line react-hooks/exhaustive-deps

  const applyPreset = p => { setF(x => ({ ...x, top: '', months: 0, minUsd: '', maxPct: '', snapshot: false, useSelection: false, ...p.f })); if (!name) setName(p.label.replace(/^\S+\s/, '')); };
  const schedule = async () => {
    if (!recipients.length || !(Number(total) > 0) || !name.trim()) { toast.error('Pick recipients, a name and a total.'); return; }
    try { await call('/admin/airdrops', { method: 'POST', body: JSON.stringify({ name, asset, note: `${MODES.find(m => m[0] === mode)[1]} split`, scheduledAt: new Date(when).getTime() / 1000, recipients: recipients.map(r => ({ address: r.owner, amount: Number(r.give.toFixed(6)) })) }) }); toast.success(`🪂 ${name} scheduled for ${recipients.length} wallets.`); onScheduled?.(); }
    catch (e) { toast.error(e.message); }
  };
  const gives = recipients.map(r => r.give);
  return <section className="cc-panel cc-studio" data-testid="airdrop-studio">
    <div className="cc-presets">{PRESETS.map(p => <button key={p.id} type="button" onClick={() => applyPreset(p)}>{p.label}</button>)}{selected.length > 0 && <button type="button" onClick={() => setF(x => ({ ...x, useSelection: true }))}>✅ My selection ({selected.length})</button>}</div>
    <div className="cc-studio-grid">
      <div className="cc-block"><h4><Sparkles size={12} /> Who</h4>
        <label>Top N holders<input type="number" min="0" placeholder="all" value={f.top} onChange={e => set('top', e.target.value)} /></label>
        <label><Clock size={12} /> Held at least<select value={f.months} onChange={e => set('months', Number(e.target.value))}>{[0, 1, 3, 6, 9, 12, 24].map(m => <option key={m} value={m}>{m ? `${m} month${m > 1 ? 's' : ''}` : 'any time'}</option>)}</select></label>
        <label>Min value (USD)<input type="number" min="0" placeholder="0" value={f.minUsd} onChange={e => set('minUsd', e.target.value)} /></label>
        <label>Max share of supply %<input type="number" min="0" step="any" placeholder="no cap" value={f.maxPct} onChange={e => set('maxPct', e.target.value)} /></label>
        <label className="cc-check"><input type="checkbox" checked={f.snapshot} onChange={e => set('snapshot', e.target.checked)} /><Camera size={12} />Still holding since snapshot</label>
        {f.snapshot && <select value={snapId} onChange={e => setSnapId(e.target.value)}>{!snaps.length && <option value="">No snapshots yet</option>}{snaps.map(s => <option key={s.id} value={s.id}>{s.label || s.asset.toUpperCase()} · {new Date(s.at * 1000).toLocaleDateString()} · {s.holders}</option>)}</select>}
        <label className="cc-check"><input type="checkbox" checked={f.excludePools} onChange={e => set('excludePools', e.target.checked)} />Skip pools / bonding curve</label>
        <label className="cc-check"><input type="checkbox" checked={f.excludeBlocked} onChange={e => set('excludeBlocked', e.target.checked)} />Skip blocklisted snipers/bundlers</label>
        <label className="cc-check"><input type="checkbox" checked={f.excludeHq} onChange={e => set('excludeHq', e.target.checked)} />Skip HQ wallet</label>
        {f.useSelection && <label className="cc-check"><input type="checkbox" checked onChange={() => set('useSelection', false)} />Only my selected wallets</label>}
        {loadingAges && <small className="cc-empty">Reading each holder's first on-chain activity…</small>}
      </div>
      <div className="cc-block"><h4><Gift size={12} /> How much</h4>
        <label>Total to drop ({asset.toUpperCase()})<input type="number" min="0" step="any" placeholder="e.g. 1000000" value={total} onChange={e => setTotal(e.target.value)} /></label>
        <div className="cc-modes">{MODES.map(([id, l, d]) => <button key={id} type="button" className={mode === id ? 'active' : ''} onClick={() => setMode(id)} title={d}><b>{l}</b><small>{d}</small></button>)}</div>
        <label>Name<input placeholder="e.g. Diamond Hands S1" value={name} onChange={e => setName(e.target.value)} /></label>
        <label>Send on<input type="datetime-local" value={when} onChange={e => setWhen(e.target.value)} /></label>
      </div>
      <div className="cc-block cc-preview"><h4>Preview</h4>
        <div className="cc-kpis"><span><small>Wallets</small><b>{recipients.length}</b></span><span><small>Biggest</small><b>{gives.length ? Math.max(...gives).toLocaleString(undefined, { maximumFractionDigits: 2 }) : '—'}</b></span><span><small>Smallest</small><b>{gives.length ? Math.min(...gives).toLocaleString(undefined, { maximumFractionDigits: 2 }) : '—'}</b></span><span><small>Value @ now</small><b>{recipients[0]?.usd != null && recipients[0]?.amount ? formatUSD((Number(total) || 0) * (recipients[0].usd / recipients[0].amount)) : '—'}</b></span></div>
        <div className="cc-prev-list">{recipients.slice(0, 60).map((r, i) => <div key={r.owner}><span>{i + 1}</span><code>{shortAddress(r.owner)}</code><small>{r.months ? `${r.months.toFixed(1)} mo` : ''}</small><b>{r.give.toLocaleString(undefined, { maximumFractionDigits: 2 })}</b></div>)}{recipients.length > 60 && <small className="cc-empty">+{recipients.length - 60} more</small>}</div>
        <button type="button" className="btn-primary" disabled={!recipients.length} onClick={schedule}>🪂 Schedule for {recipients.length} wallets</button>
      </div>
    </div>
  </section>;
}

export function Snapshots({ call, asset }) {
  const [snaps, setSnaps] = useState([]);
  const [diff, setDiff] = useState(null);
  const [label, setLabel] = useState('');
  const load = () => call('/admin/snapshots').then(d => setSnaps(d.snaps || [])).catch(() => {});
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const take = async () => { try { const r = await call(`/admin/snapshots?asset=${asset}&label=${encodeURIComponent(label)}`, { method: 'POST' }); toast.success(`Snapshot saved — ${r.holders} holders.`); setLabel(''); load(); } catch (e) { toast.error(e.message); } };
  return <section className="cc-panel">
    <p className="cc-note">A snapshot freezes every holder and balance right now. Compare later to see who's new, who left, and who never sold — then airdrop the diamond hands.</p>
    <div className="cc-toolbar"><input placeholder="Label (e.g. Pre-listing)" value={label} onChange={e => setLabel(e.target.value)} /><button type="button" className="btn-primary" onClick={take}><Camera size={13} />Snapshot {asset.toUpperCase()} now</button></div>
    {snaps.map(s => <div key={s.id} className="cc-drop"><div className="cc-drop-top"><b>📸 {s.label || s.asset.toUpperCase()}</b><em>{s.holders} holders</em><small>{new Date(s.at * 1000).toLocaleString()} · price {s.price ? `$${Number(s.price).toPrecision(4)}` : '—'}</small></div>
      <div className="cc-drop-actions"><button type="button" onClick={() => call(`/admin/snapshots/${s.id}/diff`).then(setDiff).catch(e => toast.error(e.message))}>Compare with now</button></div></div>)}
    {diff && <div className="cc-block"><h4>Since {diff.snap.label || 'snapshot'}</h4>
      <div className="cc-kpis cc-kpis-5">{Object.entries(diff.counts).map(([k, v]) => <span key={k} className={`d-${k}`}><small>{k}</small><b>{v}</b></span>)}</div>
      <div className="cc-prev-list">{diff.rows.slice(0, 80).map(r => <div key={r.owner} className={`d-${r.kind}`}><span>{r.kind}</span><code>{shortAddress(r.owner)}</code><small>{r.then.toLocaleString(undefined, { maximumFractionDigits: 0 })} → {r.now.toLocaleString(undefined, { maximumFractionDigits: 0 })}</small><b>{r.delta >= 0 ? '+' : ''}{r.delta.toLocaleString(undefined, { maximumFractionDigits: 0 })}</b></div>)}</div></div>}
  </section>;
}

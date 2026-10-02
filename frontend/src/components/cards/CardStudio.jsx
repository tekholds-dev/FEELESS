import React, { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl, errorText } from '../../lib/api';
import { CROP, uploadCropped } from '../../lib/cropImage';
import { MetaCard, CARD_DESIGNS, AuraPicker } from './MetaCard';

// HQ › Badges › Cards: every badge + season drop as a card. Pick one → edit front and back live
// (drag the preview to turn it, click to flip). Money rules stay in Reserve pool / Badge pools.
const KINDS = [['all', 'All'], ['badge', 'Badges'], ['season', 'Season'], ['weekly', 'Weekly drops']];
const RARITIES = ['common', 'rare', 'epic', 'legendary', 'mythic'];
const FIELDS = ['title', 'subtitle', 'glyph', 'lore', 'design', 'rarity', 'motion', 'aura', 'accent', 'accent2', 'art'];

export function CardStudio({ call }) {
  const [cards, setCards] = useState(null);
  const [kind, setKind] = useState('all');
  const [q, setQ] = useState('');
  const [pick, setPick] = useState(null);
  const [draft, setDraft] = useState(null);
  const [flipped, setFlipped] = useState(false);
  const [busy, setBusy] = useState('');
  const load = () => fetch(apiUrl('/api/reputation/cards')).then(r => r.json()).then(d => setCards(d.cards || [])).catch(() => setCards([]));
  useEffect(() => { load(); }, []);
  const list = useMemo(() => (cards || []).filter(c => (kind === 'all' || c.kind === kind) && (!q || `${c.title} ${c.subtitle}`.toLowerCase().includes(q.toLowerCase()))), [cards, kind, q]);
  const open = c => { setPick(c.key); setDraft(Object.fromEntries(FIELDS.map(k => [k, c[k] ?? '']))); setFlipped(false); };
  const base = cards?.find(c => c.key === pick);
  const live = base && draft ? { ...base, ...draft } : null;
  const set = (k, v) => setDraft(d => ({ ...d, [k]: v }));
  const dirty = base && draft && FIELDS.some(k => String(base[k] ?? '') !== String(draft[k] ?? ''));
  const art = async file => { if (!file) return; setBusy('Uploading…'); try { const u = await uploadCropped(file, CROP.badge, 768); if (u) set('art', u); } catch (e) { toast.error(e.message); } finally { setBusy(''); } };
  const save = async () => {
    setBusy('Saving…');
    try { const c = await call(`/admin/cards/${encodeURIComponent(pick).replace(/%3A/g, ':')}`, { method: 'PUT', body: JSON.stringify(draft) }); setCards(cs => cs.map(x => (x.key === pick ? { ...x, ...c } : x))); toast.success('Card saved — live on every profile.'); }
    catch (e) { toast.error(errorText(e)); } finally { setBusy(''); }
  };
  if (!cards) return <p className="cc-empty">Shuffling the deck…</p>;
  return <div className="card-studio" data-testid="card-studio">
    <div className="m-row cs-bar"><div className="m-seg">{KINDS.map(([k, l]) => <button key={k} type="button" className={kind === k ? 'active' : ''} onClick={() => setKind(k)}>{l} {k === 'all' ? cards.length : cards.filter(c => c.kind === k).length}</button>)}</div>
      <input className="m-input" style={{ maxWidth: 240 }} placeholder="Find a card…" value={q} onChange={e => setQ(e.target.value)} aria-label="Find a card" /></div>
    <div className={`cs-body ${live ? 'has-pick' : ''}`}>
      <div className="cs-grid m-scroll">{list.map(c => <button key={c.key} type="button" className={`mc-pick ${pick === c.key ? 'active' : ''}`} onClick={() => open(c)} title={c.title}>
        <MetaCard card={pick === c.key && live ? live : c} size="sm" /></button>)}
        {!list.length && <p className="m-dim">No cards match.</p>}</div>
      {live && <div className="cs-editor m-card is-hot m-pop">
        <div className="cs-preview"><MetaCard card={live} size="lg" interactive flipped={flipped} onFlip={setFlipped} />
          <div className="m-row"><button type="button" className="m-btn" onClick={() => setFlipped(f => !f)}>{flipped ? '↺ Show front' : '↻ Show back'}</button><small className="m-dim">drag to turn</small></div></div>
        <div className="cs-form m-stack">
          <div className="m-label">{live.kind === 'badge' ? 'BADGE CARD' : live.kind === 'season' ? 'SEASON CARD' : 'WEEKLY DROP'} <em>{live.holders} held · {pick}</em></div>
          <div className="m-grid"><label className="m-field"><span>Title</span><input className="m-input" maxLength={40} value={draft.title} onChange={e => set('title', e.target.value)} /></label>
            <label className="m-field"><span>Subtitle</span><input className="m-input" maxLength={60} value={draft.subtitle} onChange={e => set('subtitle', e.target.value)} /></label></div>
          <div className="m-field"><span>Design</span><div className="m-seg">{CARD_DESIGNS.map(([k, l]) => <button key={k} type="button" className={draft.design === k ? 'active' : ''} onClick={() => set('design', k)}>{l}</button>)}</div></div>
          <div className="m-field"><span>Motion</span><div className="m-seg">{[['still', '◻ Still'], ['alive', '✦ Alive — floats, foil sweeps, crest glows']].map(([k, l]) => <button key={k} type="button" className={(draft.motion || 'still') === k ? 'active' : ''} onClick={() => set('motion', k)}>{l}</button>)}</div></div>
          <div className="m-field"><span>Aura · live effect outside the card</span><AuraPicker value={draft.aura} onChange={v => set('aura', v)} /></div>
          <div className="m-field"><span>Rarity (crest + frame)</span><div className="m-seg">{RARITIES.map(r => <button key={r} type="button" className={draft.rarity === r ? 'active' : ''} onClick={() => set('rarity', r)}>{r}</button>)}</div></div>
          <div className="m-row"><label className="m-field"><span>Glyph</span><input className="m-input" style={{ width: 70, textAlign: 'center' }} maxLength={8} value={draft.glyph} onChange={e => set('glyph', e.target.value)} /></label>
            <label className="m-field"><span>Colour 1</span><input type="color" className="cs-color" value={draft.accent || '#19f58f'} onChange={e => set('accent', e.target.value)} /></label>
            <label className="m-field"><span>Colour 2</span><input type="color" className="cs-color" value={draft.accent2 || '#f5c451'} onChange={e => set('accent2', e.target.value)} /></label>
            <label className="m-btn"><input type="file" hidden accept="image/png,image/jpeg,image/webp,image/gif" onChange={e => art(e.target.files?.[0])} />🖼 {draft.art ? 'Change art' : 'Add art'}</label>
            {draft.art && <button type="button" className="m-btn danger" onClick={() => set('art', '')}>Remove art</button>}</div>
          <label className="m-field"><span>Lore (back of the card) · {(draft.lore || '').length}/600</span><textarea className="m-input" rows={4} maxLength={600} value={draft.lore} onChange={e => { set('lore', e.target.value); setFlipped(true); }} placeholder="The story holders read when they flip it." /></label>
          <CardRewards call={call} card={live} onSaved={load} />
          <div className="m-row"><button type="button" className="m-btn primary" disabled={!dirty || !!busy || (draft.title || '').trim().length < 2} onClick={save} data-testid="card-save">{busy || (dirty ? 'Save card' : 'Saved')}</button>
            {dirty && <button type="button" className="m-btn" onClick={() => open(base)}>Undo changes</button>}</div>
        </div></div>}
    </div>
  </div>;
}

// What a card earns, edited on the card: its % of each badge pool's pot and/or fixed SOL each per holder.
// Season cards earn by tier from pools tied to that season (and from the season reserve, set in 💰 Reserve pool).
const TIERS = [['Legend', '👑'], ['Diamond', '💎'], ['Gold', '🥇'], ['Silver', '🥈'], ['Bronze', '🥉']];
function CardRewards({ call, card, onSaved }) {
  const [pools, setPools] = useState(null);
  const [v, setV] = useState({});
  const [busy, setBusy] = useState(false);
  const loadPools = () => call('/admin/badge-pools').then(d => setPools(d.pools || [])).catch(() => setPools([]));
  useEffect(() => { loadPools(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const sid = card.kind === 'season' ? card.key.split(':')[1] : null;
  const keys = card.kind === 'badge' ? [[card.key, card.title]] : sid ? TIERS.map(([t, i]) => [`tier:${t}`, `${i} ${t}`]) : [];
  const mine = (pools || []).filter(p => card.kind === 'badge' || p.seasonId === sid);
  useEffect(() => {
    const s = {}; mine.forEach(p => keys.forEach(([k]) => { s[`${p.id}|${k}`] = p.weights?.[k] != null ? String(p.weights[k]) : ''; s[`${p.id}|${k}|sol`] = p.fixed?.[k] != null ? String(p.fixed[k]) : ''; })); setV(s);
  }, [pools, card.key]); // eslint-disable-line react-hooks/exhaustive-deps
  const save = async () => {
    setBusy(true);
    try {
      for (const p of mine) {
        const weights = { ...(p.weights || {}) }; const fixed = { ...(p.fixed || {}) }; let changed = false;
        keys.forEach(([k]) => { const w = Number(v[`${p.id}|${k}`]) || 0; const f = Number(v[`${p.id}|${k}|sol`]) || 0;
          if ((Number(weights[k]) || 0) !== w || (Number(fixed[k]) || 0) !== f) { weights[k] = w; fixed[k] = f; changed = true; } });
        if (changed) await call('/admin/badge-pools', { method: 'POST', body: JSON.stringify({ id: p.id, name: p.name, wallet: p.wallet, pct: p.pct, seasonId: p.seasonId || '', mode: p.mode || 'pct', weights, fixed }) });
      }
      toast.success('Rewards saved — the back of the card updates on the next refresh.'); loadPools(); onSaved?.();
    } catch (e) { toast.error(errorText(e)); } finally { setBusy(false); }
  };
  if (card.kind === 'weekly') return <div className="m-note"><b>Money on the back</b>Weekly drops are flex only. Season cards and badges earn.</div>;
  return <div className="m-card m-stack cr-box" data-testid="card-rewards"><div className="m-label">WHAT THIS CARD EARNS <em>{card.earnedEach || 0} SOL per card paid so far</em></div>
    {pools == null ? <p className="m-dim">Loading pools…</p> : !mine.length ? <p className="m-dim">{sid ? 'No badge pool is tied to this season yet.' : 'No badge pools yet.'} Create one in Money › Reserve & badge pools.</p>
      : mine.map(p => <div key={p.id} className="m-stack"><span className="m-dim">{p.name} · pot = {p.pct}% of {p.wallet.slice(0, 4)}…</span>
        {keys.map(([k, l]) => <div key={k} className="m-row">{keys.length > 1 && <span className="cr-key">{l}</span>}
          <label className="m-field"><span>% of pot</span><input className="m-input" style={{ width: 90 }} inputMode="decimal" placeholder="0" value={v[`${p.id}|${k}`] ?? ''} onChange={e => setV(x => ({ ...x, [`${p.id}|${k}`]: e.target.value.replace(/[^0-9.]/g, '') }))} /></label>
          <label className="m-field"><span>+ SOL each</span><input className="m-input" style={{ width: 90 }} inputMode="decimal" placeholder="0" value={v[`${p.id}|${k}|sol`] ?? ''} onChange={e => setV(x => ({ ...x, [`${p.id}|${k}|sol`]: e.target.value.replace(/[^0-9.]/g, '') }))} /></label></div>)}</div>)}
    {mine.length > 0 && <button type="button" className="m-btn" disabled={busy} onClick={save}>{busy ? 'Saving…' : 'Save rewards'}</button>}
    {sid && <small className="m-dim">Season reserve share: set the reserve wallet and % in Money › Reserve & badge pools (split by tier weight).</small>}
  </div>;
}

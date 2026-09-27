import { CROP } from '../lib/cropImage';
import React, { useRef, useState } from 'react';
import { toast } from 'sonner';
import { ImagePlus, Sparkles } from 'lucide-react';
import { uploadImage } from '../lib/adminCall';

export const BG_FX = [['money', '💸 Money rain'], ['fire', '🔥 Embers'], ['snow', '❄️ Snow'], ['leaves', '🍂 Falling leaves'], ['stars', '✨ Starfield'], ['none', 'None']];

// ---- Procedural lore + banner art: every "Generate" is a fresh, on-brand season pitch ----------
const pick = a => a[Math.floor(Math.random() * a.length)];
const LORE = {
  names: ['Degen Uprising', 'Diamond Winter', 'The Great Unrug', 'Moon Protocol', 'Sniper Purge', 'Green Candle Summer', 'Trench Kings', 'Liquidity Wars', 'Neon Genesis', 'The Clean Pump'],
  hooks: ['The trenches are louder than ever', 'Rugs got caught, snipers got named', 'Holders outlasted the paper hands', 'The chain remembers everything', 'Only the trustworthy climb'],
  quests: ['call it early and call it right', 'hold through the chop', 'hunt snipers before they hunt you', 'flag every bundle', 'stack streaks every day'],
  prizes: ['Legend ring + animated profile crown for the top 10', 'Season badge in gold for everyone who reaches Gold', 'Top 3 get a custom FeeCat skin', 'Diamond tier unlocks a permanent profile aura'],
  weeks: [['Opening Bell', '🔔'], ['Rug Hunter', '🎯'], ['Diamond Grip', '💎'], ['Sharp Caller', '📣'], ['Whale Watch', '🐋'], ['Final Boss', '👑'], ['Clean Hands', '🧼'], ['Green Wall', '🟩']],
};
export function generateLore() {
  const name = pick(LORE.names);
  const weeks = {};
  [...LORE.weeks].sort(() => Math.random() - 0.5).slice(0, 5).forEach(([n, g], i) => { weeks[String(i + 1)] = { name: n, glyph: g, story: `Week ${i + 1}: ${pick(LORE.quests)}.` }; });
  return { name, theme: `${pick(LORE.hooks)}. This season you ${pick(LORE.quests)} — and ${pick(LORE.quests)}.`, prize: pick(LORE.prizes), weeks };
}
export async function generateBannerFile(name, c1, c2) {
  const c = document.createElement('canvas'); c.width = 1600; c.height = 520; const g = c.getContext('2d');
  const bg = g.createLinearGradient(0, 0, 1600, 520); bg.addColorStop(0, '#05070a'); bg.addColorStop(0.55, c1 + '55'); bg.addColorStop(1, c2 + '66'); g.fillStyle = bg; g.fillRect(0, 0, 1600, 520);
  for (let i = 0; i < 70; i++) { g.fillStyle = i % 2 ? c1 + '33' : c2 + '33'; g.beginPath(); g.arc(Math.random() * 1600, Math.random() * 520, 4 + Math.random() * 60, 0, Math.PI * 2); g.fill(); }
  g.strokeStyle = c1 + 'aa'; g.lineWidth = 2; for (let i = 0; i < 14; i++) { g.beginPath(); g.moveTo(0, 60 + i * 34); g.bezierCurveTo(500, Math.random() * 520, 1100, Math.random() * 520, 1600, 60 + i * 30); g.stroke(); }
  g.font = 'italic 900 150px Inter, system-ui, sans-serif'; g.textAlign = 'center'; g.fillStyle = '#ffffff18'; g.fillText(name.toUpperCase(), 800, 320);
  const blob = await new Promise(r => c.toBlob(r, 'image/webp', 0.9));
  return new File([blob], 'banner.webp', { type: 'image/webp' });
}

function ImageDrop({ label, value, onChange, wide, shape }) {
  const input = useRef(null); const [busy, setBusy] = useState(false);
  const choose = async e => { const f = e.target.files?.[0]; e.target.value = ''; if (!f) return; setBusy(true); try { const url = await uploadImage(f, shape); if (url) onChange(url); } catch (err) { toast.error(err.message); } finally { setBusy(false); } };
  return <button type="button" className={`img-drop ${wide ? 'wide' : ''}`} onClick={() => input.current?.click()} style={value ? { backgroundImage: `url("${value}")` } : undefined} title={`Click to ${value ? 'replace' : 'add'} ${label}`}>
    <input ref={input} type="file" accept="image/png,image/jpeg,image/webp,image/gif" hidden onChange={choose} />
    {!value && <span><ImagePlus size={18} />{busy ? 'Uploading…' : label}</span>}{value && <em>{busy ? 'Uploading…' : 'Replace'}</em>}
    {value && <i role="button" tabIndex={0} aria-label="Remove image" onClick={e => { e.stopPropagation(); onChange(''); }}>×</i>}
  </button>;
}

// One editor for the Seasons tab and the command center. Saves through the signed admin session.
export function SeasonEditor({ season, call, onDone }) {
  const day = t => new Date(t * 1000 - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  const [f, setF] = useState({ ...season, start: day(season.start), end: day(season.end), bannerUrl: season.bannerUrl || '', badgeUrl: season.badgeUrl || '', bgFx: season.bgFx || 'none', accent2: season.accent2 || '#ff2bd6' });
  const weeksCount = Math.max(1, Math.ceil((season.end - season.start) / (7 * 86400)));
  const [weeks, setWeeks] = useState(() => Object.fromEntries(Array.from({ length: weeksCount }, (_, i) => [String(i + 1), { name: '', glyph: '', story: '', imageUrl: '', ...((season.weeks || {})[String(i + 1)] || {}) }])));
  const [busy, setBusy] = useState(false);
  const set = (k, v) => setF(x => ({ ...x, [k]: v }));
  const setW = (w, k, v) => setWeeks(x => ({ ...x, [w]: { ...x[w], [k]: v } }));
  const generate = async () => {
    setBusy(true);
    try {
      const l = generateLore();
      setF(x => ({ ...x, name: l.name, theme: l.theme, prize: l.prize }));
      setWeeks(x => Object.fromEntries(Object.entries(x).map(([k, v]) => [k, { ...v, ...(l.weeks[k] || {}) }])));
      set('bannerUrl', await uploadImage(await generateBannerFile(l.name, f.accent, f.accent2)));
      toast.success('Fresh lore + banner generated — tweak anything, then save.');
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const save = async () => {
    setBusy(true);
    try {
      const clean = Object.fromEntries(Object.entries(weeks).map(([k, v]) => [k, Object.fromEntries(Object.entries(v).filter(([, x]) => x))]).filter(([, v]) => Object.keys(v).length));
      await call(`/admin/seasons/${season.id}`, { method: 'PUT', body: JSON.stringify({ name: f.name, theme: f.theme, prize: f.prize, multiplier: Number(f.multiplier), accent: f.accent, accent2: f.accent2, bgFx: f.bgFx, bannerUrl: f.bannerUrl, badgeUrl: f.badgeUrl, start: Date.parse(f.start) / 1000, end: Date.parse(f.end) / 1000, weeks: clean }) });
      toast.success('Season updated.'); onDone(true);
    } catch (err) { toast.error(err.message); } finally { setBusy(false); }
  };
  const remove = async () => { if (!window.confirm(`Delete season "${season.name}"?`)) return; try { await call(`/admin/seasons/${season.id}`, { method: 'DELETE' }); toast.success('Season deleted.'); onDone(true); } catch (err) { toast.error(err.message); } };
  return <div className="season-editor" data-testid="season-editor">
    <header><h4>Edit season</h4><button type="button" className="btn-outline" disabled={busy} onClick={generate}><Sparkles size={14} />Generate lore + art</button></header>
    <ImageDrop wide shape={CROP.seasonBanner} label="Add banner / GIF" value={f.bannerUrl} onChange={v => set('bannerUrl', v)} />
    <div className="se-grid">
      <label>Name<input value={f.name} onChange={e => set('name', e.target.value)} /></label><label>Prize<input value={f.prize} onChange={e => set('prize', e.target.value)} /></label>
      <label className="se-wide">Story / lore<input value={f.theme} onChange={e => set('theme', e.target.value)} /></label>
      <label>Starts<input type="datetime-local" value={f.start} onChange={e => set('start', e.target.value)} /></label><label>Ends<input type="datetime-local" value={f.end} onChange={e => set('end', e.target.value)} /></label>
      <label>Multiplier<input type="number" step="0.5" min="0.5" max="5" value={f.multiplier} onChange={e => set('multiplier', e.target.value)} /></label>
      <label>Background effect<select value={f.bgFx} onChange={e => set('bgFx', e.target.value)}>{BG_FX.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></label>
      <label>Main color<input type="color" value={f.accent} onChange={e => set('accent', e.target.value)} /></label><label>Glow color<input type="color" value={f.accent2} onChange={e => set('accent2', e.target.value)} /></label>
      <div className="se-wide se-badge"><span>Season badge</span><ImageDrop shape={CROP.badge} label="Add badge / GIF" value={f.badgeUrl} onChange={v => set('badgeUrl', v)} /></div>
    </div>
    <h4>Weekly drops</h4>
    <div className="se-weeks">{Object.entries(weeks).map(([w, v]) => <div key={w} className="se-week"><ImageDrop shape={CROP.badge} label={`Week ${w}`} value={v.imageUrl} onChange={x => setW(w, 'imageUrl', x)} />
      <div><input placeholder={`Week ${w} badge name`} value={v.name} onChange={e => setW(w, 'name', e.target.value)} /><input placeholder="Emoji" maxLength={4} value={v.glyph} onChange={e => setW(w, 'glyph', e.target.value)} /><input placeholder="Story" value={v.story} onChange={e => setW(w, 'story', e.target.value)} /></div></div>)}</div>
    <div className="se-actions"><button type="button" className="btn-outline" onClick={remove}>Delete</button><button type="button" className="btn-outline" onClick={() => onDone(false)}>Cancel</button><button type="button" className="btn-primary" disabled={busy} onClick={save}>{busy ? 'Working…' : 'Save season'}</button></div>
  </div>;
}

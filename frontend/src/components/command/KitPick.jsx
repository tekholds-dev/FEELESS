import React, { useEffect, useState } from 'react';
import { Button } from '@heroui/react';
import { createPortal } from 'react-dom';
import '../../styles/features.css';
import '../../styles/kitGallery.css';

// 🧰 Which kits this agent reads first: up to 3 from Discover, or it chooses for each request. Discover is a big categorized gallery, each kit moving through its own site.
const KINDS = [['all', 'All proofs'], ['pow', 'PoW'], ['pop', 'PoP'], ['pob', 'PoB'], ['poc', 'PoC'], ['pos', 'PoStatic']];
export function KitPick({ cat, work, kind = 'all' }) {
  const [q, setQ] = useState(''); const [cat2, setCat2] = useState('All'); const [forKind, setForKind] = useState(kind); const [d, setD] = useState(null); const [open, setOpen] = useState(false); const [busy, setBusy] = useState(''); const [err, setErr] = useState(''); const [showNew, setShowNew] = useState(false);
  useEffect(() => { let on = true; Promise.resolve().then(() => work(cat.id, { op: 'kit_list' })).then(j => on && setD(j)).catch(() => {}); return () => { on = false; }; }, [cat.id, work]);
  if (!d?.kits?.length) return null;
  const save = async (picks, job, id = '') => { setBusy(id || job); setErr(''); try { setD(await work(cat.id, { op: 'kit_pick', text: picks.join(','), job })); } catch (x) { setErr(x.message); } setBusy(''); };
  const max = d.max || 3; const auto = d.mode === 'auto'; const fresh = d.kits.filter(k => k.found).length; const named = id => d.kits.find(k => k.id === id)?.name || id;
  const live = d.kits.filter(k => !k.found || showNew); const cats = ['All', ...new Set(live.map(k => k.cat).filter(Boolean))]; const shown = live.filter(k => (cat2 === 'All' || k.cat === cat2) && (forKind === 'all' || !k.kinds || k.kinds.includes(forKind)) && (!q.trim() || `${k.name} ${k.what}`.toLowerCase().includes(q.trim().toLowerCase())));
  const flip = id => save(!auto && d.picks.includes(id) ? d.picks.filter(x => x !== id) : [...(auto ? [] : d.picks), id], 'mine', id);
  return <div className="kit-row" role="group" aria-label="Kits it reads first" data-testid="kit-pick">
    <small className="kit-l">READS FIRST</small>
    {auto ? <span className="kit-chip is-auto" data-testid="kit-auto"><i aria-hidden="true" />Agent picks per request</span> : d.picks.map((id, i) => <span key={id} className="kit-chip" data-testid={`kit-on-${id}`}><b className="m-num">{i + 1}</b>{named(id)}</span>)}
    <Button size="sm" variant="secondary" className="kit-open" onPress={() => setOpen(true)} data-tip="See every kit moving, by kind. Choose up to 3, or let the agent choose for each request" data-testid="kit-discover">Discover</Button>
    {open ? createPortal(<div className="kgl-shade" onClick={e => e.target === e.currentTarget && setOpen(false)} data-testid="kit-shade"><section className="kgl" role="dialog" aria-modal="true" aria-label="Discover kits" data-testid="kit-panel">
      <header className="kgl-h"><span><b>Discover kits</b><small className="m-num">{shown.length} kits · {auto ? 'Agent chooses' : `${d.picks.length} of ${max} picked`}</small></span><div className="m-seg kit-mode" role="radiogroup" aria-label="Who chooses the kits">
        <button type="button" role="radio" aria-checked={auto} className={auto ? 'active' : ''} disabled={!!busy} onClick={() => save(d.picks, 'auto')} data-tip="It reads your request, picks what fits from these, and may use another free kit if it says which" data-testid="kit-mode-auto">Agent picks</button>
        <button type="button" role="radio" aria-checked={!auto} className={!auto ? 'active' : ''} disabled={!!busy} onClick={() => save(d.picks, 'mine')} data-tip="It reads your picks first, in this order" data-testid="kit-mode-mine">I pick</button></div>
        <button type="button" className="m-btn" onClick={() => setOpen(false)} aria-label="Close" data-tip="Close" data-testid="kit-close">✕</button></header>
      <div className="kgl-f"><input className="m-input" value={q} onChange={e => setQ(e.target.value)} placeholder="Search kits" aria-label="Search kits" data-testid="kit-search" /><span className="m-seg" role="group" aria-label="Kind of kit">{cats.map(c => <button key={c} type="button" className={cat2 === c ? 'active' : ''} aria-pressed={cat2 === c} onClick={() => setCat2(c)} data-testid={`kit-cat-${c}`}>{c}</button>)}</span><span className="m-seg" role="group" aria-label="For which proof">{KINDS.map(([k, l]) => <button key={k} type="button" className={forKind === k ? 'active' : ''} aria-pressed={forKind === k} onClick={() => setForKind(k)} data-testid={`kit-for-${k}`}>{l}</button>)}</span></div>
      <ul className="kgl-grid">{shown.map((k, i) => { const on = !auto && d.picks.includes(k.id); const full = !auto && !on && d.picks.length >= max;
        return <li key={k.id} style={{ '--i': Math.min(i, 12) }} className={`${on ? 'is-on' : ''}${k.private ? ' is-private' : ''}`}><span className="kgl-show" aria-hidden="true">{k.private ? <i>FEELESS</i> : <img src={`/kits/${k.id}.webp`} alt="" loading="lazy" onError={e => { e.currentTarget.style.display = 'none'; }} />}</span>
          <button type="button" role="checkbox" aria-checked={on} disabled={!!busy || full} onClick={() => flip(k.id)} data-tip={full ? `Up to ${max}. Remove one first` : on ? 'Remove it' : k.added ? 'Read it first' : 'Downloads its guide, then reads it first'} data-testid={`kit-pick-${k.id}`}><i className="kit-box" aria-hidden="true">{on ? d.picks.indexOf(k.id) + 1 : ''}</i><span><b>{k.name}{k.found ? <i className="kit-new">NEW</i> : null}</b><small>{k.what}</small></span><em className="m-num">{busy === k.id ? 'Getting…' : k.private ? 'FEELESS' : k.added ? `${k.vitals?.items || 0} listed` : 'Not added'}</em></button>
          {k.private ? null : <a href={k.site} target="_blank" rel="noopener noreferrer" aria-label={`Open ${k.name}'s site`} data-tip={`${k.license} · opens its site in a new tab`}>↗</a>}</li>; })}</ul>
      {fresh ? <button type="button" className="m-btn kit-more" aria-expanded={showNew} onClick={() => setShowNew(x => !x)} data-tip="Popular free kits found this week, with an AI guide on their own site. They only reach PoStatic builds" data-testid="kit-new">{showNew ? 'Hide new kits' : `${fresh} new to try`}</button> : null}
      {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}</section></div>, document.body) : null}
  </div>;
}

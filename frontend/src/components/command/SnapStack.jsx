import { agentAuthQuery } from '../../lib/chatSession';
import React, { useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { apiUrl } from '../../lib/api';
import '../../styles/snapStack.css';

// 📸 ONE snapshot viewer (owner 2026-11-03: "when I click a snapshot I want stacks of all info scraped, no same sites or bot check snapshots").
// Filed folders may still hold repeats from before the capture filter, so every view reads snapshots through cleanShots.
export function cleanShots(f, mint) {
  const walled = new Set([...((f?.evidenceMetrics || {})[mint]?.gaps || []), ...((f?.poiTrace || {})[mint]?.walled || [])]);
  const bySite = new Map();
  (f?.shots || []).filter(s => s.mint === mint && s.site && !walled.has(s.site)).forEach(s => { const had = bySite.get(s.site); if (!had || (s.at || 0) >= (had.at || 0)) bySite.set(s.site, s); });
  return [...bySite.values()].sort((a, b) => (a.at || 0) - (b.at || 0));
}
export const cleanFolderShots = f => (f?.coins || []).flatMap(c => cleanShots(f, c.mint));

const STACKS = [['Contract risk', /mint|freeze|authority|\blp\b|lock|rug|honeypot|risk|tax|score|creator|\bdev\b|renounc/i], ['Holders', /holder|top ?\d|concentr|bundle|sniper|insider|wallet/i],
  ['Market', /price|cap|mcap|fdv|volume|\bvol\b|liquid|pool/i], ['Activity', /\btx|txn|trade|buy|sell|age|call|mention|post/i], ['Other', /./]];
const shotSrc = (catId, f, file) => apiUrl(`/api/cats/${catId}/powshot/${String(f.id).replace(/[^a-z0-9]/gi, '').toLowerCase()}/${file}?${agentAuthQuery()}`);

export function SnapStack({ f, shot, catId, onClose, onPick }) {
  const coin = (f.coins || []).find(c => c.mint === shot.mint); const rail = useMemo(() => cleanShots(f, shot.mint), [f, shot.mint]);
  const facts = ((f.vitals || {})[shot.mint] || []).filter(x => x.site === shot.site || (x.sites || []).includes(shot.site));
  const stacks = STACKS.map(([name, re]) => [name, []]); facts.forEach(x => { stacks[STACKS.findIndex(([, re]) => re.test(x.label || ''))][1].push(x); });
  const at = rail.findIndex(s => s.file === shot.file);
  useEffect(() => { const k = e => { if (e.key === 'Escape') onClose(); else if (e.key === 'ArrowRight' && rail[at + 1]) onPick(rail[at + 1]); else if (e.key === 'ArrowLeft' && at > 0) onPick(rail[at - 1]); };
    window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [at, rail, onClose, onPick]);
  return createPortal(<div className="ss" role="dialog" aria-modal="true" aria-label={`${shot.site} snapshot`} onClick={e => { if (e.target === e.currentTarget) onClose(); }} data-testid="snap-stack">
    <div className="ss-panel m-glass">
      <header><span><b>{shot.site}</b><small>{coin ? `$${coin.sym} · ` : ''}{shot.at ? `${new Date(shot.at * 1000).toLocaleString()} · ` : ''}{facts.length} fact{facts.length === 1 ? '' : 's'} scraped</small></span>
        <button type="button" className="m-btn" onClick={onClose} aria-label="Close the snapshot" data-tip="Close (Esc)" data-testid="dsk-shot-big">✕</button></header>
      <div className="ss-body">
        <img key={shot.file} src={shotSrc(catId, f, shot.file)} alt={`${shot.site} snapshot`} />
        <div className="ss-stacks">{stacks.filter(([, rows]) => rows.length).map(([name, rows], i) => <section key={name} className="ss-stack" style={{ '--i': i }}><h4>{name}<i className="m-num">{rows.length}</i></h4>
          {rows.map((x, k) => <article key={`${x.label}${k}`} className={x.contradiction ? 'is-disputed' : x.verified ? 'is-verified' : ''} style={{ '--k': k }}><em>{x.label}</em><b className="m-num">{x.value}</b>
            <small>{x.contradiction ? 'Conflicting values' : x.verified ? 'Verified on the page' : 'Candidate'}{x.at ? ` · ${new Date(Number(x.at) * 1000).toLocaleTimeString()}` : ''}</small>{x.support ? <q>{x.support}</q> : null}</article>)}</section>)}
          {!facts.length ? <p className="ss-none">No facts were saved from this page.</p> : null}</div>
      </div>
      {rail.length > 1 ? <nav className="ss-rail" aria-label="Other sites for this coin">{rail.map(s => <button key={s.file} type="button" className={s.file === shot.file ? 'is-on' : ''} onClick={() => onPick(s)} aria-pressed={s.file === shot.file} data-tip={`Open ${s.site}`}><img src={shotSrc(catId, f, s.file)} alt="" loading="lazy" /><small>{s.site}</small></button>)}</nav> : null}
    </div></div>, document.body);
}

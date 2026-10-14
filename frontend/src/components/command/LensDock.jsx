// 🧭 AGENTS TAB DOCK (owner, 2026-10-13: "tabs at the bottom more usable · every Agents tab needs live visuals, no crazy reading"): the lens
// tabs sit on TOP of the lens (sticky), big icon + short word + a live badge, ← / → walk them; under it `LensVitals` = four live tubes for
// the open lens, every number from the payload the desk already holds (no new request). Reading stays in the panes for those who open them.
import React, { useEffect, useRef } from 'react';
import '../../styles/lensDock.css';

const clamp = v => Math.max(0, Math.min(1, Number(v) || 0));
const share = (a, b) => (b ? clamp(a / b) : 0);
// pure: the open lens → four tubes {k, label, val, fill 0–1, tone ok|bad|warn|ice}. Missing numbers read "—" with an empty tube.
export function lensVitals(lens, d, cnt = {}) {
  const o = d?.office || {}; const seat = o.seat || {}; const j = d?.judge || {}; const desk = d?.desk || {}; const road = d?.road || {};
  const rv = o.review || {}; const open = rv.open || {}; const counts = rv.counts || {}; const sum = x => Object.values(x || {}).reduce((a, b) => a + (Number(b) || 0), 0);
  const gens = o.generations || []; const pr = d?.proof?.card || {}; const pp = d?.proof?.paper || {}; const rg = d?.perf?.regime || {};
  const t = (k, label, val, fill, tone = 'ok') => ({ k, label, val: val == null || Number.isNaN(val) ? '—' : String(val), fill: val == null ? 0 : clamp(fill), tone });
  const held = seat.held ?? null; const want = seat.want || 4;
  switch (lens) {
    case 'live': return [t('ready', 'READY', cnt.ready ?? 0, share(cnt.ready || 0, want), cnt.ready ? 'ok' : 'warn'), t('cont', 'CONTENDING', cnt.contending ?? 0, share(cnt.contending || 0, 10), 'ice'),
      t('seats', 'SEATS', held == null ? null : `${held}/${want}`, share(held, want), held ? 'ok' : 'bad'), t('green', 'GREEN 5M', rg.green == null ? null : `${rg.green}%`, (rg.green || 0) / 100, rg.green != null && rg.green < 40 ? 'bad' : 'ok')];
    case 'review': return [t('open', 'TO REVIEW', sum(open), share(sum(open), Math.max(1, sum(counts))), sum(open) ? 'warn' : 'ok'), t('missed', 'MISSED', open.missed ?? 0, share(open.missed, Math.max(1, counts.missed)), 'bad'),
      t('entry', 'ENTRIES', open.entry ?? 0, share(open.entry, Math.max(1, counts.entry)), 'ice'), t('exit', 'EXITS', open.exit ?? 0, share(open.exit, Math.max(1, counts.exit)), 'ice')];
    case 'missed': return [t('missed', 'MISSED RUNS', counts.missed ?? 0, share(counts.missed, 50), 'bad'), t('waits', 'WAITS THAT RAN', j.missed ?? null, share(j.missed, 30), 'warn'),
      t('vetoes', 'VETOES', counts.vetoes ?? 0, share(counts.vetoes, 50), 'ice'), t('ctl', 'WAIT COINS · TYPICAL', d?.control?.n ? `${d.control.med > 0 ? '+' : ''}${d.control.med}%` : null, 0.5 + clamp((d?.control?.med || 0) / 20) / 2, (d?.control?.med || 0) >= 0 ? 'ok' : 'bad')];
    case 'board': { const pf = o.performance || {}; const ex = o.execution || {};
      return [t('ms', 'DESK MS', pf.deskMs != null ? Math.round(pf.deskMs) : null, share(pf.deskMs, 3000), (pf.deskMs || 0) > 2000 ? 'bad' : 'ok'), t('exec', 'EXECUTION', ex.health || null, ex.health === 'OK' ? 1 : ex.health ? 0.5 : 0, ex.health === 'OK' ? 'ok' : 'warn'),
        t('fills', 'FILLS 15M', ex.fills ?? null, share(ex.fills, Math.max(1, ex.sends || 1)), 'ice'), t('slip', 'FILL VS MID', ex.deltaMed != null ? `${ex.deltaMed}%` : null, share(ex.deltaMed, 10), (ex.deltaMed || 0) > 3 ? 'bad' : 'ok')]; }
    case 'limits': return [t('seats', 'SEATS HELD', held == null ? null : `${held}/${want}`, share(held, want), held ? 'ok' : 'bad'), t('cash', 'FREE CASH', seat.freeUsd != null ? `$${Number(seat.freeUsd).toFixed(2)}` : null, share(seat.freeUsd, Math.max(1, o.mission?.value || 1)), 'ice'),
      t('moves', 'FILLS LEFT', seat.movesLeft ?? null, share(seat.movesLeft, 36), 'ok'), t('empty', 'EMPTY FOR', seat.emptyFor != null ? `${Math.round(seat.emptyFor)}s` : null, share(seat.emptyFor, 300), (seat.emptyFor || 0) > (seat.target || 30) ? 'bad' : 'ok')];
    case 'learn': return [t('judge', 'JUDGE W–L', j.wins != null ? `${j.wins}–${j.losses}` : null, share(j.wins, (j.wins || 0) + (j.losses || 0)), 'ok'), t('paper', 'PAPER W–L', pp.n ? `${pp.w}–${pp.l}` : null, share(pp.w, pp.n), 'ice'),
      t('card', 'CARD W–L', pr.n ? `${pr.w}–${pr.l}` : null, share(pr.w, pr.n), (pr.w || 0) >= (pr.l || 0) ? 'ok' : 'bad'), t('ideas', 'IDEAS WAITING', (d?.ideas || []).filter(i => i.status === 'new').length, share((d?.ideas || []).filter(i => i.status === 'new').length, 5), 'warn')];
    case 'life': { const act = gens.filter(g => g.status === 'ACTIVE').length; const rep = gens.reduce((n, g) => n + (g.lineage || []).length, 0);
      return [t('active', 'ACTIVE', gens.length ? `${act}/${gens.length}` : null, share(act, gens.length), 'ok'), t('risk', 'ON PROBATION', (cnt.probation || []).length, share((cnt.probation || []).length, 4), (cnt.probation || []).length ? 'bad' : 'ok'),
        t('rep', 'REPLACED', rep, share(rep, 20), 'ice'), t('top', 'TOP GEN', gens.length ? Math.max(...gens.map(g => g.generation || 1)) : null, share(Math.max(0, ...gens.map(g => g.generation || 1)), 10), 'warn')]; }
    case 'ctl': return [t('x', 'PAPER ×', desk.x != null ? `${desk.x}×` : null, Math.log10(Math.max(1, desk.x || 1)), (desk.x || 0) >= 1 ? 'ok' : 'bad'), t('road', 'ROAD TO REAL', `${road.pct ?? 0}%`, (road.pct || 0) / 100, 'ice'),
      t('stake', 'STAKE', desk.stake != null ? `${desk.stake}%` : null, (desk.stake || 0) / 50, desk.heat === 'cold' ? 'warn' : 'ok'), t('trades', 'DESK TRADES', desk.trades ?? null, share(desk.trades, 50), 'ok')];
    default: return [];
  }
}

export function LensVitals({ lens, d, cnt }) {
  const v = lensVitals(lens, d, cnt); if (!v.length) return null;
  return <div className="lnd-vitals" data-testid="lens-vitals" key={lens}>{v.map((x, i) => <span key={x.k} className={`lnd-tube is-${x.tone}`} style={{ '--i': i }} data-testid={`lv-${x.k}`}>
    <small>{x.label}</small><b key={x.val}>{x.val}</b><i aria-hidden="true"><u style={{ transform: `scaleX(${x.fill})` }} /><s /></i></span>)}</div>;
}

// the dock: tabs = [key, label]; badge(k) → small text or null
export function LensDock({ tabs, lens, setLens, badge }) {
  const ref = useRef(null);
  useEffect(() => { const el = ref.current?.querySelector('[aria-selected="true"]'); if (el?.scrollIntoView && ref.current.scrollWidth > ref.current.clientWidth) el.scrollIntoView({ block: 'nearest', inline: 'center' }); }, [lens]);
  const key = e => { const i = tabs.findIndex(t => t[0] === lens); if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { e.preventDefault(); const n = tabs[(i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length][0]; setLens(n); ref.current?.querySelector(`[data-testid="lens-${n}"]`)?.focus(); } };
  return <div className="lnd" role="tablist" aria-label="Agent desk lens" ref={ref} onKeyDown={key}>{tabs.map(([k, l]) => { const ic = l.split(' ')[0]; const w = l.split(' ').slice(1).join(' '); const b = badge?.(k);
    return <button key={k} type="button" role="tab" aria-selected={lens === k} tabIndex={lens === k ? 0 : -1} className={lens === k ? 'active' : ''} onClick={() => setLens(k)} data-testid={`lens-${k}`}>
      <i aria-hidden="true">{ic}</i><span>{w}</span>{b ? <small>{b}</small> : null}</button>; })}<u className="lnd-glow" aria-hidden="true" /></div>;
}

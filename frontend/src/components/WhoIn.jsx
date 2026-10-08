import React, { useEffect, useState } from 'react';
import { sharedJson } from '../lib/sharedJson';
import '../styles/whoIn.css';

// 👥 WHO'S IN: the people inside one coin, from records that can be checked — its top holders tagged by FEELESS's own forensics
// (dev · sniper · bundled · pool · flagged) and the verified FEELESS traders in it (early-buyer rank, still in / out, result).
// Loads when you open the fold (the holder scan is not free). GET /coin/{mint}/whos-in.
const TAGS = { dev: ['👤 dev', 'The coin\'s creator wallet'], sniper: ['🎯 sniper', 'Bought in the first slots of the launch'], bundled: ['📦 bundled', 'Bought in a bundle with other wallets'], pool: ['💧 pool', 'The liquidity pool / launch curve'], flagged: ['⛔ flagged', 'On the FEELESS blocklist'] };
export const tagInfo = t => TAGS[t] || [t, ''];
export const resultLine = r => (r.ret == null ? (r.in ? 'still in' : 'in & out') : `${r.in ? 'still in · ' : 'out · '}${r.ret >= 0 ? '+' : ''}${(r.ret * 100).toFixed(Math.abs(r.ret) >= 1 ? 0 : 1)}%`);

export function WhoIn({ mint }) {
  const [open, setOpen] = useState(false); const [d, setD] = useState(null); const [err, setErr] = useState(false);
  useEffect(() => { setOpen(false); setD(null); setErr(false); }, [mint]);
  useEffect(() => { let alive = true; if (!open || !mint || d) return undefined; sharedJson(`/api/reputation/coin/${mint}/whos-in`, { maxAge: 45000 }).then(x => alive && setD(x)).catch(() => alive && setErr(true)); return () => { alive = false; }; }, [open, mint, d]);
  if (!mint) return null;
  const v = d?.verdict; const tr = d?.traders || []; const hs = d?.holders || [];
  const max = Math.max(1, ...hs.map(h => h.pct || 0));
  return <details className="wi" data-testid="whos-in" onToggle={e => setOpen(e.currentTarget.open)}>
    <summary data-tip="Who is inside this coin: its biggest holders tagged by FEELESS's own forensics, and the verified FEELESS traders in it. Checked records only — no avatars, no guesses.">
      👥 Who&apos;s in{d ? ` · ${hs.length} top holders${v?.risky ? ` · ${v.risky} risky` : ''}${tr.length ? ` · ${tr.length} FEELESS trader${tr.length === 1 ? '' : 's'}` : ''}` : ''}</summary>
    {!d && !err && <small className="m-dim">Reading the holders…</small>}{err && <small className="m-dim">Could not read this coin's holders right now.</small>}
    {d && !d.scanned && !tr.length && <small className="m-dim">No holder scan for this coin yet — it fills in when the scan lands.</small>}
    {tr.length > 0 && <ul className="wi-tr" data-testid="whos-in-traders">{tr.map((r, i) => <li key={r.address} style={{ '--i': i }}>
      <b className="wi-rank" data-tip="Early-buyer rank among verified FEELESS traders in this coin">#{r.rank}</b>
      <a href={`/terminal/profile/${r.address}`} className="wi-name">{(r.badges || []).map(b => <img key={b.id} className="wi-badge" src={`${b.art}.jpg`} alt="" loading="lazy" onError={e => { e.currentTarget.style.display = 'none'; }} />)}{r.name}</a>
      <em className={r.ret == null ? '' : r.ret >= 0 ? 'm-pos' : 'm-neg'}>{resultLine(r)}</em></li>)}</ul>}
    {hs.length > 0 && <ul className="wi-hs" data-testid="whos-in-holders">{hs.map((h, i) => <li key={h.address} style={{ '--i': i }}>
      <a href={`/terminal/profile/${h.address}`} className="wi-name">{h.name}</a>
      <span className="wi-bar" aria-hidden="true"><i style={{ transform: `scaleX(${Math.max(0.03, (h.pct || 0) / max)})` }} /></span><em className="m-num">{h.pct == null ? '—' : `${h.pct}%`}</em>
      <span className="wi-tags">{h.tags.map(t => <i key={t} className={`wi-tag t-${t}`} data-tip={tagInfo(t)[1]}>{tagInfo(t)[0]}</i>)}</span></li>)}</ul>}
  </details>;
}

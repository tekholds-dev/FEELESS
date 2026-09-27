import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiUrl } from '../../lib/api';
import { CopyBtn } from '../CopyBtn';

const short = a => `${a.slice(0, 4)}…${a.slice(-4)}`;

// Render the report as a 1200×675 image card (X/Twitter size) and download it.
function downloadCard(r) {
  const c = document.createElement('canvas'); c.width = 1200; c.height = 675; const g = c.getContext('2d');
  const bg = g.createLinearGradient(0, 0, 1200, 675); bg.addColorStop(0, '#05070a'); bg.addColorStop(1, '#1a0710'); g.fillStyle = bg; g.fillRect(0, 0, 1200, 675);
  g.fillStyle = '#ff2d55'; g.font = 'italic 900 68px Inter, sans-serif'; g.fillText('RUG REPORT', 60, 110);
  g.fillStyle = '#9fb3a8'; g.font = '600 26px Inter, sans-serif'; g.fillText(`FEELESS · last ${r.days} days · on-chain evidence only`, 60, 155);
  const t = r.totals; [['Snipers/bundlers caught', t.caught], ['Blocklisted', t.blocklisted], ['Repeat funders', t.funders], ['Broken Shields', t.brokenShields]].forEach(([l, v], i) => {
    const x = 60 + i * 275; g.fillStyle = '#ffffff'; g.font = '800 76px JetBrains Mono, monospace'; g.fillText(String(v), x, 300); g.fillStyle = '#9fb3a8'; g.font = '600 20px Inter, sans-serif'; g.fillText(l, x, 335);
  });
  g.fillStyle = '#eafff3'; g.font = '600 24px JetBrains Mono, monospace';
  r.caught.slice(0, 5).forEach((c2, i) => g.fillText(`${short(c2.wallet)}  ${c2.roles.join('+')} on ${c2.launches} launches${c2.blocked ? '  ⛔' : ''}`, 60, 420 + i * 40));
  g.fillStyle = '#00ffa3'; g.font = '800 28px Inter, sans-serif'; g.fillText('feeless — the chain remembers.', 60, 640);
  const a = document.createElement('a'); a.download = `feeless-rug-report-${new Date().toISOString().slice(0, 10)}.png`; a.href = c.toDataURL('image/png'); a.click();
}

export function RugReport() {
  const [r, setR] = useState(null);
  useEffect(() => { fetch(apiUrl('/api/reputation/rug-report?days=7')).then(x => x.json()).then(setR).catch(() => {}); }, []);
  if (!r) return null;
  const t = r.totals;
  return <section className="rug-report" data-testid="rug-report">
    <header><div><h3>Rug Report</h3><small>Last 7 days · every entry is on-chain evidence</small></div><button type="button" className="btn-outline" onClick={() => downloadCard(r)}>⬇ Download card</button></header>
    <div className="rr-totals">{[['Caught', t.caught], ['Blocklisted', t.blocklisted], ['Repeat funders', t.funders], ['Broken Shields', t.brokenShields], ['Rugs/dumps', t.rugs]].map(([l, v]) => <div key={l}><b>{v.toLocaleString()}</b><small>{l}</small></div>)}</div>
    <div className="rr-list">{r.caught.slice(0, 5).map(c => <Link key={c.wallet} to={`/terminal/profile/${c.wallet}`}><code>{short(c.wallet)}</code><CopyBtn value={c.wallet} /><span>{c.roles.join(' + ')} on {c.launches} launch{c.launches === 1 ? '' : 'es'}</span>{c.blocked && <em>⛔</em>}</Link>)}</div>
  </section>;
}

export function ShieldLeaderboard() {
  const [rows, setRows] = useState(null);
  useEffect(() => { fetch(apiUrl('/api/reputation/shields/leaderboard')).then(x => x.json()).then(d => setRows(d.rows || [])).catch(() => setRows([])); }, []);
  return <section className="shield-board" data-testid="shield-leaderboard">
    <header><h3>🛡 Shield leaderboard</h3><small>Creators ranked by public launch promises kept — and broken.</small></header>
    {rows == null ? <p className="wp-bio">Loading…</p> : !rows.length ? <p className="wp-bio">No shielded launches yet. Creators can Shield a coin from the launch page — the first to keep one tops this board.</p>
      : rows.map((r, i) => <Link key={r.creator} to={`/terminal/profile/${r.creator}`} className={`sb-row ${r.broken ? 'has-broken' : ''}`}><span className="sb-rank">#{i + 1}</span><b>@{r.handle}</b><CopyBtn value={r.creator} /><span className="sb-kept">✓ {r.kept} kept</span><span>{r.active} active</span>{r.broken > 0 && <span className="sb-broken">✗ {r.broken} broken</span>}</Link>)}
  </section>;
}

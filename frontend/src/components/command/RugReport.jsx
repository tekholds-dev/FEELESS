import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiUrl } from '../../lib/api';
import { CopyBtn } from '../CopyBtn';
import { ShareGifButton } from '../ShareGif';

const short = a => `${a.slice(0, 4)}…${a.slice(-4)}`;

// The report as a 1200×675 card (X/Twitter size): royal-green panels, stat tiles and the FEE watermark.
async function downloadCard(r) {
  await document.fonts?.ready;
  const logo = await new Promise(res => { const i = new Image(); i.onload = () => res(i); i.onerror = () => res(null); i.src = '/assets/feeless-logo.png'; });
  const c = document.createElement('canvas'); c.width = 1200; c.height = 675; const g = c.getContext('2d');
  g.fillStyle = '#021a10'; g.fillRect(0, 0, 1200, 675);
  for (const [x, y, rad, col] of [[260, 120, 620, '18,192,122,.35'], [1050, 640, 520, '255,45,85,.22']]) { const rg = g.createRadialGradient(x, y, 0, x, y, rad); rg.addColorStop(0, `rgba(${col})`); rg.addColorStop(1, 'rgba(2,26,16,0)'); g.fillStyle = rg; g.fillRect(0, 0, 1200, 675); }
  if (logo) { g.globalAlpha = 0.09; g.drawImage(logo, 760, 60, 520, 520); g.globalAlpha = 1; }
  g.strokeStyle = 'rgba(18,192,122,.5)'; g.lineWidth = 2; g.beginPath(); g.roundRect(28, 28, 1144, 619, 28); g.stroke();
  if (logo) g.drawImage(logo, 60, 58, 64, 64);
  g.fillStyle = '#ffffff'; g.font = '400 60px Bungee, sans-serif'; g.fillText('RUG REPORT', 140, 112);
  g.fillStyle = '#9dffd9'; g.font = '600 22px "Space Grotesk", sans-serif'; g.fillText(`Last ${r.days} days · on-chain evidence only`, 142, 148);
  const t = r.totals;
  [['Caught', t.caught, '#19f58f'], ['Blocklisted', t.blocklisted, '#ff6b8b'], ['Repeat funders', t.funders, '#ffc36b'], ['Broken Shields', t.brokenShields, '#ff6b8b']].forEach(([l, v, col], i) => {
    const x = 60 + i * 272; g.fillStyle = 'rgba(3,20,12,.7)'; g.strokeStyle = 'rgba(255,255,255,.12)'; g.beginPath(); g.roundRect(x, 190, 252, 130, 18); g.fill(); g.stroke();
    g.fillStyle = col; g.shadowColor = col; g.shadowBlur = 16; g.font = '400 54px Bungee, sans-serif'; g.fillText(Number(v).toLocaleString(), x + 22, 262); g.shadowBlur = 0;
    g.fillStyle = '#b9d6c8'; g.font = '600 19px "Space Grotesk", sans-serif'; g.fillText(l, x + 24, 298);
  });
  g.font = '600 22px "JetBrains Mono", monospace';
  (r.caught || []).slice(0, 5).forEach((c2, i) => { g.fillStyle = i % 2 ? 'rgba(255,255,255,.03)' : 'rgba(18,192,122,.06)'; g.fillRect(60, 350 + i * 44, 1080, 40); g.fillStyle = '#eafff3'; g.fillText(`${short(c2.wallet)}   ${c2.roles.join(' + ')} · ${c2.launches} launches${c2.blocked ? '   ⛔ blocked' : ''}`, 76, 377 + i * 44); });
  g.fillStyle = '#19f58f'; g.font = '400 26px Bungee, sans-serif'; g.fillText('FEELESS', 60, 624); g.fillStyle = '#9fb3a8'; g.font = '600 20px "Space Grotesk", sans-serif'; g.fillText('the chain remembers.', 214, 622);
  const a = document.createElement('a'); a.download = `feeless-rug-report-${new Date().toISOString().slice(0, 10)}.png`; a.href = c.toDataURL('image/png'); a.click();
}

const reportGif = r => ({ kicker: `RUG REPORT · LAST ${r.days} DAYS`, title: 'The chain remembers', tone: 'down', bigValue: r.totals.caught, bigDigits: 0, bigSuffix: ' caught',
  lines: [`${r.totals.blocklisted} blocklisted · ${r.totals.funders} repeat funders`, `${r.totals.brokenShields} broken Shields · ${r.totals.rugs} rugs/dumps`, 'On-chain evidence only · FEELESS'] });

export function RugReport() {
  const [r, setR] = useState(null);
  useEffect(() => { fetch(apiUrl('/api/reputation/rug-report?days=7')).then(x => x.json()).then(setR).catch(() => {}); }, []);
  if (!r?.totals) return null;  // no report yet (or an error body): render nothing, never crash
  const t = r.totals;
  return <section className="rug-report" data-testid="rug-report">
    <header><div><h3>Rug Report</h3><small>Last 7 days · every entry is on-chain evidence</small></div><div className="rr-share"><button type="button" className="btn-outline" onClick={() => downloadCard(r)}>⬇ Download card</button><ShareGifButton card={reportGif(r)} /></div></header>
    <div className="rr-totals">{[['Caught', t.caught], ['Blocklisted', t.blocklisted], ['Repeat funders', t.funders], ['Broken Shields', t.brokenShields], ['Rugs/dumps', t.rugs]].map(([l, v]) => <div key={l}><b>{v.toLocaleString()}</b><small>{l}</small></div>)}</div>
    <div className="rr-list">{(r.caught || []).slice(0, 5).map(c => <Link key={c.wallet} to={`/terminal/profile/${c.wallet}`}><code>{short(c.wallet)}</code><CopyBtn value={c.wallet} profile /><span>{c.roles.join(' + ')} on {c.launches} launch{c.launches === 1 ? '' : 'es'}</span>{c.blocked && <em>⛔</em>}</Link>)}</div>
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

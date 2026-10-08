import React, { useEffect, useState } from 'react';
import { sharedJson } from '../lib/sharedJson';
import '../styles/rugBounty.css';

// 🪙 RUG BOUNTY: recent catches and the top finders. Only wallets FEELESS's own forensics prove bundled or sniped the coin are accepted
// (the same rule as reporting from a launch's forensics), the first finder earns season points. GET /bounty. Fits the Reputation page.
const ago = at => { const m = Math.max(1, Math.round((Date.now() / 1000 - at) / 60)); return m < 60 ? `${m}m` : m < 2880 ? `${Math.round(m / 60)}h` : `${Math.round(m / 1440)}d`; };
export const shortMint = m => (m ? `${m.slice(0, 4)}…${m.slice(-4)}` : '');
export const catchLine = c => `${c.wallets} wallet${c.wallets === 1 ? '' : 's'} flagged${c.bundlers ? ` · ${c.bundlers} bundled` : ''}${c.snipers ? ` · ${c.snipers} sniped` : ''}`;
const TABS = [['recent', '🆕 Recent catches'], ['week', '🏆 Top finders · week'], ['all', '👑 All time']];

export function RugBounty() {
  const [d, setD] = useState(null); const [tab, setTab] = useState('recent');
  useEffect(() => { let alive = true; sharedJson('/api/reputation/bounty', { maxAge: 60000 }).then(x => alive && setD(x)).catch(() => {}); return () => { alive = false; }; }, []);
  const rows = d?.[tab] || [];
  return <section className="rb m-card m-live" data-testid="rug-bounty">
    <header><span className="m-label">🪙 RUG BOUNTY</span><small data-tip={d?.rule || 'Evidence-checked reports earn season points.'}>{d?.total ? `${d.total.wallets} wallets flagged on ${d.total.coins} coins` : 'evidence-checked reports earn points'}</small></header>
    <div className="m-seg rb-seg" role="tablist">{TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{l}</button>)}</div>
    {!d && <small className="m-dim">Loading the board…</small>}
    {d && !rows.length && <p className="rb-empty m-dim">{tab === 'recent' ? 'No catches yet. Open a launch\'s forensics and report the wallets it proves bundled or sniped — the first finder earns points.' : 'Nobody on the board for this window yet.'}</p>}
    <ol className="rb-list">{tab === 'recent' ? rows.map((c, i) => <li key={c.mint} style={{ '--i': i }}>
      <a className="rb-coin" href={`/terminal/coin/solana/${c.mint}`} data-tip="Open this coin">{shortMint(c.mint)}</a><span className="rb-what">{catchLine(c)}</span>
      <span className="rb-who">{(c.finders || []).map(f => <a key={f.address} href={`/terminal/profile/${f.address}`}>{f.name}</a>)}</span><i>{ago(c.at)}</i></li>)
      : rows.map((r, i) => <li key={r.address} style={{ '--i': i }}><b className="rb-rank">{i + 1}</b><a className="rb-coin" href={`/terminal/profile/${r.address}`}>{r.name}</a>
        <span className="rb-what">{r.wallets} wallet{r.wallets === 1 ? '' : 's'} · {r.coins} coin{r.coins === 1 ? '' : 's'}</span><em className="m-num rb-pts" data-tip="Season points earned for finds (25 a new wallet, max 100 a coin)">+{r.pts}</em></li>)}</ol>
    <small className="m-dim rb-rule">{d?.rule}</small>
  </section>;
}

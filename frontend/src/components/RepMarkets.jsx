import React, { useCallback, useEffect, useState } from 'react';
import { useWallet } from '../hooks/useWallet';
import { apiUrl } from '../lib/api';
import { getChatSession } from '../lib/chatSession';
import '../styles/repMarkets.css';

// 🛡 Rep markets: YES / NO on what FEELESS measures. Free weekly chips (never bought, sent or cashed out) — net gain becomes season points.
// The twist: two prices per market — the crowd's chips, and the same chips weighted by each wallet's verified trust score.
export const KIND_WORD = { up: 'UP 1H', double: '2× IN 4H', rug: 'RUG WATCH' };
export function clock(sec) {
  if (!(sec > 0)) return 'closed';
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = Math.floor(sec % 60);
  return h ? `${h}h ${m}m` : `${m}:${String(s).padStart(2, '0')}`;
}
export function sparkPath(path, w = 120, h = 30) {
  const p = (path || []).filter(v => v > 0);
  if (p.length < 2) return '';
  const lo = Math.min(...p, 1), hi = Math.max(...p, 1), span = hi - lo || 1;
  return p.map((v, i) => `${i ? 'L' : 'M'}${((i / (p.length - 1)) * w).toFixed(1)},${(h - ((v - lo) / span) * h).toFixed(1)}`).join(' ');
}
const STAKES = [25, 100, 250];

function Market({ m, now, onStake, busy }) {
  const left = m.closesAt - now, locked = now >= m.locksAt || m.state !== 'open';
  const up = (m.move ?? 0) >= 0;
  return (
    <article className={`rpm-card k-${m.kind} ${m.split ? 'is-split' : ''} ${m.state !== 'open' ? `is-done r-${m.result}` : ''}`}>
      <header>
        <span className="rpm-kind">{m.icon} {KIND_WORD[m.kind]}</span>
        {m.split && <span className="rpm-split" data-tip="Wallets with a FEELESS record disagree with the crowd by 15+ points">⚡ SMART SPLIT</span>}
        <span className="rpm-clock">{m.state === 'open' ? (locked ? '🔒 locked' : `⏱ ${clock(left)}`) : `✓ ${String(m.result).toUpperCase()}`}</span>
      </header>
      <h4>{m.q}</h4>
      <div className="rpm-live">
        <svg viewBox="0 0 120 30" preserveAspectRatio="none" aria-hidden="true"><path d={sparkPath(m.path)} className={up ? 'up' : 'dn'} /></svg>
        <b className={up ? 'up' : 'dn'}>{m.move == null ? '—' : `${up ? '+' : ''}${m.move.toFixed(1)}%`}</b>
        <small>peak {m.peak == null ? '—' : `${m.peak >= 0 ? '+' : ''}${m.peak.toFixed(1)}%`}</small>
      </div>
      <div className="rpm-odds">
        <div><em>CROWD</em><i style={{ transform: `scaleX(${m.crowd / 100})` }} /><b>{m.crowd}¢ YES</b></div>
        <div className="is-rep"><em>🛡 REP</em><i style={{ transform: `scaleX(${m.rep / 100})` }} /><b>{m.rep}¢ YES</b></div>
      </div>
      <p className="rpm-pool">{m.yes + m.no} chips · {m.n} backers</p>
      {m.mine && <p className="rpm-mine">You: <b>{m.mine.side.toUpperCase()}</b> {m.mine.chips}{m.mine.paid != null && <> → <b className={m.mine.paid > m.mine.chips ? 'up' : m.mine.paid < m.mine.chips ? 'dn' : ''}>{m.mine.paid}</b></>}</p>}
      {m.state === 'open' && !locked && (
        <div className="rpm-acts">
          {['yes', 'no'].map(side => (
            <div key={side} className={`rpm-side s-${side}`}>
              <span>{side.toUpperCase()}</span>
              {STAKES.map(c => <button key={c} type="button" disabled={busy || (m.mine && m.mine.side !== side)} onClick={() => onStake(m.id, side, c)} data-testid={`rpm-${m.id}-${side}-${c}`}>{c}</button>)}
            </div>
          ))}
        </div>
      )}
    </article>
  );
}

export default function RepMarkets() {
  const { wallet, signMessage, connect } = useWallet() || {};
  const address = wallet?.address;
  const [d, setD] = useState(null);
  const [now, setNow] = useState(() => Date.now() / 1000);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [lens, setLens] = useState('live');
  const load = useCallback(() => fetch(apiUrl(`/api/reputation/rep-markets${address ? `?address=${address}` : ''}`)).then(r => (r.ok ? r.json() : null)).then(x => x && setD(x)).catch(() => {}), [address]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, 15000); return () => clearInterval(t); }, [load]);
  useEffect(() => { const t = setInterval(() => setNow(Date.now() / 1000), 1000); return () => clearInterval(t); }, []);
  const onStake = async (market, side, chips) => {
    if (!address) { connect?.(); return; }
    setBusy(true); setErr('');
    try {
      const session = await getChatSession(address, signMessage);
      const r = await fetch(apiUrl('/api/reputation/rep-markets/stake'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address, session, market, side, chips }) });
      const b = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(b.detail || 'Stake refused.');
      setD(b);
    } catch (e) { setErr(e.message || 'Stake refused.'); }
    setBusy(false);
  };
  const list = (lens === 'live' ? d?.live : d?.settled) || [];
  return (
    <section className="rpm m-card m-live" data-testid="rep-markets">
      <header className="rpm-head">
        <div>
          <span className="m-label">🛡 REP MARKETS</span>
          <h3>Call it. Prove it.</h3>
          <small>Free chips every week · settled on recorded prices · two prices: the crowd and the wallets with a record.</small>
        </div>
        <div className="rpm-bank">
          {d?.bank ? <><em>YOUR CHIPS</em><b>{d.bank.chips}</b><small>+{d.bank.won} / −{d.bank.lost} · {d.bank.pts} season pts</small></>
            : <button type="button" className="m-btn" onClick={() => connect?.()}>Connect to play</button>}
        </div>
      </header>
      <div className="rpm-bar">
        <div className="m-seg">
          <button type="button" className={lens === 'live' ? 'active' : ''} onClick={() => setLens('live')}>⚡ Live {d?.live?.length || 0}</button>
          <button type="button" className={lens === 'settled' ? 'active' : ''} onClick={() => setLens('settled')}>✓ Settled</button>
        </div>
        {!!d?.top?.length && <p className="rpm-top">🏆 {d.top.slice(0, 5).map((t, i) => <span key={t.w}>{i + 1}. {t.w} <b>+{t.net}</b></span>)}</p>}
      </div>
      {err && <p className="rpm-err">⚠ {err}</p>}
      {list.length ? <div className="rpm-grid">{list.map((m, i) => <div key={m.id} style={{ '--i': i }} className="rpm-cell"><Market m={m} now={now} onStake={onStake} busy={busy} /></div>)}</div>
        : <p className="rpm-empty">{lens === 'live' ? 'New markets open every hour from Pump trending and the trench list.' : 'Nothing settled yet this week.'}</p>}
      <p className="rpm-rules">Stake {d?.rules?.min || 10}–{d?.rules?.max || 500} chips · one side per market · locks 2 min before the close · {d?.rules?.perPt || 10} chips won = 1 season point. Points only — never money.</p>
    </section>
  );
}

import React, { useMemo } from 'react';
import { FeeCatMark } from '../FeeCatMark';
import { openWarRoom } from '../WarRoomHost';
import { callThread, callStats, capWord } from '../../lib/feeCallChat';
import '../../styles/feeCallChat.css';

// 🐱 FEE'S CALLS — a chat, not a list (owner 2026-10-29, N15). Fee speaks every BUY / SELL in her own words: what she did, why, her tags
// (setup · the AI's verdict), the cap she called it at; each BUY carries its thread — the SELL that closed it (result + how long she held) or
// "still holding". Read-only (her calls, not a room); a coin chip opens its war room. Live: a scanning line while she hunts, a 24h strip
// (calls · closed · won · net), new calls slide in. Data: FeeLiveTab's one shared read of /api/cats/activity?catId=leader.
const ago = s => { const d = Math.max(0, Math.round(Date.now() / 1000 - s)); return d < 60 ? `${d}s` : d < 3600 ? `${Math.round(d / 60)}m` : d < 86400 ? `${Math.round(d / 3600)}h` : `${Math.round(d / 86400)}d`; };
const sol = v => `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(4)} SOL`;
const pct = v => `${v > 0 ? '+' : ''}${v}%`;

function Bubble({ m, first, i }) {
  const coin = m.coin ? <button type="button" className="fcc-coin" disabled={!m.pair} onClick={() => openWarRoom({ chainId: 'solana', pairAddress: m.pair, baseToken: { symbol: m.coin } })}
    data-tip={m.pair ? `Open $${m.coin}'s war room` : `$${m.coin}`} data-testid="fcc-coin">${m.coin}</button> : null;
  return <li className={`fcc-msg is-${m.side.toLowerCase()}${first ? ' is-first' : ''}`} style={{ '--i': i }} data-testid="fcc-msg">
    <span className="fcc-av" aria-hidden="true">{first ? <FeeCatMark size={30} animate={false} /> : null}</span>
    <div className="fcc-bubble">
      {first ? <p className="fcc-who"><b>Fee</b><small>{ago(m.at)} ago</small></p> : null}
      <p className="fcc-head"><em className="fcc-side">{m.side}</em>{coin}
        {m.side === 'BUY' && m.sol != null ? <span className="m-num">{m.sol} SOL</span> : null}
        {m.side === 'SELL' && m.move != null ? <span className={`m-num ${m.move >= 0 ? 'is-up' : 'is-dn'}`}>{pct(m.move)}</span> : null}
        {(m.side === 'BUY' ? m.cap : m.cap || m.entryCap) ? <small className="fcc-cap" data-tip="The market cap when she called it">@ {capWord(m.side === 'BUY' ? m.cap : m.cap || m.entryCap)} MC</small> : null}</p>
      {m.why ? <p className="fcc-why">{m.why}</p> : null}
      {m.tags.length ? <p className="fcc-tags">{m.tags.map(t => <i key={t} className={/AI/.test(t) ? 'is-ai' : ''}>{t}</i>)}</p> : null}
      {m.side === 'SELL' && m.pnl != null ? <p className={`fcc-res ${m.pnl >= 0 ? 'is-up' : 'is-dn'}`}><b className="m-num">{sol(m.pnl)}</b><small>on the price move · fees apart</small></p> : null}
      {m.closed ? <p className={`fcc-thread ${(m.closed.pnl || 0) >= 0 ? 'is-up' : 'is-dn'}`} data-testid="fcc-closed">↳ closed {m.closed.move != null ? pct(m.closed.move) : ''}{m.closed.pnl != null ? ` · ${sol(m.closed.pnl)}` : ''} · held {m.closed.heldMin}m</p>
        : m.open ? <p className="fcc-thread is-open" data-testid="fcc-open"><i aria-hidden="true" />↳ still holding</p> : null}
    </div>
  </li>;
}

export function FeeCallChat({ events, positions, hunting }) {
  const msgs = useMemo(() => callThread(events, positions).slice(0, 14), [events, positions]);
  const st = useMemo(() => callStats(msgs), [msgs]);
  return <div className="fcc" data-testid="fee-call-chat">
    <header className="fcc-top"><b>🐱 FEE'S CALLS</b><span className={`fcc-live${hunting ? ' is-on' : ''}`}><i aria-hidden="true" />{hunting ? 'LIVE' : 'NAPPING'}</span>
      <span className="fcc-st" data-tip="Her last 24 hours: calls made · trades closed · closed green · net on the price move (fees apart)">
        <span><small>24H</small><b className="m-num">{st.calls}</b></span><span><small>CLOSED</small><b className="m-num">{st.closed}</b></span>
        <span><small>WON</small><b className="m-num">{st.closed ? `${Math.round((st.won / st.closed) * 100)}%` : '—'}</b></span>
        <span className={st.pnl > 0 ? 'is-up' : st.pnl < 0 ? 'is-dn' : ''}><small>NET</small><b className="m-num">{st.closed ? sol(st.pnl) : '—'}</b></span></span></header>
    {hunting ? <p className="fcc-typing" aria-live="polite"><FeeCatMark size={18} animate={false} /><span>Fee is scanning the board</span><i aria-hidden="true" /><i aria-hidden="true" /><i aria-hidden="true" /></p> : null}
    {msgs.length ? <ol className="fcc-list">{msgs.map((m, i) => <Bubble key={m.id} m={m} i={i} first={i === 0 || Math.abs(msgs[i - 1].at - m.at) > 600} />)}</ol>
      : <p className="fcc-empty">No calls yet — she waits for a coin that passes every check.</p>}
  </div>;
}

import React, { useState } from 'react';
import { useTradeStream } from '../../lib/tradeStream';
import { useWallet } from '../../hooks/useWallet';
import { formatUSD } from '../../lib/dexscreener';
import { formatLivePrice } from '../../lib/livePrice';
import { investigate } from '../CaseFile';
import { useWalletTags } from '../../lib/coinIntel';
import { FLOW_WINDOWS, TrenchPulse } from './TrenchPulse';
import { Ic3 } from '../../lib/icon3d';

const TX_EXPLORER = { solana: 'https://solscan.io/tx/', ethereum: 'https://etherscan.io/tx/', base: 'https://basescan.org/tx/', bsc: 'https://bscscan.com/tx/', arbitrum: 'https://arbiscan.io/tx/', avalanche: 'https://snowtrace.io/tx/', polygon: 'https://polygonscan.com/tx/', sui: 'https://suiscan.xyz/mainnet/tx/' };

// A whale is a trade ≥ $1K and ≥ 5× the tape's median size (so a $1K buy on a $5M coin isn't a whale).
export function whaleCut(trades) {
  const sizes = trades.map(t => Number(t.usd) || 0).sort((a, b) => a - b);
  const median = sizes.length ? sizes[Math.floor(sizes.length / 2)] : 0;
  return Math.max(1000, median * 5);
}

const FACE_KEY = 'feeless.tapeFace'; const WIN_KEY = 'feeless.flowWin';
const read = (k, d) => { try { return localStorage.getItem(k) || d; } catch { return d; } };
const keep = (k, v) => { try { localStorage.setItem(k, String(v)); } catch { /* this visit only */ } };

// Live swaps under the chart: buy pressure, whales flagged, your own trades marked, any wallet → case file.
// 🔁 trench dash v2 (Slice 34): the card FLIPS — front = this live tape, back = the Flow read (the pulse, redesigned) — both from the one trade stream.
export function TradeTape({ pair, rows = 12 }) {
  const { trades, feed = { state: 'live' } } = useTradeStream(pair);
  const dead = !trades.length && feed.state === 'down';   // 📡 no trades because the feed is down: say so, never call it quiet
  const [face, setFace] = useState(() => (read(FACE_KEY, 'tape') === 'flow' ? 'flow' : 'tape'));
  const [win, setWin] = useState(() => { const n = Number(read(WIN_KEY, 60)); return FLOW_WINDOWS.some(w => w[0] === n) ? n : 60; });
  const flip = () => setFace(f => { const n = f === 'tape' ? 'flow' : 'tape'; keep(FACE_KEY, n); return n; });
  const me = (useWallet() || {}).wallet?.address;
  const tags = useWalletTags(pair);
  if (!pair) return null;
  const list = trades.slice(0, rows);
  const cut = whaleCut(trades);
  const buyUsd = list.reduce((a, t) => a + (t.kind === 'buy' ? Number(t.usd) || 0 : 0), 0);
  const allUsd = list.reduce((a, t) => a + (Number(t.usd) || 0), 0);
  const explorer = TX_EXPLORER[pair.chainId];
  const turn = <button type="button" className="tape-turn" onClick={flip} aria-pressed={face === 'flow'} data-tip={face === 'tape' ? 'Flip to the Flow read: who is really in charge, by $' : 'Back to the live tape'} data-testid="tape-flip">↻ {face === 'tape' ? 'Flow read' : 'Tape'}</button>;
  if (face === 'flow') return <div className="trade-tape is-flow" data-testid="trade-tape">
    <div className="trade-tape-head"><span><i />FLOW READ</span>
      <span className="tape-win" role="group" aria-label="Window">{FLOW_WINDOWS.map(([n, l]) => <button key={n} type="button" aria-pressed={win === n} onClick={() => { setWin(n); keep(WIN_KEY, n); }} data-testid={`flow-win-${n}`}>{l}</button>)}</span>
      <small>{dead ? 'trade feed down: nothing to read' : 'from the same trades as the tape'}</small>{turn}</div>
    {dead ? <p className="tape-dead" data-testid="flow-dead">The trade feed is down ({feed.error}). The Flow read needs real trades, so it calls nothing until the feed is back.</p> : <TrenchPulse trades={trades} tags={tags} me={me} sec={win} flow />}
  </div>;
  return <div className="trade-tape" data-testid="trade-tape">
    <div className="trade-tape-head"><span><i />LIVE TRADE TAPE</span>
      <small>{list.length ? `${allUsd ? `${Math.round((buyUsd / allUsd) * 100)}% buys · ` : ''}last ${Math.max(0, Math.round((Date.now() - Date.parse(list[0].ts)) / 1000))}s ago` : dead ? `trade feed down (${feed.error}): no trades shown` : feed.state === 'empty' ? 'no trades on this pool yet' : 'waiting for trades…'}</small>{turn}</div>
    <div className="trade-tape-list custom-scroll">{list.map(t => {
      const mine = t.mine || (me && t.wallet === me);
      return <div key={t.tx} className={`tape-row ${t.kind} ${mine ? 'is-mine' : ''} ${(Number(t.usd) || 0) >= cut ? 'is-whale' : ''}`} data-testid="tape-row">
        <b>{t.kind === 'buy' ? 'BUY' : 'SELL'}</b><span>{formatUSD(t.usd)}</span>
        <a href={explorer ? `${explorer}${t.tx}` : undefined} target="_blank" rel="noopener noreferrer" title="Open the transaction">{formatLivePrice(t.price)}</a>
        <code>{mine ? '✓ YOU' : t.wallet ? <a className="tape-who" href={`/terminal/profile/${t.wallet}`} title="Open this wallet's profile">{`${t.wallet.slice(0, 4)}…${t.wallet.slice(-4)}`}</a> : '—'}{(tags.get(t.wallet) || []).map(g => <em key={g.id} className={`tape-tag ${g.tone}`} title={g.why} data-testid={`tape-tag-${g.id}`}>{g.label}</em>)}</code>
        {t.wallet && !mine ? <button type="button" className="tape-case" title="Open this wallet's case file" aria-label="Open case file" onClick={() => investigate(t.wallet)}><Ic3 e="🔎" /></button> : <span />}
      </div>;
    })}</div>
  </div>;
}

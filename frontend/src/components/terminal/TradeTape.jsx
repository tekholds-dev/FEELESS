import React from 'react';
import { useTradeStream } from '../../lib/tradeStream';
import { useWallet } from '../../hooks/useWallet';
import { formatUSD } from '../../lib/dexscreener';
import { formatLivePrice } from '../../lib/livePrice';
import { investigate } from '../CaseFile';
import { useWalletTags } from '../../lib/coinIntel';

const TX_EXPLORER = { solana: 'https://solscan.io/tx/', ethereum: 'https://etherscan.io/tx/', base: 'https://basescan.org/tx/', bsc: 'https://bscscan.com/tx/', arbitrum: 'https://arbiscan.io/tx/', avalanche: 'https://snowtrace.io/tx/', polygon: 'https://polygonscan.com/tx/', sui: 'https://suiscan.xyz/mainnet/tx/' };

// A whale is a trade ≥ $1K and ≥ 5× the tape's median size (so a $1K buy on a $5M coin isn't a whale).
export function whaleCut(trades) {
  const sizes = trades.map(t => Number(t.usd) || 0).sort((a, b) => a - b);
  const median = sizes.length ? sizes[Math.floor(sizes.length / 2)] : 0;
  return Math.max(1000, median * 5);
}

// Live swaps under the chart: buy pressure, whales flagged, your own trades marked, any wallet → case file.
export function TradeTape({ pair, rows = 12 }) {
  const { trades } = useTradeStream(pair);
  const me = (useWallet() || {}).wallet?.address;
  const tags = useWalletTags(pair);
  if (!pair) return null;
  const list = trades.slice(0, rows);
  const cut = whaleCut(trades);
  const buyUsd = list.reduce((a, t) => a + (t.kind === 'buy' ? Number(t.usd) || 0 : 0), 0);
  const allUsd = list.reduce((a, t) => a + (Number(t.usd) || 0), 0);
  const explorer = TX_EXPLORER[pair.chainId];
  return <div className="trade-tape" data-testid="trade-tape">
    <div className="trade-tape-head"><span><i />LIVE TRADE TAPE</span>
      <small>{list.length ? `${allUsd ? `${Math.round((buyUsd / allUsd) * 100)}% buys · ` : ''}last ${Math.max(0, Math.round((Date.now() - Date.parse(list[0].ts)) / 1000))}s ago` : 'waiting for trades…'}</small></div>
    <div className="trade-tape-list custom-scroll">{list.map(t => {
      const mine = t.mine || (me && t.wallet === me);
      return <div key={t.tx} className={`tape-row ${t.kind} ${mine ? 'is-mine' : ''} ${(Number(t.usd) || 0) >= cut ? 'is-whale' : ''}`} data-testid="tape-row">
        <b>{t.kind === 'buy' ? 'BUY' : 'SELL'}</b><span>{formatUSD(t.usd)}</span>
        <a href={explorer ? `${explorer}${t.tx}` : undefined} target="_blank" rel="noopener noreferrer" title="Open the transaction">{formatLivePrice(t.price)}</a>
        <code>{mine ? '✓ YOU' : t.wallet ? `${t.wallet.slice(0, 4)}…${t.wallet.slice(-4)}` : '—'}{(tags.get(t.wallet) || []).map(g => <em key={g.id} className={`tape-tag ${g.tone}`} title={g.why} data-testid={`tape-tag-${g.id}`}>{g.label}</em>)}</code>
        {t.wallet && !mine ? <button type="button" className="tape-case" title="Open this wallet's case file" aria-label="Open case file" onClick={() => investigate(t.wallet)}>🔎</button> : <span />}
      </div>;
    })}</div>
  </div>;
}

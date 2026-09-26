import React from 'react';
import { apiUrl } from '../lib/api';
import { formatUSD, formatPct, shortAddress } from '../lib/dexscreener';

// Slash commands. Lookup commands show a private card (only you see it); text commands post.
export const COMMANDS = [
  { cmd: 'price', args: '$TICKER | CA', desc: 'Live price, MC, liquidity, 24h', tier: 0 },
  { cmd: 'chart', args: '$TICKER | CA', desc: 'Open the coin in a new tab', tier: 0 },
  { cmd: 'fee', args: '', desc: "Fee the Leader cat's live positions + PnL", tier: 0 },
  { cmd: 'top', args: '', desc: 'Top 5 trending on Solana right now', tier: 0 },
  { cmd: 'callers', args: '', desc: 'Call Ledger leaderboard (7d)', tier: 0 },
  { cmd: 'perks', args: '', desc: 'Your $FEE holder tier and what it unlocks', tier: 0 },
  { cmd: 'me', args: '', desc: 'Open your profile', tier: 0 },
  { cmd: 'gm', args: '', desc: 'Post a gm ☀️', tier: 0, post: 'gm ☀️ trenches' },
  { cmd: 'wagmi', args: '', desc: 'Post WAGMI 🚀', tier: 0, post: 'WAGMI 🚀🌿' },
  { cmd: 'ngmi', args: '', desc: 'Post NGMI 💀', tier: 0, post: 'ngmi 💀' },
  { cmd: 'shrug', args: 'text', desc: 'Append ¯\\_(ツ)_/¯', tier: 0, post: a => `${a ? `${a} ` : ''}¯\\_(ツ)_/¯` },
  { cmd: 'scan', args: 'CA', desc: 'Holders, snipers & concentration check', tier: 1 },
  { cmd: 'alpha', args: '', desc: "Fee's live read on this room's coin", tier: 2 },
  { cmd: 'boost', args: 'message', desc: 'Send a boosted, highlighted message', tier: 2 },
  { cmd: 'whales', args: '', desc: "Top holders of this room's coin", tier: 3 },
];
const TIER_NAME = ['Trencher', 'Fee Friend ($10+)', 'Fee Insider ($100+)', 'Fee Whale ($1k+)'];

async function findPair(arg) {
  const q = String(arg || '').trim().replace(/^\$/, '').replace(/^CA:/i, '');
  if (!q) throw new Error('Add a $TICKER or CA.');
  const d = await (await fetch(`https://api.dexscreener.com/latest/dex/search?q=${encodeURIComponent(q)}`)).json();
  const pairs = (d.pairs || []).filter(p => (p.baseToken?.address === q) || p.baseToken?.symbol?.toLowerCase() === q.toLowerCase());
  // Rank by real 24h volume — liquidity alone is easy to fake on junk pools.
  const best = (pairs.length ? pairs : d.pairs || []).sort((a, b) => (b.volume?.h24 || 0) - (a.volume?.h24 || 0))[0];
  if (!best) throw new Error(`Nothing found for ${arg}.`);
  return best;
}
const roomPair = room => { const m = /^coin-([a-z0-9]+)-([A-Za-z0-9]+)-/.exec(room || ''); return m ? { chainId: m[1], pairAddress: m[2] } : null; };
async function pairFromRoom(room) {
  const r = roomPair(room); if (!r) throw new Error('Use this inside a coin room.');
  const d = await (await fetch(`https://api.dexscreener.com/latest/dex/pairs/${r.chainId}/${r.pairAddress}`)).json();
  if (!d.pairs?.[0]) throw new Error('Coin data unavailable.'); return d.pairs[0];
}
const coinHref = p => `/?coin=${p.chainId}:${p.pairAddress}`;

export async function runCommand(line, { room, wallet, tier }) {
  const [, name, rest = ''] = /^\/(\w+)\s*(.*)$/.exec(line.trim()) || [];
  const c = COMMANDS.find(x => x.cmd === (name || '').toLowerCase());
  if (!c) return { card: { title: 'Unknown command', lines: [`Try: ${COMMANDS.map(x => `/${x.cmd}`).join(' ')}`] } };
  if (c.tier > (tier || 0)) return { card: { title: `🔒 /${c.cmd} is a ${TIER_NAME[c.tier]} perk`, lines: ['Hold more $FEE to unlock it — type /perks to see your tier.'] } };
  if (c.post) return { post: typeof c.post === 'function' ? c.post(rest) : c.post };
  if (c.cmd === 'boost') { if (!rest.trim()) throw new Error('Write the message after /boost.'); return { post: rest.trim(), boost: true }; }
  if (c.cmd === 'me') { if (!wallet?.address) throw new Error('Connect a wallet first.'); window.open(`/terminal/profile/${wallet.address}`, '_blank', 'noopener'); return { card: { title: 'Opened your profile ↗', lines: [] } }; }
  if (c.cmd === 'chart') { const p = await findPair(rest); window.open(coinHref(p), '_blank', 'noopener'); return { card: { title: `Opened $${p.baseToken.symbol} ↗`, lines: [] } }; }
  if (c.cmd === 'price') {
    const p = await findPair(rest);
    return { card: { title: `$${p.baseToken.symbol} · ${formatUSD(p.priceUsd)}`, href: coinHref(p), img: p.info?.imageUrl, lines: [`24h ${formatPct(p.priceChange?.h24)} · 1h ${formatPct(p.priceChange?.h1)} · 5m ${formatPct(p.priceChange?.m5)}`, `MC ${formatUSD(p.marketCap || p.fdv)} · Liq ${formatUSD(p.liquidity?.usd)} · Vol ${formatUSD(p.volume?.h24)}`, `Buys/sells 1h: ${p.txns?.h1?.buys ?? '—'}/${p.txns?.h1?.sells ?? '—'}`] } };
  }
  if (c.cmd === 'fee') {
    const d = await (await fetch('/api/cats/leader')).json(); const cat = d.cat || {};
    return { card: { title: `🐱 Fee · ${Number(cat.balanceSol || 0).toFixed(2)} SOL · PnL ${Number(cat.totalPnlSol || 0).toFixed(3)} SOL`, lines: (cat.positions || []).length ? cat.positions.map(p => `${p.symbol}: ${Number(p.currentChange ?? 0).toFixed(1)}% · ${Number(p.costSol).toFixed(2)} SOL in`) : ['No open positions — Fee is watching the tape.'] } };
  }
  if (c.cmd === 'top') {
    const d = await (await fetch(apiUrl('/api/market/feed?kind=trending&chain=solana&page=1'))).json();
    return { card: { title: '🔥 Trending on Solana', lines: (d.pairs || []).slice(0, 5).map((p, i) => `${i + 1}. $${p.baseToken?.symbol} ${formatUSD(p.priceUsd)} · ${formatPct(p.priceChange?.h24)} · vol ${formatUSD(p.volume?.h24)}`) } };
  }
  if (c.cmd === 'callers') {
    const d = await (await fetch(apiUrl('/api/reputation/calls/leaderboard?days=7'))).json();
    const rows = (d.rows || []).slice(0, 5);
    return { card: { title: '🎯 Call Ledger · 7 days', lines: rows.length ? rows.map((r, i) => `${i + 1}. ${r.caller} — ${r.calls} calls, ${Math.round(r.hitRate * 100)}% hit 2×`) : ['No calls yet — drop a CA to get on the board.'] } };
  }
  if (c.cmd === 'perks') {
    if (!wallet?.address) throw new Error('Connect a wallet to see your tier.');
    const d = await (await fetch(apiUrl(`/api/reputation/perks/${wallet.address}`))).json(); const t = d.tiers[d.tier];
    return { card: { title: `${t.icon} ${t.name} · holding $${d.feeUsd} of $FEE`, lines: [...t.perks.map(x => `✓ ${x}`), d.next ? `Next: ${d.next.name} — $${d.next.needUsd} more $FEE` : '👑 Max tier.'] } };
  }
  if (c.cmd === 'scan') {
    const p = await findPair(rest);
    const d = await (await fetch(apiUrl(`/api/reputation/intel/${p.chainId}/${p.baseToken.address}`))).json();
    const top = (d.topHolders || []).filter(h => h.kind === 'wallet');
    const top10 = top.slice(0, 10).reduce((s, h) => s + h.pct, 0);
    return { card: { title: `🔎 Scan · $${p.baseToken.symbol}`, href: coinHref(p), lines: [`Top 10 wallets hold ${top10.toFixed(1)}% of supply${top10 > 40 ? ' ⚠️ concentrated' : ''}`, `Biggest wallet: ${top[0] ? `${shortAddress(top[0].owner)} · ${top[0].pct.toFixed(2)}%` : '—'}`, ...(d.snipers?.length ? [`Snipers seen: ${d.snipers.length}`] : []), ...(d.bundlers?.length ? [`Bundled wallets: ${d.bundlers.length}`] : []), `Liq ${formatUSD(p.liquidity?.usd)} · MC ${formatUSD(p.marketCap || p.fdv)}`] } };
  }
  if (c.cmd === 'alpha') {
    const p = await pairFromRoom(room);
    const t = p.txns?.h1 || {}; const flow = (t.buys || 0) + (t.sells || 0) ? t.buys / (t.buys + t.sells) : null;
    const liqR = (p.liquidity?.usd || 0) / ((p.marketCap || p.fdv) || 1);
    return { card: { title: `🐱 Fee's read · $${p.baseToken.symbol}`, href: coinHref(p), lines: [`Momentum: 5m ${formatPct(p.priceChange?.m5)}, 1h ${formatPct(p.priceChange?.h1)}, 6h ${formatPct(p.priceChange?.h6)}`, flow != null ? `Order flow 1h: ${Math.round(flow * 100)}% buys (${t.buys}/${t.sells}) — ${flow > 0.55 ? 'buyers pressing' : flow < 0.45 ? 'sellers pressing' : 'balanced'}` : 'No order-flow data.', `Liquidity ${(liqR * 100).toFixed(1)}% of MC — ${liqR < 0.05 ? 'thin, careful with size' : 'healthy'}`, 'Rules-based read · not financial advice'] } };
  }
  if (c.cmd === 'whales') {
    const p = await pairFromRoom(room);
    const d = await (await fetch(apiUrl(`/api/reputation/intel/${p.chainId}/${p.baseToken.address}`))).json();
    return { card: { title: `🐋 Top holders · $${p.baseToken.symbol}`, lines: (d.topHolders || []).filter(h => h.kind === 'wallet').slice(0, 8).map((h, i) => `${i + 1}. ${shortAddress(h.owner)} — ${h.pct.toFixed(2)}%`) } };
  }
  return { card: { title: `/${c.cmd}`, lines: [] } };
}

export function SlashMenu({ input, tier, onPick }) {
  if (!input.startsWith('/') || input.includes(' ')) return null;
  const q = input.slice(1).toLowerCase();
  const list = COMMANDS.filter(c => c.cmd.startsWith(q));
  if (!list.length) return null;
  return <div className="slash-menu" role="listbox" data-testid="slash-menu">{list.map(c => <button type="button" key={c.cmd} className={c.tier > tier ? 'locked' : ''} onMouseDown={e => { e.preventDefault(); onPick(c); }}>
    <b>/{c.cmd}</b>{c.args && <code>{c.args}</code>}<span>{c.desc}</span>{c.tier > tier && <em>🔒 {TIER_NAME[c.tier]}</em>}
  </button>)}</div>;
}

export function CommandCard({ card, onClose }) {
  return <div className="cmd-card" data-testid="command-card"><div className="cmd-card-head">{card.img && <img src={card.img} alt="" />}<b>{card.title}</b><small>only you see this</small><button type="button" onClick={onClose} aria-label="Dismiss">×</button></div>
    {card.lines.map((l, i) => <p key={i}>{l}</p>)}{card.href && <a href={card.href} target="_blank" rel="noopener noreferrer">Open in FEELESS ↗</a>}</div>;
}

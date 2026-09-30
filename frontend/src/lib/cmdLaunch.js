// Command Center launcher helpers (pure): which terms a coin launches under, the receipt links, and form checks.
const unit = p => (p?.quote === 'USDC' ? 'USDC' : 'SOL');

export function launchTerms(kind, cfg) {
  if (kind === 'pump') return [['Curve', 'Pump.fun bonding curve'], ['Supply', '1B fixed'], ['Trading fee', 'Pump.fun’s own'], ['Graduates to', 'PumpSwap'], ['Mint / freeze', 'revoked by pump.fun']];
  const p = cfg?.params || {};
  const u = unit(p);
  return [
    ['Config', cfg?.label || (kind === 'house' ? 'House config' : 'FEELESS public config')],
    ['Opens → graduates', `${Number(p.initialMarketCap ?? 30)} → ${Number(p.migrationMarketCap ?? 500)} ${u}`],
    ['Snipe tax', `${Number(p.startingFeeBps ?? 9900) / 100}% → ${Number(p.endingFeeBps ?? 100) / 100}% over ${Number(p.feeDecayMin ?? 3)} min`],
    ['Creator fee share', `${Number(p.creatorFeePct ?? 50)}%`],
    ['Graduated LP locked', `${Number(p.lockedLpPct ?? 100)}%`],
    ['Supply', Number(p.supply || 1e9).toLocaleString('en-US')],
    ...(Number(p.poolCreationFeeSol) > 0 ? [['Launch toll', `${Number(p.poolCreationFeeSol)} SOL (you pay it; 90% lands back at the fee claimer)`]] : []),
  ];
}

export function receiptLinks(kind, mint, signature) {
  return [
    ...(kind === 'pump' ? [['pump.fun', `https://pump.fun/coin/${mint}`]] : []),
    ['FEELESS coin page', `/terminal/coin/solana/${mint}`],
    ['Solscan token', `https://solscan.io/token/${mint}`],
    ['Launch tx', `https://solscan.io/tx/${signature}`],
    ['DexScreener', `https://dexscreener.com/solana/${mint}`],
  ];
}

export function coinErrors(f, { maxDevBuySol = 50 } = {}) {
  const e = {};
  if (!f.name?.trim() || f.name.trim().length > 32) e.name = 'Name, up to 32 characters.';
  if (!/^[A-Za-z0-9$]{1,10}$/.test(f.symbol?.trim() || '')) e.symbol = 'Ticker: 1–10 letters or numbers.';
  if (!f.imageUrl) e.imageUrl = 'Upload the coin image.';
  if (f.website?.trim() && !/^https:\/\/\S+$/.test(f.website.trim())) e.website = 'Full https:// link.';
  if (f.twitter?.trim() && !/^(https:\/\/(x|twitter)\.com\/[A-Za-z0-9_]{1,15}\/?|@?[A-Za-z0-9_]{1,15})$/i.test(f.twitter.trim())) e.twitter = '@handle or x.com link.';
  if (f.telegram?.trim() && !/^(https:\/\/t\.me\/[A-Za-z0-9_+]{3,}\/?|@?[A-Za-z0-9_]{3,32})$/i.test(f.telegram.trim())) e.telegram = '@group or t.me link.';
  const buy = Number(f.devBuy || 0);
  if (!(buy >= 0) || buy > maxDevBuySol) e.devBuy = `First buy 0–${maxDevBuySol}.`;
  return e;
}

export const socialLink = (kind, v) => { const t = String(v || '').trim(); if (!t || /^https:\/\//i.test(t)) return t; const h = t.replace(/^@/, ''); return kind === 'twitter' ? `https://x.com/${h}` : `https://t.me/${h}`; };

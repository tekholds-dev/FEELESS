import React, { useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';
import { investigate } from './CaseFile';

// Coin passport: one strip that answers "is this coin safe to touch?" from the same cited checks the
// verification engine and case files use. Click any chip for the full case file.
const RAIL = { pumpfun: '💊 Pump.fun curve', pumpswap: '💊 Pump.fun → PumpSwap', 'meteora': '🌊 Meteora', 'dynamic-bonding-curve': '🌊 Meteora curve', raydium: '☀ Raydium', 'raydium-launchlab': '☀ LaunchLab', orca: '🐋 Orca' };

export function CoinPassport({ pair }) {
  const mint = pair?.chainId === 'solana' ? pair?.baseToken?.address : null;
  const [r, setR] = useState(null);
  useEffect(() => {
    if (!mint) return undefined;
    let alive = true; setR(null);
    fetch(apiUrl(`/api/reputation/verify/${mint}`)).then(x => (x.ok ? x.json() : null)).then(d => alive && setR(d)).catch(() => {});
    return () => { alive = false; };
  }, [mint]);
  if (!mint) return null;
  const gate = k => r?.gates?.find(g => g.key === k)?.pass;
  const check = k => r?.checks?.find(c => c.key === k)?.pass;
  const chips = !r ? [['…', 'Reading passport', '']] : !Array.isArray(r.gates) ? [['○', 'Passport unavailable right now', 'dim']] : [
    [r.level === 'gold' ? '✦' : r.level === 'verified' ? '✓' : r.level === 'revoked' ? '✕' : '○', r.level === 'gold' ? 'FEELESS verified' : r.level === 'verified' ? `Verified ${r.score}` : r.level === 'revoked' ? 'Revoked' : `Unverified · ${r.score}`, r.level === 'gold' ? 'gold' : r.level === 'verified' ? 'ok' : r.level === 'revoked' ? 'bad' : 'dim'],
    ['', RAIL[String(pair.dexId || '').toLowerCase()] || `🔁 ${pair.dexId || 'DEX'}`, 'dim'],
    [check('lp') ? '🔒' : '🔓', check('lp') ? 'LP locked' : 'LP not locked', check('lp') ? 'ok' : 'warn'],
    [gate('mint') && gate('freeze') ? '✓' : '!', gate('mint') && gate('freeze') ? 'Mint + freeze revoked' : 'Authority live', gate('mint') && gate('freeze') ? 'ok' : 'bad'],
    [gate('creator') ? '✓' : '⚠', gate('creator') ? 'Creator clean' : 'Creator flagged', gate('creator') ? 'ok' : 'bad'],
    [check('top10') ? '✓' : '!', check('top10') ? 'Holders spread' : 'Top-heavy holders', check('top10') ? 'ok' : 'warn'],
  ];
  return <button type="button" className="coin-passport" data-testid="coin-passport" onClick={() => investigate(mint)} title="Open the full case file">
    <small>PASSPORT</small>{chips.map(([ic, t, tone]) => <span key={t} className={`cp-chip ${tone}`}>{ic && <i>{ic}</i>}{t}</span>)}<em>case file →</em></button>;
}

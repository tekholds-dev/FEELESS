import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { AutoRangePicker } from './AutoRangeDesk';
import { usePools, PoolHub } from './PoolHub';
import { NightVault } from './NightVault';
import { PriceGaps } from './PriceGaps';
import { FirstTips } from './FirstTips';
import '../styles/launchModes.css';

// 🚀 LAUNCH › COIN | POOLS (owner 2026-10-26: "Launch should start on coin but a switch btn for pools with amazing realtime $ ranging before
// signing"). COIN = the launch flow as it is; POOLS = the AutoRange engine on the busiest concentrated pools — pick $, see the band, the replay
// and the next move BEFORE any signature. The mode rides the URL (?mode=pools) so a refresh or a shared link keeps it.
// 🧺 POOLS = everything that puts money to work, one tab each (owner 2026-10-30: Familia's pools, Night Vault and price gaps here too)
const POOL_TABS = [['range', '🤖 AUTORANGE', 'The busiest bands — the engine ranges it before you sign'], ['pools', '🌊 ALL POOLS', 'Every Solana pool, safe to risky — compound in any of them'],
  ['vault', '🌙 NIGHT VAULT', 'Stake, stable, auto-compound and loops — what $ earns while you sleep'], ['gaps', '⚡ PRICE GAPS', 'The same coin priced differently across pools, live']];
export function LaunchModes({ children }) {
  const [params, setParams] = useSearchParams(); const mode = params.get('mode') === 'pools' ? 'pools' : 'coin';
  const hub = usePools();
  const tab = POOL_TABS.some(t => t[0] === params.get('tab')) ? params.get('tab') : 'range';   // 🧺 one panel at a time (owner: "not too scroll heavy")
  const setTab = t => { const p = new URLSearchParams(params); p.set('mode', 'pools'); p.set('tab', t); setParams(p, { replace: true }); };
  const go = m => { const p = new URLSearchParams(params); if (m === 'coin') p.delete('mode'); else p.set('mode', m); setParams(p, { replace: true }); };
  return <div className={`lm is-${mode}`} data-testid="launch-modes">
    <div className="lm-switch" role="tablist" aria-label="Launch">{[['coin', '🚀 LAUNCH A COIN', 'Pump · Raydium · FEELESS — make the coin'], ['pools', '🤖 POOLS · AUTORANGE', 'Put $ into the busiest bands — the engine ranges it']].map(([k, l, tip]) =>
      <button key={k} type="button" role="tab" aria-selected={mode === k} className={mode === k ? 'is-on' : ''} onClick={() => go(k)} data-tip={tip} data-testid={`lm-${k}`}><b>{l}</b><small>{tip}</small></button>)}
      <i className="lm-glow" aria-hidden="true" /></div>
    {mode === 'pools' ? <div className="lm-pools">
      <nav className="m-seg lm-tabs" role="tablist" aria-label="Pools">{POOL_TABS.map(([k, l, tip]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''}
        onClick={() => setTab(k)} data-tip={tip} data-testid={`lm-tab-${k}`}>{l}</button>)}</nav>
      <FirstTips id="launch-pools" tips={[['[data-testid="lm-tab-range"]', 'AutoRange', 'See the band, the replay and the next move before you sign anything.'],
        ['[data-testid="lm-tab-pools"]', 'All pools', 'Every Solana pool — filter SAFE to RISKY, sort by yield.'], ['[data-testid="lm-tab-vault"]', 'Night Vault', 'Stake, stables, auto-compound and loops: what $ earns while you sleep.'],
        ['[data-testid="lm-tab-gaps"]', 'Price gaps', 'The same coin priced differently across pools — only the ones that beat their costs count.']]} />
      <div className="lm-panel" key={tab}>
        {tab === 'range' ? <AutoRangePicker pools={hub?.pools} title="🤖 RANGE BEFORE YOU SIGN · THE BUSIEST BANDS" />
          : tab === 'pools' ? (hub ? <PoolHub pools={hub} compact /> : <p className="m-dim">Reading every pool…</p>)
          : tab === 'vault' ? <NightVault bare /> : <PriceGaps />}</div></div> : children}
  </div>;
}

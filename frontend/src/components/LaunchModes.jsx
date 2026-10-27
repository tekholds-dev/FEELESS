import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { AutoRangePicker } from './AutoRangeDesk';
import { usePools } from './PoolHub';
import '../styles/launchModes.css';

// 🚀 LAUNCH › COIN | POOLS (owner 2026-10-26: "Launch should start on coin but a switch btn for pools with amazing realtime $ ranging before
// signing"). COIN = the launch flow as it is; POOLS = the AutoRange engine on the busiest concentrated pools — pick $, see the band, the replay
// and the next move BEFORE any signature. The mode rides the URL (?mode=pools) so a refresh or a shared link keeps it.
export function LaunchModes({ children }) {
  const [params, setParams] = useSearchParams(); const mode = params.get('mode') === 'pools' ? 'pools' : 'coin';
  const hub = usePools();
  const go = m => { const p = new URLSearchParams(params); if (m === 'coin') p.delete('mode'); else p.set('mode', m); setParams(p, { replace: true }); };
  return <div className={`lm is-${mode}`} data-testid="launch-modes">
    <div className="lm-switch" role="tablist" aria-label="Launch">{[['coin', '🚀 LAUNCH A COIN', 'Pump · Raydium · FEELESS — make the coin'], ['pools', '🤖 POOLS · AUTORANGE', 'Put $ into the busiest bands — the engine ranges it']].map(([k, l, tip]) =>
      <button key={k} type="button" role="tab" aria-selected={mode === k} className={mode === k ? 'is-on' : ''} onClick={() => go(k)} data-tip={tip} data-testid={`lm-${k}`}><b>{l}</b><small>{tip}</small></button>)}
      <i className="lm-glow" aria-hidden="true" /></div>
    {mode === 'pools' ? <div className="lm-pools"><AutoRangePicker pools={hub?.pools} title="🤖 RANGE BEFORE YOU SIGN · THE BUSIEST BANDS" /></div> : children}
  </div>;
}

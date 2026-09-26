import React, { useEffect, useState } from 'react';
import { Hint } from '../Hint';
import { Glyph } from '../Glyph';
import { AnimatedNumber } from '../terminal/AnimatedNumber';

// Live counts of what FEELESS has caught on-chain — refreshed every 20s.
export function LiveIntelStats() {
  const [s, setS] = useState(null);
  useEffect(() => {
    let alive = true;
    const load = () => fetch('/api/reputation/stats').then(r => r.json()).then(d => alive && setS(d)).catch(() => {});
    load(); const t = setInterval(load, 20000);
    return () => { alive = false; clearInterval(t); };
  }, []);
  const cells = [['snipers', 'Sniper wallets marked', 'bad', 'target'], ['bundlers', 'Bundled wallets marked', 'bad', 'bundle'], ['blocklisted', 'Blocklisted', 'bad', 'ban'], ['mintsScanned', 'Coins scanned', 'mint', 'scan'], ['creators', 'Creators tracked', 'mint', 'person'], ['trustedCreators', 'Trusted creators', 'mint', 'shield'], ['flaggedCreators', 'Flagged creators', 'gold', 'shield']];
  return <section className="live-intel" data-testid="live-intel-stats">
    <div className="li-head"><h2 className="live-gradient-text">FEELESS is watching <Hint text="Counts come from real launch transactions: snipers bought within ~1s of launch, bundlers were funded together and bought in the same block." /></h2><span><i className="flr-dot" /> live · on-chain evidence only</span></div>
    <div className="li-grid">{cells.map(([k, label, tone, icon]) => <div key={k} className={`li-cell tone-${tone}`}><Glyph name={icon} tone={tone === 'bad' ? 'rose' : tone === 'gold' ? 'gold' : 'mint'} size={22} /><b>{s ? <AnimatedNumber value={s[k]} format={v => Math.round(v).toLocaleString()} /> : '—'}</b><small>{label}</small></div>)}</div>
    <p className="wp-bio">Snipers bought within ~1 second of launch; bundlers were funded together and bought in the same block. Wallets with repeated strikes are blocklisted, and FEELESS launches can block them. Every count comes from real transactions.</p>
  </section>;
}

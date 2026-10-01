import React from 'react';
import { useTraderId } from '../lib/traderIds';

// 🪪 One trader chip, sitewide: ⚛️ Fuse score · 🥇 medals · ⚔ W-L. Tap → their trader page (profile). Every number comes
// from FEELESS's own verified Fuse records (bots score 0). Shared poller: lib/traderIds.js.
// In-app navigation without a router dependency: push + popstate (the app's router listens to it).
export const openProfile = a => { window.history.pushState({}, '', `/terminal/profile/${a}`); window.dispatchEvent(new PopStateEvent('popstate')); };

export function TraderChip({ address, compact }) {
  const id = useTraderId(address);
  if (!address) return null;
  const m = id?.medals || {}; const gold = Number(m['1'] || 0); const any = gold + Number(m['2'] || 0) + Number(m['3'] || 0);
  const b = id?.battles || {};
  const tip = id ? `⚛️ Fuse score ${id.score ?? 0}/100 · ${any} season medal${any === 1 ? '' : 's'} · battles ${b.w || 0}W ${b.l || 0}L${id.catWins ? ` · beat FeeCat ×${id.catWins}` : ''} — open trader page`
    : 'Open trader page';
  return <button type="button" className={`tchip ${id ? '' : 'is-ghost'} ${compact ? 'is-compact' : ''}`} onClick={e => { e.preventDefault(); e.stopPropagation(); openProfile(address); }} data-tip={tip} data-testid={`tchip-${address}`}>
    <i>⚛️</i><b className="m-num">{id ? id.score ?? 0 : '··'}</b>
    {any > 0 && <span>{gold ? '🥇' : '🏅'}{any}</span>}
    {!compact && (b.w || b.l) ? <em>⚔ {b.w || 0}-{b.l || 0}</em> : null}
  </button>;
}

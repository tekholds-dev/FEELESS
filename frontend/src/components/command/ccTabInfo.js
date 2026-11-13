import React from 'react';
import { Ic3 } from '../../lib/icon3d';
import { useCountUp } from '../../lib/useCountUp';
import '../../styles/hqVitals.css';

// 🫙 one empty state for every HQ list (owner 2026-11-11: pages were a form row over blank space): what goes here and how it fills
export function HqEmpty({ ic, title, line }) {
  return <div className="cc-emptycard" role="status"><i aria-hidden="true"><Ic3 e={ic} /></i><b>{title}</b><small>{line}</small></div>;
}

// One clear line per HQ tab: what it is, what you do there. Rendered as the tab's header.
export const TAB_INFO = {
  launch: ['Launch & setup', 'Hook up keys, then sign the one-time launch config. Everything launchable is mapped here.', ['Launch map', 'Presets', 'Readiness check']],
  fees: ['Trading & fees', 'The FEELESS fee on every trade: rate, engine, fee accounts and live earnings.', ['Fee %', 'Engine', 'Fee accounts']],
  latency: ['Lag catcher', 'What real visitors feel: slow routes, janky pages, and the fix for each.', ['Speed score', 'Lite effects', 'Fix list']],
  nfts: ['NFTs', 'Your cards as Solana collections on Metaplex Core, Crossmint or Underdog, dropped to any wallets or to everyone holding the card.', ['Create collection', 'Drop to holders']],
  money: ['Money', 'Every FEELESS wallet in one place: fee accounts + splits, the season reserve and badge pools, and Circle wallets. One live pulse feeds it all.', ['Treasury & splits', 'Reserve & badge pools', 'Circle wallets']],
  numbers: ['Numbers', 'Growth at a glance: users, trades, volume, retention.', []],
  traffic: ['Traffic', 'Where visitors come from and which pages they use.', []],
  pulse: ['Pulse', 'Live activity across chat, calls and trades.', []],
  marketing: ['Marketing', 'Shareable FeeCat posts and GIFs built from real trades.', ['Posts', 'GIFs']],
  kols: ['KOLs', 'Callers ranked by what their calls actually did.', []],
  invites: ['Invites', 'Referral codes and who they brought in.', []],
  ads: ['Ads', 'Sponsored slots and what they earn.', []],
  ideas: ['Ideas', 'Feature ideas from the community.', []],
  holders: ['Holders', 'Every holder of your coins. Select wallets to airdrop or badge.', ['Select', 'Airdrop', 'Badge']],
  studio: ['Airdrop Studio', 'Build a drop, simulate it, send from your wallet.', []],
  airdrops: ['Scheduled drops', 'Drops waiting to go out, and their on-chain receipts.', []],
  snapshots: ['Snapshots', 'Freeze a holder list at a moment in time.', []],
  badges: ['Badges', 'Award badges and decide what % of which pool each badge earns.', ['Reserve pool', 'Badge × pool matrix', 'Award']],
  seasons: ['Seasons', 'Season themes, weeks, prizes and the reserve wallet.', []],
  familia: ['Familia control center', 'Run the game: plot prices, Fee City multiplier, turf cap, Family Fuse minimum (live now) and the real-money prices (applied after the custody pick).', ['Economy', 'Rules', 'Paid-hit math']],
  pools: ['Pools', 'Create a locked TOKEN/SOL pool for a token that already exists.', ['Create pool', 'Verify pool']],
  feecat: ['Fee 🐱', "FeeCat's trading brain: rules, what she's learning, and her results.", ['Brain', 'Lessons', 'Book']],
  broadcast: ['Broadcast', 'Message everyone at once (site banner / push).', []],
  investigate: ['Intel desk', 'The reputation department: ruggers, snipers, bundlers, their funders and crews, with each one\'s likely next move. FeeCat and the rug shield read the same database.', []],
  looks: ['Looks', 'Pick how all of FEELESS looks: Plasma, the free looks and the advanced ones holders unlock.', ['Preview', 'Save']],
  verify: ['Verify coins', 'Run the verification checks, grant the gold check or revoke one.', ['Run checks', 'Grant', 'Revoke']],
  overview: ['Security', 'Platform health, keys and risks at a glance.', []],
  war: ['War Room', 'Live attacks on FEELESS, decoys + canaries, auto-hardening, on-chain tracing and the bounty — all in one place.', []],
  mod: ['Moderation', 'Reports, mutes and the blocklist.', []],
  access: ['Access', 'Who can open this HQ.', []],
  bugs: ['Bugs', 'Crash reports and bug tickets, newest first.', []],
};

// 📟 one live vitals band for every HQ tab (owner 2026-11-11: 18 tabs were bare text panels): each tile is a ring filled by value / of, or a spark
// of a real series, and its number counts up when it changes. Real numbers only: a tile with no value says "—" and draws an empty ring.
const kfmt = n => (Math.abs(n) >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : Math.abs(n) >= 1e4 ? `${(n / 1e3).toFixed(1)}K` : n.toLocaleString());
function HqTile({ t, i }) {
  const raw = Number(t.value); const has = t.value != null && Number.isFinite(raw); const n = useCountUp(has ? raw : 0);
  const pct = has && t.of ? Math.max(0, Math.min(1, raw / t.of)) : has && !t.spark ? 1 : 0; const C = 2 * Math.PI * 16;
  const sp = (t.spark || []).map(Number).filter(Number.isFinite); const mx = Math.max(1, ...sp);
  return <div className={`hqv-t is-${t.tone || 'violet'}`} style={{ '--i': i }} data-tip={t.tip || t.label} data-testid="hq-vital">
    {sp.length > 1 ? <svg className="hqv-spark" viewBox="0 0 60 36" aria-hidden="true"><polyline points={sp.map((v, k) => `${(k / (sp.length - 1)) * 60},${34 - (v / mx) * 30}`).join(' ')} /></svg>
      : <svg className="hqv-ring" viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="16" className="bg" /><circle cx="20" cy="20" r="16" className="fg" style={{ strokeDasharray: `${C * pct} ${C}` }} /></svg>}
    <span><b className="m-num" key={has ? raw : 'x'}>{has ? `${t.pre || ''}${t.dec ? raw.toFixed(t.dec) : kfmt(n)}${t.unit || ''}` : '—'}</b><small>{t.label}{t.of ? <em> / {kfmt(t.of)}</em> : null}</small></span></div>;
}
export function HqVitals({ tiles }) {
  return <div className="hqv" data-testid="hq-vitals"><i className="hqv-sweep" aria-hidden="true" />{tiles.map((t, i) => <HqTile key={t.label} t={t} i={i} />)}</div>;
}

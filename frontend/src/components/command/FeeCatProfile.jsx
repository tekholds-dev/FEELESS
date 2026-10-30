import React, { useEffect, useState } from 'react';
import EcosystemChat from '../EcosystemChat';
import '../../styles/feeWall.css';
import { toast } from 'sonner';
import { PnlCard } from './MetaPanels';
import { ShareGifButton } from '../ShareGif';
import { useLeaderProfile } from '../../lib/feeLeader';
import { currentSubscription, enablePush, readPushPrefs, savePushPrefs, syncPush } from '../../lib/push';

const sol = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(4)} SOL`);
const ago = ts => { const m = Math.floor((Date.now() / 1000 - ts) / 60); return m < 60 ? `${m}m` : m < 1440 ? `${Math.floor(m / 60)}h` : `${Math.floor(m / 1440)}d`; };

// Fee the Leader cat's full profile: live book, every trade, what happened after each sell, and how it's learning.
// Fee's trades as shareable FeeCat GIFs (paw prints + blinking eyes); losses get the crimson palette.
const feeCard = t => {
  const up = t.type === 'BUY' || (t.pnlSol ?? 0) >= 0;
  const sym = (t.detail.match(/\b(?:of|Sold(?: \d+% of)?)\s+\$?([A-Z0-9]{2,12})\b/) || [])[1] || 'the trenches';
  return { mascot: 'feecat', tone: up ? 'up' : 'down', kicker: `FEECAT ${t.type === 'BUY' ? 'BUYS' : 'SELLS'} · PAPER · LIVE PRICES`, title: `$${sym}`,
    big: t.pnlSol != null ? `${t.pnlSol >= 0 ? '+' : ''}${t.pnlSol.toFixed(3)} SOL` : t.type === 'BUY' ? 'ENTERED' : 'EXITED', lines: [t.detail.slice(0, 64), t.detail.slice(64, 128)].filter(Boolean), footer: 'feeless · fee the cat trades out loud' };
};
const exitCard = e => ({ mascot: 'feecat', tone: e.peakAfter >= 40 ? 'down' : 'up', kicker: 'FEECAT · AFTER THE SELL', title: `$${e.symbol}`,
  big: `${e.changeAtExit >= 0 ? '+' : ''}${e.changeAtExit}%`, lines: [`Sold: ${e.why}`.slice(0, 60), `After: best +${e.peakAfter}% · low ${e.lowAfter}%`, e.peakAfter >= 40 ? '🧠 Lesson learned: give runners room' : '✅ The exit held up'], footer: 'feeless · she learns from every sell' });

// 🔔 follow Fee = a push every time she trades (lives in the stage hero; the FeeCat tower in Familia shows it too)
export function FollowFee() {
  const [following, setFollowing] = useState(() => Boolean(readPushPrefs().followFee));
  const follow = async () => {
    const prefs = { ...readPushPrefs(), followFee: !following };
    try {
      let wl = []; try { wl = JSON.parse(localStorage.getItem('feeless-watchlist') || '[]'); } catch { /* ignore */ }
      if (await currentSubscription()) await syncPush(wl, prefs); else await enablePush(wl, prefs);
      savePushPrefs(prefs); setFollowing(!following);
      toast.success(!following ? '🐱 You\'ll get a push every time Fee trades.' : 'Stopped following Fee.');
    } catch (e) { toast.error(e.message); }
  };
  return <button type="button" className={`fcp-follow ${following ? 'is-on' : ''}`} data-testid="follow-fee" onClick={follow} aria-pressed={following}
    data-tip={following ? 'You get a push every time Fee trades — tap to stop' : 'Get a push every time Fee buys or sells (copy her alerts)'}>{following ? '✓ FOLLOWING FEE' : '🔔 FOLLOW FEE'}</button>;
}

// 🐱 Fee's book under the live desk (2026-10-23 redo: her name / balance / win-rate header lived here AND in the stage — the stage keeps them;
// the panther picker moved to 🎨 Build a cat; her learning moved to 🧠 Her brain): open trades, her wall, every trade, what happened after each sell.
export function FeeCatProfile({ catId = 'leader' }) {
  const shared = useLeaderProfile(catId === 'leader');
  const [own, setOwn] = useState(null);
  const [tab, setTab] = useState('wall');
  useEffect(() => {
    if (catId === 'leader') return undefined; let alive = true;
    const load = () => fetch(`/api/cats/${catId}/profile`).then(r => r.json()).then(x => alive && setOwn(x)).catch(() => {});
    load(); const t = setInterval(() => { if (!document.hidden) load(); }, 20000);
    return () => { alive = false; clearInterval(t); };
  }, [catId]);
  const d = catId === 'leader' ? shared : own;
  if (!d) return <section className="fcp" data-testid="feecat-profile"><p className="wp-bio">Loading Fee…</p></section>;
  const c = d.cat || {};
  return <section className="fcp" data-testid="feecat-profile">
    {c.positions?.length > 0 && <div className="fcp-open"><h4>Open now</h4>{c.positions.map(p => <a key={p.pairAddress} className="fcp-pos" href={`/terminal/chat?chain=solana&pair=${p.pairAddress}&room=bulls`} target="_blank" rel="noopener noreferrer">
      <b>${p.symbol}</b><span className={p.currentChange >= 0 ? 'positive' : 'negative'}>{p.currentChange >= 0 ? '+' : ''}{Number(p.currentChange).toFixed(1)}%</span><em className="fcp-mirror" onClick={e => { e.preventDefault(); window.location.href = `/terminal/chat?chain=solana&pair=${p.pairAddress}&room=bulls`; }}>Mirror this trade →</em><small>{Number(p.costSol).toFixed(2)} SOL · peak +{Number(p.peakChange || 0).toFixed(1)}%{p.scaled ? ' · runner' : ''}{p.conviction ? ` · ${p.conviction}×` : ''}</small></a>)}</div>}
    <nav className="fcp-tabs m-seg" role="tablist" aria-label="Fee's book">{[['wall', '💬 Her wall', null], ['trades', '📈 Every trade', (d.trades || []).length], ['after', '👀 After the sell', (d.exits || []).length]].map(([k, l, n]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-testid={`fcp-tab-${k}`}>{l}{n ? <em>{n}</em> : null}</button>)}</nav>
    {tab === 'wall' && <div className="fcp-wall" data-testid="fee-wall"><details className="fee-wall-pin" data-testid="fee-wall-pin"><summary><b>📌 What Fee does</b><span>trades like a desk · calls every buy · trench report every 30 min</span></summary>
        <ul><li data-testid="feecat-crowd-edge"><b>🧠 Learns from users</b> — every 10 min FEELESS scores its traders on their verified buys (≥24h old); the proven ones are "elite". When elites buy a coin she leans in a little (≤×1.15) and files it in her memory, so following them only keeps its weight if it actually wins.</li>
          <li data-testid="feecat-fuse-edge"><b>⚛️ Fuse edge</b> — skips any coin the Fuse runner gates already failed (the gate is her reason), gives a small boost (≤×1.2) to coins several Fuse sources agree on, and her setup memory learns whether Fuse-backed entries actually pay. Never while discipline is cutting her size.</li>
          <li><b>Trades the trenches like a stock desk</b> — starter size, adds on healthy dips to lower her average, holds while liquidity, volume and buyers hold, takes profit in pieces, cuts only when the thesis breaks. Paper trades on live prices.</li>
          <li><b>Calls every buy</b> in the coin's chat and on Live Calls, with the reasons — so her record is public.</li>
          <li><b>Posts a trench report here every ~30 min</b>: the board's bangers and why, the Degen Weather, SOL, and her book.</li></ul>
        <small>Posting here is signed by your wallet (free, no transaction) — nobody can post as you. FEELESS never asks for your seed phrase or private key; anyone who does is a scammer. Keep calls to a coin's contract address, not links.</small></details><EcosystemChat compact window={10} room="wall-FEE-LEADER-CAT" ecosystem={{ id: 'wall-FEE-LEADER-CAT', name: "Fee's wall" }} /></div>}
    {tab === 'trades' && <div className="fcp-list">{!(d.trades || []).length ? <p className="wp-bio">No trades yet.</p> : (d.trades || []).map(t => <div key={t.id} className={`fcp-trade t-${t.type.toLowerCase()}`}><em>{t.type}</em>{t.pnlSol != null && <b className={`fcp-result ${t.pnlSol >= 0 ? 'win' : 'loss'}`}>{t.pnlSol >= 0 ? 'WIN' : 'LOSS'} {t.pnlSol >= 0 ? '+' : ''}{t.pnlSol.toFixed(4)}</b>}<p>{t.detail}</p><small>{ago(t.ts / 1000)} ago{t.pnlSol != null ? ` · ${sol(t.pnlSol)}` : ''}</small><ShareGifButton className="fcp-share" label="🎞" card={feeCard(t)} /></div>)}</div>}
    {tab === 'after' && <div className="fcp-list">{!(d.exits || []).length ? <p className="wp-bio">No exits yet.</p> : (d.exits || []).map(e => <a key={`${e.pairAddress}-${e.exitAt}`} className={`fcp-exit ${e.peakAfter >= 40 ? 'missed' : ''}`} href={`/terminal/chat?chain=solana&pair=${e.pairAddress}&room=bulls`} target="_blank" rel="noopener noreferrer">
      <b>${e.symbol}</b><span>sold {e.changeAtExit >= 0 ? '+' : ''}{e.changeAtExit}% · {e.why}</span><span>after: best <b className="positive">+{e.peakAfter}%</b> · low <b className="negative">{e.lowAfter}%</b></span><small>{ago(e.exitAt)} ago{e.peakAfter >= 40 ? ' · 🧠 lesson: sold a runner' : ''}</small><ShareGifButton className="fcp-share" label="🎞" card={exitCard(e)} /></a>)}{(d.exits || [])[0] && <PnlCard symbol={(d.exits || [])[0]?.symbol} pnlPct={(d.exits || [])[0]?.changeAtExit} pnlSol={(d.exits || [])[0]?.pnlSol} note={(d.exits || [])[0]?.why} />}</div>}
  </section>;
}

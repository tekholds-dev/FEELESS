import React, { useEffect, useState } from 'react';
import EcosystemChat from '../EcosystemChat';
import '../../styles/feeWall.css';
import { toast } from 'sonner';
import { ShareGifButton } from '../ShareGif';
import { useLeaderProfile } from '../../lib/feeLeader';
import { currentSubscription, enablePush, readPushPrefs, savePushPrefs, syncPush } from '../../lib/push';

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
// 💜 her wall's live sides (owner 2026-10-30: "more vital live animations beside — not text heavy"): left = how she is right now, right = her last calls
export function WallVitals({ d, side }) {
  const c = d?.cat || {}; const disc = d?.discipline || {}; const st = d?.stats || {};
  const on = c.status === 'running' && !disc.pause; const wr = Number(c.winRate ?? disc.winRate ?? 0); const lives = Number(disc.lives ?? 9);
  if (side === 'l') return <aside className="fw-side" data-testid="fw-vitals">
    <span className={`fw-state${on ? ' is-on' : ''}`}><i />{on ? 'HUNTING' : 'NAPPING'}</span>
    <span className="fw-ring" style={{ '--p': Math.max(0, Math.min(100, wr)) / 100 }}><svg viewBox="0 0 44 44" aria-hidden="true"><circle cx="22" cy="22" r="18" /><circle className="a" cx="22" cy="22" r="18" /></svg><b>{Math.round(wr)}%</b><small>WON</small></span>
    <span className="fw-meter"><em>OPEN</em><b key={(c.positions || []).length}>{(c.positions || []).length}</b><i><u style={{ transform: `scaleX(${Math.min(1, (c.positions || []).length / 5)})` }} /></i></span>
    <span className="fw-meter"><em>ROI</em><b className={Number(st.roiPct) < 0 ? 'is-dn' : 'is-up'}>{st.roiPct != null ? `${st.roiPct > 0 ? '+' : ''}${st.roiPct}%` : '—'}</b><i><u className={Number(st.roiPct) < 0 ? 'is-dn' : ''} style={{ transform: `scaleX(${Math.min(1, Math.abs(Number(st.roiPct) || 0) / 20)})` }} /></i></span>
    <span className="fw-lives" aria-label={`${lives} of 9 lives`}>{Array.from({ length: 9 }, (_, i) => <i key={i} className={i < lives ? 'on' : ''} style={{ '--i': i }} />)}</span>
  </aside>;
  const calls = (d?.trades || []).slice(0, 5);
  return <aside className="fw-side" data-testid="fw-calls"><em className="fw-h">HER LAST CALLS</em>
    {calls.length ? calls.map((t, i) => <span key={t.id || i} className={`fw-call is-${String(t.type || '').toLowerCase()}`} style={{ '--i': i }}><b>{t.type}</b><span>${t.symbol || String(t.detail || '').match(/\bof\s+\$?([A-Z0-9_]{2,})/i)?.[1] || String(t.detail || '').match(/^Sold\s+\$?([A-Z0-9_]{2,})/i)?.[1] || '—'}</span>{t.pnlSol != null ? <em className={t.pnlSol < 0 ? 'is-dn' : 'is-up'}>{t.pnlSol > 0 ? '+' : ''}{Number(t.pnlSol).toFixed(3)}</em> : null}</span>)
      : <span className="fw-call">waiting for her next call</span>}
  </aside>;
}

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

// 📈 HER BOOK, readable in 5 seconds (owner 2026-10-31 redo: "Every trade / After the sell" were paragraph walls): a summary strip with the
// won/lost meter + her P&L curve, then one row per trade — side · coin · why (one line, the full note on hover) · P&L bar · age
const symOf = t => t.symbol || (String(t.detail || '').match(/\b(?:of|Sold(?: \d+% of)?)\s+\$?([A-Za-z0-9_]{2,14})\b/) || [])[1] || '—';
const whyOf = t => { const d = String(t.detail || ''); const w = d.split(/ — |: /).slice(1).join(' — ').split(/(?<=[a-z%)])[.;] /)[0]; return (w || d).replace(/\s*\((?:fees apart|paper|\d+ min ago)[^)]*\)\.?/g, '').slice(0, 120); };
const cap$ = v => (v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${Math.round(v / 1e3)}K` : `$${Math.round(v)}`);
export function TradeBook({ trades = [] }) {
  const sells = trades.filter(t => t.pnlSol != null); const won = sells.filter(t => t.pnlSol >= 0).length;
  const max = Math.max(1e-9, ...sells.map(t => Math.abs(t.pnlSol)));
  let run = 0; const curve = [0, ...sells.slice().reverse().map(t => (run += t.pnlSol))];
  const lo = Math.min(...curve); const span = (Math.max(...curve) - lo) || 1; const y = v => 29 - ((v - lo) / span) * 27;
  if (!trades.length) return <p className="wp-bio">No trades yet.</p>;
  return <div className="fcp-book" data-testid="fcp-book">
    <header className="fcp-sum">
      <span><em>CLOSED</em><b className="m-num sm">{sells.length}</b></span>
      <span className="fcp-wl" data-tip={`${won} wins · ${sells.length - won} losses`}><em>WON · LOST</em><b className="m-num sm">{won} · {sells.length - won}</b><i><u style={{ transform: `scaleX(${sells.length ? won / sells.length : 0})` }} /></i></span>
      <span><em>NET · PRICE MOVES</em><b className={`m-num sm ${run < 0 ? 'is-dn' : 'is-up'}`} key={run.toFixed(4)}>{run >= 0 ? '+' : ''}{run.toFixed(3)} SOL</b></span>
      <svg className={`fcp-curve${run < 0 ? ' is-dn' : ''}`} viewBox="0 0 100 30" preserveAspectRatio="none" role="img" aria-label="Her running P&L, oldest to newest" data-tip="Her running P&L across these sells, oldest → newest (fees apart)">
        <line x1="0" x2="100" y1={y(0)} y2={y(0)} /><polyline points={curve.map((v, i) => `${(i / Math.max(1, curve.length - 1)) * 100},${y(v)}`).join(' ')} /></svg>
    </header>
    <ol className="fcp-list">{trades.map((t, i) => { const up = (t.pnlSol ?? 0) >= 0;
      return <li key={t.id} className={`fcp-trade t-${String(t.type).toLowerCase()}`} style={{ '--i': Math.min(i, 12) }} data-tip={t.detail}>
        <em>{t.type}</em><b className="fcp-sym">${symOf(t)}</b><span className="fcp-why">{whyOf(t)}</span>
        {t.pnlSol != null ? <span className={`fcp-pnl ${up ? 'is-up' : 'is-dn'}`}><i><u style={{ transform: `scaleX(${Math.abs(t.pnlSol) / max})` }} /></i><b className="m-num">{up ? '+' : ''}{t.pnlSol.toFixed(4)}</b></span>
          : <span className="fcp-pnl"><small>{t.marketCapUsd ? `in @ ${cap$(t.marketCapUsd)}` : 'entered'}</small></span>}
        <small className="fcp-age">{ago(t.ts / 1000)}</small><ShareGifButton className="fcp-share" label="🎞" card={feeCard(t)} /></li>; })}</ol>
  </div>;
}

// 👀 after each sell: one gauge per exit — the low → best the coin did AFTER she sold, her sale pinned at 0 (a runner she left = gold)
export function AfterBook({ exits = [] }) {
  if (!exits.length) return <p className="wp-bio">No exits yet.</p>;
  const held = exits.filter(e => e.peakAfter < 40).length;
  return <div className="fcp-book" data-testid="fcp-after">
    <header className="fcp-sum">
      <span className="fw-ring" style={{ '--p': held / exits.length }} data-tip="Exits where the coin did NOT run +40% after she sold"><svg viewBox="0 0 44 44" aria-hidden="true"><circle cx="22" cy="22" r="18" /><circle className="a" cx="22" cy="22" r="18" /></svg><b>{held}/{exits.length}</b><small>HELD</small></span>
      <span><em>RUNNERS SHE LEFT</em><b className="m-num sm is-warn">{exits.length - held}</b></span>
      <span className="fcp-legend"><i className="dn" />low after<i className="at" />her sale<i className="up" />best after</span>
    </header>
    <ol className="fcp-list">{exits.map((e, i) => { const lo = Math.min(0, Number(e.lowAfter) || 0); const hi = Math.max(0, Number(e.peakAfter) || 0); const s = (hi - lo) || 1; const z = ((0 - lo) / s) * 100; const missed = e.peakAfter >= 40;
      return <li key={`${e.pairAddress}-${e.exitAt}`} className={`fcp-exit${missed ? ' missed' : ''}`} style={{ '--i': Math.min(i, 12) }}>
        <a className="fcp-sym" href={`/terminal/chat?chain=solana&pair=${e.pairAddress}&room=bulls`} target="_blank" rel="noopener noreferrer" data-tip={`Open $${e.symbol} — sold: ${e.why}`}>${e.symbol}</a>
        <span className="fcp-sold"><em>SOLD</em><b className={`m-num ${e.changeAtExit < 0 ? 'is-dn' : 'is-up'}`}>{e.changeAtExit >= 0 ? '+' : ''}{e.changeAtExit}%</b></span>
        <span className="fcp-range" data-tip={`After she sold: low ${e.lowAfter}% · best +${e.peakAfter}%`}><i className="dn" style={{ left: 0, width: `${z}%` }} /><i className="up" style={{ left: `${z}%`, width: `${100 - z}%` }} /><s style={{ left: `${z}%` }} />
          <small style={{ left: 0 }}>{e.lowAfter}%</small><small style={{ right: 0 }}>+{e.peakAfter}%</small></span>
        <em className={`m-chip ${missed ? 'warn' : 'ok'}`}>{missed ? 'SOLD A RUNNER' : 'EXIT HELD'}</em>
        <small className="fcp-age">{ago(e.exitAt)}</small><ShareGifButton className="fcp-share" label="🎞" card={exitCard(e)} /></li>; })}</ol>
  </div>;
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
    {tab === 'wall' && <div className="fw-row"><WallVitals d={d} side="l" /><div className="fcp-wall" data-testid="fee-wall"><details className="fee-wall-pin" data-testid="fee-wall-pin"><summary><b>📌 What Fee does</b><span>trades like a desk · calls every buy · trench report every 30 min</span></summary>
        <ul><li data-testid="feecat-crowd-edge"><b>🧠 Learns from users</b> — every 10 min FEELESS scores its traders on their verified buys (≥24h old); the proven ones are "elite". When elites buy a coin she leans in a little (≤×1.15) and files it in her memory, so following them only keeps its weight if it actually wins.</li>
          <li data-testid="feecat-fuse-edge"><b>⚛️ Fuse edge</b> — skips any coin the Fuse runner gates already failed (the gate is her reason), gives a small boost (≤×1.2) to coins several Fuse sources agree on, and her setup memory learns whether Fuse-backed entries actually pay. Never while discipline is cutting her size.</li>
          <li><b>Trades the trenches like a stock desk</b> — starter size, adds on healthy dips to lower her average, holds while liquidity, volume and buyers hold, takes profit in pieces, cuts only when the thesis breaks. Paper trades on live prices.</li>
          <li><b>Calls every buy</b> in the coin's chat and on Live Calls, with the reasons — so her record is public.</li>
          <li><b>Posts a trench report here every ~30 min</b>: the board's bangers and why, the Degen Weather, SOL, and her book.</li></ul>
        <small>Posting here is signed by your wallet (free, no transaction) — nobody can post as you. FEELESS never asks for your seed phrase or private key; anyone who does is a scammer. Keep calls to a coin's contract address, not links.</small></details><EcosystemChat compact window={10} room="wall-FEE-LEADER-CAT" ecosystem={{ id: 'wall-FEE-LEADER-CAT', name: "Fee's wall" }} /></div><WallVitals d={d} side="r" /></div>}
    {tab === 'trades' && <TradeBook trades={d.trades || []} />}
    {tab === 'after' && <AfterBook exits={d.exits || []} />}
  </section>;
}

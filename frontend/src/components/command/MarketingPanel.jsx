import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { ShareGifButton } from '../ShareGif';
import { apiUrl } from '../../lib/api';

const CATS = [['coins', '🪙 FEELESS coins'], ['feecat', '🐱 FeeCat trades'], ['movers', '🚀 Top movers · 3 days'], ['reps', '🛡 Top reputation']];
const mc = v => (!(v > 0) ? '—' : v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : `$${(v / 1e3).toFixed(1)}K`);
const pct = v => `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(1)}%`;
const coinImg = mint => (mint ? `https://dd.dexscreener.com/ds-data/tokens/solana/${mint}.png` : null);
const link = pa => `${window.location.origin}/terminal/chat?chain=solana&pair=${pa}&room=bulls`;

// FeeCat's paper trades → degen but useful posts: entry, move, size and the rule that fired. Always labelled paper.
export function feecatPosts(cat) {
  const open = (cat?.positions || []).map(p => {
    const ch = Number(p.currentChange) || 0;
    const up = ch >= 0;
    return { key: `o-${p.pairAddress}`, kind: 'open', symbol: p.symbol, mint: p.mint, pair: p.pairAddress, change: ch, up,
      post: `🐱 FeeCat is ${up ? 'riding' : 'holding through the dip on'} $${p.symbol}: ${pct(ch)} since entry at ${mc(p.entryMarketCapUsd)} MC${p.peakChange ? ` (peak ${pct(p.peakChange)})` : ''}. ${p.costSol} SOL paper bag. Why in: ${p.reason || 'passed the live entry rules'}. Chart + chat: ${link(p.pairAddress)} #Solana #memecoins #FEELESS`,
      card: { kicker: `FEECAT TRADE · OPEN · PAPER`, title: `$${p.symbol}`, imageUrl: coinImg(p.mint), mascot: 'feecat', tone: up ? 'up' : 'down', bigValue: Math.abs(ch), bigPrefix: up ? '+' : '−', bigSuffix: '%', bigDigits: 1,
        lines: [`Entry ${mc(p.entryMarketCapUsd)} MC · ${p.costSol} SOL`, p.peakChange ? `Peak ${pct(p.peakChange)} since entry` : 'Fresh entry', (p.reason || 'Live entry rules').slice(0, 58)], footer: 'FeeCat paper trade · feeless' } };
  });
  const closed = [...(cat?.exits || [])].reverse().slice(0, 12).map(e => {
    const ch = Number(e.changeAtExit) || 0;
    const win = (e.pnlSol ?? ch) >= 0;
    return { key: `x-${e.pairAddress}-${e.exitAt}`, kind: 'closed', symbol: e.symbol, pair: e.pairAddress, change: ch, up: win,
      post: win ? `🐱💰 FeeCat closed $${e.symbol} ${pct(ch)} (${Number(e.pnlSol || 0).toFixed(3)} SOL paper). Exit: ${e.why || 'take-profit rule'}. No feelings, just rules. Track every call: ${link(e.pairAddress)} #FEELESS`
        : `🐱🩸 FeeCat cut $${e.symbol} at ${pct(ch)}. Exit: ${e.why || 'stop-loss rule'}. Small L, bag protected: that's the rule. Receipts on FEELESS: ${link(e.pairAddress)} #FEELESS`,
      card: { kicker: `FEECAT TRADE · ${win ? 'WIN' : 'CUT LOSS'} · PAPER`, title: `$${e.symbol}`, mascot: 'feecat', tone: win ? 'up' : 'down', bigValue: Math.abs(ch), bigPrefix: win ? '+' : '−', bigSuffix: '%', bigDigits: 1,
        lines: [`${win ? 'Profit' : 'Loss'} ${Math.abs(Number(e.pnlSol || 0)).toFixed(3)} SOL`, (e.why || (win ? 'Take-profit rule' : 'Stop-loss rule')).slice(0, 58), `Closed ${new Date(e.exitAt * 1000).toLocaleString()}`], footer: 'FeeCat paper trade · feeless' } };
  });
  return { open, closed };
}
const copy = t => navigator.clipboard?.writeText(t).then(() => toast.success('Post text copied')).catch(() => toast.error('Copy failed'));
const short = a => `${a.slice(0, 4)}…${a.slice(-4)}`;

// Marketing: ready-to-post lists with copyable text and an animated GIF card for each row.
export function MarketingPanel({ call }) {
  const [d, setD] = useState(null);
  const [cat, setCat] = useState('feecat');
  const [cat_, setCat_] = useState(null);
  useEffect(() => { call('/admin/marketing').then(setD).catch(e => { toast.error(e.message); setD({}); }); }, [call]);
  useEffect(() => { fetch(apiUrl('/api/cats/leader')).then(r => r.json()).then(x => setCat_(x.cat || {})).catch(() => setCat_({})); }, []);
  const fc = feecatPosts(cat_);
  const fcRow = r => <Row key={r.key} title={`$${r.symbol}`} sub={`${r.kind === 'open' ? 'open' : r.up ? 'win' : 'cut'} · ${pct(r.change)}`} tone={r.up ? 'positive' : 'negative'} img={r.card.imageUrl} post={r.post} card={r.card} />;
  const Row = ({ title, sub, post, card, img, tone }) => <div className="mk-row"><div className="mk-id">{img ? <img src={img} alt="" /> : <span className="mk-dot" />}<b>{title}</b><em className={tone}>{sub}</em></div>
    <p>{post}</p><div className="mk-act"><button type="button" className="btn-outline" onClick={() => copy(post)}>Copy post</button><ShareGifButton card={card} /></div></div>;
  const mover = r => <Row key={r.pairAddress} title={`$${r.symbol}`} sub={`${r.move3d >= 0 ? '+' : ''}${r.move3d}% · 3d`} tone={r.move3d >= 0 ? 'positive' : 'negative'} img={r.imageUrl} post={r.post}
    card={{ kicker: `TOP MOVER · 3 DAYS · ${r.chain.toUpperCase()}`, title: `$${r.symbol}`, imageUrl: r.imageUrl, tone: r.move3d >= 0 ? 'up' : 'down', bigValue: Math.abs(r.move3d), bigPrefix: r.move3d >= 0 ? '+' : '−', bigSuffix: '%', bigDigits: 1, lines: [r.name || '', 'Chart · chat · trade fee-free on FEELESS'] }} />;
  const rep = (r, good) => <Row key={r.address} title={short(r.address)} sub={`${good ? 'trusted' : 'flagged'} · score ${r.score ?? '—'}`} tone={good ? 'positive' : 'negative'} post={r.post}
    card={{ kicker: good ? 'TRUSTED CREATOR · FEELESS REP' : 'FLAGGED CREATOR · FEELESS REP', title: short(r.address), tone: good ? 'up' : 'down', bigValue: r.score ?? 0, bigDigits: 0, bigSuffix: ' rep', lines: [`${r.tokenCount} coins · ${r.bigWinners} big winners`, `${r.dumpedCount} dumps · ${r.ruggedCount} rugs`, 'Check any wallet on FEELESS'] }} />;
  return <section className="cc-panel marketing-panel">
    <nav className="feed-cats">{CATS.map(([id, l]) => <button type="button" key={id} className={cat === id ? 'on' : ''} onClick={() => setCat(id)}>{l}</button>)}</nav>
    {cat === 'coins' ? <FeelessCoins call={call} /> : cat === 'feecat' ? (!cat_ ? <p className="cc-empty">Loading FeeCat's book…</p> : <div className="mk-cols">
      <div><h4>Open trades</h4>{fc.open.length ? fc.open.map(fcRow) : <p className="cc-empty">FeeCat has no open trades right now.</p>}</div>
      <div><h4>Closed · wins green, cuts crimson</h4>{fc.closed.length ? fc.closed.map(fcRow) : <p className="cc-empty">No closed trades yet.</p>}</div>
    </div>) : !d ? <p className="cc-empty">Measuring 3-day moves from FEELESS candles…</p> : cat === 'movers' ? <div className="mk-cols">
      <div><h4>Biggest gainers</h4>{(d.movers?.up || []).map(mover)}</div>
      <div><h4>Biggest drops</h4>{(d.movers?.down || []).length ? d.movers.down.map(mover) : <p className="cc-empty">No coin fell over 3 days.</p>}</div>
    </div> : <div className="mk-cols">
      <div><h4>Most trusted creators</h4>{(d.reps?.good || []).map(r => rep(r, true))}</div>
      <div><h4>Flagged creators</h4>{(d.reps?.bad || []).map(r => rep(r, false))}</div>
    </div>}
    {d?.snapshots?.length > 0 && <p className="cc-empty">3-day snapshots kept: {d.snapshots.map(x => `${new Date(x.at * 1000).toLocaleDateString()} ($${x.top || '—'})`).join(' · ')}</p>}
  </section>;
}

const $c = v => { const n = Number(v); return !Number.isFinite(n) || !n ? '—' : n >= 1e6 ? `$${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `$${(n / 1e3).toFixed(1)}K` : n >= 1 ? `$${n.toFixed(2)}` : `$${n.toPrecision(3)}`; };
const pctC = v => { const n = Number(v); return Number.isFinite(n) ? `${n >= 0 ? '+' : ''}${Math.abs(n) >= 900 ? `${(n / 100 + 1).toFixed(1)}x` : `${n.toFixed(1)}%`}` : '—'; };

// Every FEELESS coin with its logo: live stats, a detailed ready-to-post write-up and a downloadable GIF.
function FeelessCoins({ call }) {
  const [coins, setCoins] = useState(null);
  const [bust, setBust] = useState(0);
  // Owner pins a coin's logo by hand: served by /token-logo for every card, chart and chat on the site.
  const setLogo = async (mint, file) => {
    if (!file) return;
    try {
      const { uploadCropped, CROP } = await import('../../lib/cropImage');
      const image = await uploadCropped(file, CROP.token, 512);
      if (!image) return;
      await call('/admin/token-logo', { method: 'POST', body: JSON.stringify({ mint, image }) });
      setBust(Date.now()); toast.success('Logo set — it shows everywhere on the site now.');
    } catch (e) { toast.error(e.message); }
  };
  useEffect(() => { fetch(apiUrl('/api/market/assets')).then(r => r.json()).then(d => setCoins((d.assets || []).filter(a => a.mint || a.pair))).catch(() => setCoins([])); }, []);
  if (!coins) return <p className="cc-empty">Loading FEELESS coins…</p>;
  if (!coins.length) return <p className="cc-empty">No FEELESS coins are listed yet.</p>;
  return <div className="mk-coins">{coins.map(a => {
    const p = a.pair || {}; const sym = (a.label || p.baseToken?.symbol || a.id || 'FEE').replace(/^\$/, '').toUpperCase();
    // Never blank: the FEELESS logo service (DexScreener → Jupiter → on-chain metadata → pump.fun → owner override).
    const logo = a.mint ? apiUrl(`/api/reputation/token-logo/${a.mint}${bust ? `?v=${bust}` : ''}`) : a.imageUrl || a.logo || p.info?.imageUrl; const ch = Number(p.priceChange?.h24);
    const tx = p.txns?.h24 || {}; const flow = (tx.buys || 0) + (tx.sells || 0) ? Math.round((tx.buys / (tx.buys + tx.sells)) * 100) : null;
    const url = p.pairAddress ? `${window.location.origin}/terminal/chat?chain=solana&pair=${p.pairAddress}` : `${window.location.origin}/terminal/coin/solana/${a.mint}`;
    const post = [`🟢 $${sym} on FEELESS`, p.priceUsd ? `Price ${$c(p.priceUsd)} (${pctC(ch)} 24h) · MC ${$c(p.marketCap || p.fdv)}` : 'Market initializing — be early.',
      p.liquidity?.usd ? `Liquidity ${$c(p.liquidity.usd)} · 24h volume ${$c(p.volume?.h24)}${flow != null ? ` · ${flow}% buys` : ''}` : null,
      'Zero-fee buys of FEELESS coins · every trade signed by your own wallet · rug shield + cited case files on every coin.',
      `Trade + chart: ${url}`, `#FEELESS $${sym}`].filter(Boolean).join('\n');
    return <div key={a.id || a.mint} className="mk-coin">
      <div className="mk-coin-head">{logo ? <img src={logo} alt="" /> : <i>{sym.slice(0, 2)}</i>}<div><b>${sym}</b><small>{a.mint ? `${a.mint.slice(0, 4)}…${a.mint.slice(-4)}` : ''}</small></div><span className={ch >= 0 ? 'positive' : 'negative'}>{pctC(ch)}</span></div>
      <div className="mk-coin-stats"><span><small>PRICE</small><b>{$c(p.priceUsd)}</b></span><span><small>MC</small><b>{$c(p.marketCap || p.fdv)}</b></span><span><small>LIQ</small><b>{$c(p.liquidity?.usd)}</b></span><span><small>VOL 24H</small><b>{$c(p.volume?.h24)}</b></span></div>
      <pre className="mk-post">{post}</pre>
      <div className="mk-coin-actions">{a.mint && call && <label className="m-btn"><input type="file" hidden accept="image/png,image/jpeg,image/webp,image/gif" onChange={e => setLogo(a.mint, e.target.files?.[0])} />🖼 Set logo</label>}<button type="button" className="btn-outline" onClick={() => navigator.clipboard?.writeText(post).then(() => toast.success('Post copied'))}>Copy post</button>
        <ShareGifButton label="🎞 Download GIF" card={{ kicker: 'FEELESS COIN · LIVE', title: `$${sym}`, imageUrl: logo, tone: ch < 0 ? 'down' : 'up', big: p.priceUsd ? pctC(ch) : 'LIVE SOON', lines: [`Price ${$c(p.priceUsd)} · MC ${$c(p.marketCap || p.fdv)}`, `Liquidity ${$c(p.liquidity?.usd)} · Vol ${$c(p.volume?.h24)}`, 'Zero-fee buys on FEELESS'], footer: 'feeless · non-custodial trading' }} /></div>
    </div>; })}</div>;
}

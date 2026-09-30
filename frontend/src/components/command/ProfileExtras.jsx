import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Hint } from '../Hint';
import { apiUrl } from '../../lib/api';
import { toast } from 'sonner';
import { useWallet } from '../../hooks/useWallet';
import { getChatSession } from '../../lib/chatSession';
import { ShareGifButton } from '../ShareGif';

export function usePerks(address) {
  const [d, setD] = useState(null);
  useEffect(() => { if (!address) return; fetch(apiUrl(`/api/reputation/perks/${address}`)).then(r => r.json()).then(setD).catch(() => {}); }, [address]);
  return d;
}

const ago = ts => { const days = (Date.now() / 1000 - ts) / 86400; return days < 1 ? 'today' : days < 60 ? `${Math.floor(days)}d` : days < 730 ? `${Math.floor(days / 30)}mo` : `${(days / 365).toFixed(1)}y`; };

// Real on-chain stats — every wallet has a profile before it ever sets one up.
export function OnchainStrip({ address }) {
  const [s, setS] = useState(null);
  useEffect(() => { fetch(apiUrl(`/api/reputation/wallet-stats/${address}`)).then(r => r.json()).then(setS).catch(() => setS({})); }, [address]);
  if (!s) return <div className="wp-onchain loading" data-testid="onchain-strip"><span>Reading the chain…</span></div>;
  if (!s.supported) return <div className="wp-onchain" data-testid="onchain-strip"><span><small>Chain</small><b>{s.chain === 'evm' ? 'EVM' : '—'}</b></span></div>;
  return <div className="wp-onchain" data-testid="onchain-strip">
    <span><small>SOL</small><b>{s.sol != null ? s.sol.toFixed(3) : '—'}</b></span>
    <span><small>Tokens held</small><b>{s.tokensHeld ?? '—'}</b></span>
    <span><small>Transactions</small><b>{s.txCount?.toLocaleString()}{s.txCountCapped ? '+' : ''}</b></span>
    <span><small>Wallet age</small><b>{s.firstSeen ? ago(s.firstSeen) : s.txCountCapped ? 'veteran' : '—'}</b></span>
    <a href={`https://solscan.io/account/${address}`} target="_blank" rel="noopener noreferrer">Solscan ↗</a>
  </div>;
}

export function PerksCard({ perks, mine }) {
  if (!perks) return null;
  const pct = perks.next ? Math.min(100, (perks.feeUsd / (perks.feeUsd + perks.next.needUsd)) * 100) : 100;
  return <section className="wp-card wp-perks" data-testid="perks-card">
    <div className="wpj-head"><h3>$FEE holder perks <Hint text="Your tier is checked live from the $FEE in your wallet — no subscriptions. Hold more to unlock more." /></h3><span className="wpj-count">holding <b>${perks.feeUsd}</b></span></div>
    <p className="wp-bio">No subscriptions. Hold $FEE and FEELESS unlocks more — checked live against the wallet.</p>
    <div className="wpp-ladder">{(perks.tiers || []).map(t => <div key={t.tier} className={`wpp-tier ${t.tier <= perks.tier ? 'on' : ''} ${t.tier === perks.tier ? 'current' : ''}`}>
      <div className="wpp-top"><span>{t.icon}</span><b>{t.name}</b><small>{t.minUsd ? `$${t.minUsd.toLocaleString()}+` : 'free'}</small></div>
      <ul>{(t.perks || []).map(x => <li key={x}>{t.tier <= perks.tier ? '✓' : '🔒'} {x}</li>)}</ul>
    </div>)}</div>
    {perks.next && <div className="wpp-next"><div className="wpj-bar"><i style={{ width: `${pct}%` }} /></div><span>{mine ? 'You are' : 'They are'} ${perks.next.needUsd} of $FEE away from <b>{perks.next.name}</b>{mine && <> · <Link to="/terminal/fee">Get $FEE →</Link></>}</span></div>}
  </section>;
}

export function SetupCallout({ profile, onEdit }) {
  const steps = [['displayName', 'Pick a name'], ['avatarUrl', 'Add a pic or GIF'], ['bio', 'Write a bio'], ['bannerUrl', 'Upload a banner'], ['theme', 'Choose a theme'], ['top8', 'Add your Top 8 coins']];
  const done = steps.filter(([k]) => { const v = profile?.[k]; return Array.isArray(v) ? v.length : k === 'theme' ? v && v !== 'grid' : Boolean(v); }).length;
  if (done === steps.length) return null;
  return <section className="wp-card wp-setup" data-testid="profile-setup">
    <div className="wpj-head"><h3>✨ Your profile is live — make it yours</h3><span className="wpj-count"><b>{done}</b>/{steps.length}</span></div>
    <div className="wpj-bar"><i style={{ width: `${(done / steps.length) * 100}%` }} /></div>
    <div className="wps-steps">{steps.map(([k, l]) => { const v = profile?.[k]; const ok = Array.isArray(v) ? v.length : k === 'theme' ? v && v !== 'grid' : Boolean(v); return <span key={k} className={ok ? 'ok' : ''}>{ok ? '✓' : '○'} {l}</span>; })}</div>
    <button type="button" className="btn-primary" onClick={onEdit}>Set up profile</button>
  </section>;
}

// Live portfolio: every coin held, with logos, values and links to each coin's profile.
export function PortfolioCard({ address, onSwap }) {
  const [d, setD] = useState(null);
  const [logos, setLogos] = useState({});
  const [showAll, setShowAll] = useState(false);
  useEffect(() => {
    let alive = true;
    const load = (fresh = false) => fetch(apiUrl(`/api/reputation/portfolio/${address}${fresh ? '?fresh=1' : ''}`)).then(r => r.json()).then(x => alive && setD(x)).catch(() => {});
    load(); const t = setInterval(load, 60000);
    // Right after a trade: re-read the wallet (twice: RPC balances can lag a few seconds behind confirmation).
    const onTrade = () => { setTimeout(() => load(true), 2500); setTimeout(() => load(true), 9000); };
    window.addEventListener('feeless:trade-confirmed', onTrade);
    fetch(apiUrl('/api/market/assets')).then(r => r.json()).then(x => alive && setLogos(Object.fromEntries((x.assets || []).map(a => [a.mint, { logo: a.logo || a.pair?.info?.imageUrl, pair: a.pair?.pairAddress }])))).catch(() => {});
    return () => { alive = false; clearInterval(t); window.removeEventListener('feeless:trade-confirmed', onTrade); };
  }, [address]);
  if (!d?.supported) return null;
  const fmt = v => (v == null ? '—' : v >= 1000 ? `$${(v / 1000).toFixed(1)}K` : `$${v.toFixed(2)}`);
  return <section className="wp-card portfolio-card" data-testid="portfolio">
    <div className="wpj-head"><h3>Portfolio</h3><span className="wpj-count">net worth <b>{fmt(d.totalUsd)}</b></span></div>
    <div className="pf-grid">
      <a className="pf-coin pf-sol" href="https://solscan.io/account/" onClick={e => { e.preventDefault(); window.open(`https://solscan.io/account/${d.address}`, '_blank', 'noopener'); }}><span className="pf-logo sol">◎</span><b>SOL</b><small>{d.sol.toFixed(3)}</small><em>{fmt(d.solUsd)}</em></a>
      {(showAll ? d.tokens : d.tokens.slice(0, 11)).map(t => { const pair = t.pairAddress || logos[t.mint]?.pair; const logo = t.logo || logos[t.mint]?.logo; const href = pair ? `/terminal/chat?chain=solana&pair=${pair}&room=bulls` : `/terminal/trade?q=${t.mint}`; const up = Number(t.change24h) >= 0;
        return <a key={t.mint} className="pf-coin" href={href} title={`${t.name || t.mint} · ${t.amount.toLocaleString()}`}>
          {logo ? <img className="pf-logo" src={logo} alt="" /> : <span className="pf-logo">{(t.symbol || '?').slice(0, 2)}</span>}
          <b>{t.symbol ? `$${t.symbol}` : `${t.mint.slice(0, 4)}…`}</b>
          <small>{t.amount >= 1e6 ? `${(t.amount / 1e6).toFixed(2)}M` : t.amount >= 1e3 ? `${(t.amount / 1e3).toFixed(1)}K` : t.amount.toFixed(2)}</small>
          <em>{fmt(t.usd)}{t.change24h != null && <i className={up ? 'positive' : 'negative'}> {up ? '+' : ''}{Number(t.change24h).toFixed(1)}%</i>}</em>
          {onSwap && <button type="button" className="pf-swap" onClick={e => { e.preventDefault(); e.stopPropagation(); onSwap({ chainId: 'solana', pairAddress: pair || t.mint, priceUsd: t.amount ? String(t.usd / t.amount) : undefined, baseToken: { address: t.mint, symbol: t.symbol || t.mint.slice(0, 4) }, info: { imageUrl: logo } }); }}>Swap</button>}
        </a>; })}
    </div>
    {d.tokens.length > 11 && <button type="button" className="pf-more" onClick={() => setShowAll(v => !v)}>{showAll ? 'Show top holdings' : `Show all ${d.tokens.length + 1} holdings`}</button>}
    {d.unpriced > 0 && <small className="cc-empty">{d.unpriced} token{d.unpriced === 1 ? '' : 's'} without a market price are listed without value.</small>}
  </section>;
}

// Trust ring + Follow button + follower/following counts (profile header).
export function SocialStrip({ address, mine }) {
  const { wallet, signMessage } = useWallet() || {};
  const [trust, setTrust] = useState(null);
  const [f, setF] = useState(null);
  const [open, setOpen] = useState(false);
  const load = () => fetch(apiUrl(`/api/reputation/follows/${address}${wallet?.address ? `?viewer=${wallet.address}` : ''}`)).then(r => r.json()).then(setF).catch(() => {});
  useEffect(() => { fetch(apiUrl(`/api/reputation/trust/${address}`)).then(r => r.json()).then(setTrust).catch(() => {}); }, [address]);
  useEffect(() => { load(); }, [address, wallet?.address]); // eslint-disable-line react-hooks/exhaustive-deps
  const toggle = async () => {
    if (!wallet) { toast('Connect a wallet to follow.'); return; }
    try {
      const session = await getChatSession(wallet.address, signMessage);
      const r = await fetch(apiUrl('/api/reputation/follow'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: wallet.address, session, target: address, follow: !f?.viewerFollows }) });
      if (!r.ok) throw new Error((await r.json()).detail); load();
    } catch (e) { toast.error(e.message || 'Could not follow'); }
  };
  const s = trust?.score; const pct = s == null ? 0 : s;
  return <div className="social-strip" data-testid="social-strip">
    <button type="button" className={`trust-ring lvl-${trust?.level || 'unknown'}${trust ? '' : ' loading'}`} aria-busy={!trust} onClick={() => setOpen(o => !o)} title="Trust score — tap for the breakdown" data-testid="trust-ring">
      <svg viewBox="0 0 44 44"><circle cx="22" cy="22" r="18" /><circle cx="22" cy="22" r="18" className="arc" style={{ strokeDasharray: trust ? `${(pct / 100) * 113.1} 113.1` : '28 113.1' }} /></svg>
      <span className="tr-num"><b>{trust ? (s ?? '—') : ''}</b><small>trust</small></span>
    </button>
    <div className="follow-counts"><span><b>{f?.followers ?? 0}</b> {f?.followers === 1 ? "follower" : "followers"}</span><span><b>{f?.following ?? 0}</b> following</span></div>
    {!mine && <button type="button" className={f?.viewerFollows ? 'btn-outline' : 'btn-primary'} data-testid="follow-btn" onClick={toggle}>{f?.viewerFollows ? 'Following' : 'Follow'}</button>}
    {open && trust && <div className="trust-pop" data-testid="trust-pop"><b>Trust {s ?? '—'}{trust.level ? ` · ${trust.level}` : ''}</b>{trust.note && <p>{trust.note}</p>}{trust.parts.map((p, i) => <div key={i}><span>{p.label}</span><em className={p.points >= 0 ? 'positive' : 'negative'}>{p.points >= 0 ? '+' : ''}{p.points}</em></div>)}<small>Evidence-only: wallet age, blocklist strikes, creator record, call results, followers, verification.</small></div>}
  </div>;
}

// Your FEELESS trades as cards: each one shows size, P&L on sells (vs your average entry), the fee and the tx,
// and turns into a shareable GIF in one tap.
const usd2 = v => `$${Math.abs(v).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
export function tradeCardGif(c) {
  const sell = c.side === 'sell'; const sym = c.symbol ? `$${c.symbol}` : `${c.token.slice(0, 4)}…`;
  const up = sell ? (c.pnlUsd || 0) >= 0 : true;
  return { kicker: sell ? 'SOLD ON FEELESS' : 'BOUGHT ON FEELESS', title: sym, imageUrl: apiUrl(`/api/reputation/token-logo/${c.token}`), tone: up ? 'up' : 'down',
    ...(sell && c.pnlPct != null ? { bigValue: Math.abs(c.pnlPct), bigPrefix: up ? '+' : '−', bigSuffix: '%', bigDigits: 1 } : { big: usd2(c.usd) }),
    lines: [sell && c.pnlUsd != null ? `${up ? '+' : '−'}${usd2(c.pnlUsd)} realized on ${usd2(c.usd)}` : `Size ${usd2(c.usd)}`,
      c.feeUsd ? `FEELESS fee ${usd2(c.feeUsd)}` : 'Fee-free', `tx ${c.tx.slice(0, 6)}…${c.tx.slice(-4)} · signed in my wallet`], footer: 'feeless · trade out loud' };
}

export function TradeCards({ address }) {
  const [cards, setCards] = useState(null);
  useEffect(() => {
    let alive = true;
    const load = () => fetch(apiUrl(`/api/reputation/trade-cards/${address}`)).then(r => (r.ok ? r.json() : null)).then(d => alive && d && setCards(d.cards || [])).catch(() => {});
    load();
    const onTrade = () => { setTimeout(load, 3000); setTimeout(load, 12000); };
    window.addEventListener('feeless:trade-confirmed', onTrade);
    return () => { alive = false; window.removeEventListener('feeless:trade-confirmed', onTrade); };
  }, [address]);
  if (!cards?.length) return null;
  return <section className="wp-card m-stack trade-cards" data-testid="trade-cards">
    <span className="m-label">TRADES <em>on FEELESS · every one signed by this wallet</em></span>
    <div className="trade-cards-list m-scroll">{cards.map(c => { const sell = c.side === 'sell'; const up = (c.pnlUsd || 0) >= 0;
      return <div key={c.tx} className={`m-card trade-card ${sell ? (up ? 'is-up' : 'is-down') : 'is-buy'}`}>
        <span className={`m-chip ${sell ? (up ? '' : 'bad') : ''}`}>{sell ? 'SELL' : 'BUY'}</span>
        <b>{c.symbol ? `$${c.symbol}` : `${c.token.slice(0, 4)}…`}</b>
        <span className="m-num sm">{usd2(c.usd)}</span>
        <span className={`m-num sm ${sell ? (up ? 'pos' : 'neg') : ''}`}>{sell && c.pnlUsd != null ? `${up ? '+' : '−'}${usd2(c.pnlUsd)}${c.pnlPct != null ? ` · ${up ? '+' : '−'}${Math.abs(c.pnlPct).toFixed(1)}%` : ''}` : c.feeUsd ? `fee ${usd2(c.feeUsd)}` : ''}</span>
        <a className="m-dim" href={`https://solscan.io/tx/${c.tx}`} target="_blank" rel="noopener noreferrer" title="Signed by this wallet · verified on-chain">✓ tx ↗</a>
        <ShareGifButton className="m-btn trade-card-share" label="🎞" card={tradeCardGif(c)} />
      </div>; })}</div>
  </section>;
}

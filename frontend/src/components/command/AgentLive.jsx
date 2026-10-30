import React, { Suspense, lazy } from 'react';
import { Bubble } from './LaunchCat';
import { DemoChart } from './AgentDemo';
import '../../styles/agentDemo.css';

// 🛸 AGENT LIVE (owner, 2026-10-30: "this same ui/layout from the demo in live — when a cat is bought, when I enter My agent, and Fee's live
// desk: 2 charts with thoughts"). The demo's frame, fed REAL data: each mind a live bubble whose thoughts are its own latest words, two REAL
// coin charts (what it holds, then what it reads next), and its real activity riding over both windows. A window with no coin yet shows the
// drawn ghost, labelled as a preview. Pure helpers are exported for tests.
const PriceChart = lazy(() => import('../terminal/PriceChart').then(m => ({ default: m.PriceChart })));
export const asModel = id => (id ? { id, name: String(id).split('/').pop(), provider: String(id).split('/')[0] } : null);
const pctWord = v => (v == null || !Number.isFinite(Number(v)) ? '' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`);

// pure: a trading cat's two minds — each one's own latest decisions become its thoughts; the feed is every decision, newest last
export function catMinds(cat) {
  const b = cat?.brainsCfg || {}; const brains = (b.brains || []).slice(0, 2); const dec = (b.decisions || []).slice(-24);
  const mine = id => dec.filter(x => String(x.by || '').includes(String(id).split('/').pop())).slice(-4).map(x => `${x.word} $${x.sym}`);
  return { brains, thoughts: brains.map(mine), cloud: (b.cloud || []).slice(-5).reverse(), feed: dec.slice(-3).map(x => `🧠 ${x.by} · ${x.word} $${x.sym}${x.why ? ` — ${String(x.why).slice(0, 70)}` : ''}`) };
}
// pure: the coins its two windows chart — held first, then the coins it just closed (it still reads them)
export function catCoins(cat) {
  const held = (cat?.positions || []).filter(p => p.pairAddress).map(p => ({ pair: p.pairAddress, mint: p.mint, symbol: p.symbol, pct: Number(p.currentChange), entry: Number(p.entryPriceUsd) || null, open: true }));
  const seen = new Set(held.map(c => c.pair));
  const after = (cat?.exits || []).filter(e => e.pairAddress && !seen.has(e.pairAddress)).slice(-2).reverse().map(e => ({ pair: e.pairAddress, mint: e.mint, symbol: e.symbol, open: false }));
  return [...held, ...after].slice(0, 2);
}

// the bubbles row alone (a general cat's desk puts it over its two cloud browsers)
// ☁ the HEAD CLOUD between the two minds: only what BOTH agreed on lands here (launch_cat.cloud_check) — drawn cloud, a count, the last calls
export function HeadCloud({ items = [] }) {
  const top = items[0];
  return <span className={`agl-cloud${items.length ? ' is-on' : ''}`} data-testid="head-cloud" data-tip="The head cloud: a call lands here only when BOTH minds said the same thing on the same coin">
    <svg viewBox="0 0 120 70" aria-hidden="true"><path d="M30 60 C12 60 8 40 24 36 C22 18 46 12 54 26 C62 8 92 12 90 32 C108 30 112 58 92 60 Z" /></svg>
    <b className="m-num" key={items.length}>{items.length}</b><em>HEAD CLOUD</em>
    <small>{top ? `${top.word} $${top.sym} · both agree` : 'waiting for both to agree'}</small></span>;
}
export function MindsRow({ minds = [], cloud }) {
  const mind = i => { const m = minds[i];
    return <span key={i} className={`agl-mind${m ? '' : ' is-empty'}`}><Bubble m={m?.model} i={i} kind={m?.kind} thoughts={m?.thoughts} size={64} live={!!m?.live} />
      <b>{m?.label || (i ? 'no second mind' : 'its mind')}</b><small>{m?.sub || ''}</small></span>; };
  return <div className={`agl-minds${cloud ? ' has-cloud' : ''}`} data-testid="minds-row">{mind(0)}{cloud ? <HeadCloud items={cloud} /> : null}{mind(1)}</div>;
}

export function AgentLive({ title = 'LIVE', minds = [], coins = [], feed = [], callouts, testId = 'agent-live', cloud }) {
  return <section className="agd agl is-trading" data-testid={testId}>
    <i className="agd-hex" aria-hidden="true" /><i className="agd-scan" aria-hidden="true" />
    <span className="agd-tag">◈ {title}</span>
    {minds.length ? <MindsRow minds={minds} cloud={cloud} /> : null}
    <div className="agd-wins">{[0, 1].map(i => { const c = coins[i];
      return <div key={i} className={`agd-win w${i}`} style={{ '--i': i }}>
        <span className={`agd-bar ${c ? 'is-go' : 'is-stop'}`}><i /><i /><i /><b>{c ? `$${c.symbol}` : `WINDOW ${'AB'[i]}`}</b><small>{c ? (c.open ? `holding ${pctWord(c.pct)}` : c.note || 'reading next') : 'waiting for a coin'}</small>
          <em className="agd-live">{c ? '● LIVE' : '◌ IDLE'}</em></span>
        {c ? <div className="agl-plot"><Suspense fallback={<span className="agl-load">loading ${c.symbol}'s live chart…</span>}>
          <PriceChart key={c.pair} pair={{ chainId: 'solana', pairAddress: c.pair, baseToken: { address: c.mint, symbol: c.symbol } }} interval="1m" metric="price" showVolume={false} userEntry={c.entry || null} callouts={callouts ? callouts(c.pair) : undefined} />
        </Suspense></div> : <div className="agl-ghost"><DemoChart seed={i ? 7 : 3} t={0} who="…" sym="NEXT" calls={false} /><span>PREVIEW · its next coin charts here</span></div>}
      </div>; })}</div>
    {feed.length ? <ol className="agd-feed" aria-live="polite">{feed.slice(-3).map((l, i) => <li key={`${i}-${l}`}>{l}</li>)}</ol> : null}
  </section>;
}

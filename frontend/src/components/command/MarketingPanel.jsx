import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { ShareGifButton } from '../ShareGif';

const CATS = [['movers', '🚀 Top movers · 3 days'], ['reps', '🛡 Top reputation']];
const copy = t => navigator.clipboard?.writeText(t).then(() => toast.success('Post text copied')).catch(() => toast.error('Copy failed'));
const short = a => `${a.slice(0, 4)}…${a.slice(-4)}`;

// Marketing: ready-to-post lists with copyable text and an animated GIF card for each row.
export function MarketingPanel({ call }) {
  const [d, setD] = useState(null);
  const [cat, setCat] = useState('movers');
  useEffect(() => { call('/admin/marketing').then(setD).catch(e => { toast.error(e.message); setD({}); }); }, [call]);
  const Row = ({ title, sub, post, card, img, tone }) => <div className="mk-row"><div className="mk-id">{img ? <img src={img} alt="" /> : <span className="mk-dot" />}<b>{title}</b><em className={tone}>{sub}</em></div>
    <p>{post}</p><div className="mk-act"><button type="button" className="btn-outline" onClick={() => copy(post)}>Copy post</button><ShareGifButton card={card} /></div></div>;
  const mover = r => <Row key={r.pairAddress} title={`$${r.symbol}`} sub={`${r.move3d >= 0 ? '+' : ''}${r.move3d}% · 3d`} tone={r.move3d >= 0 ? 'positive' : 'negative'} img={r.imageUrl} post={r.post}
    card={{ kicker: `TOP MOVER · 3 DAYS · ${r.chain.toUpperCase()}`, title: `$${r.symbol}`, imageUrl: r.imageUrl, tone: r.move3d >= 0 ? 'up' : 'down', bigValue: Math.abs(r.move3d), bigPrefix: r.move3d >= 0 ? '+' : '−', bigSuffix: '%', bigDigits: 1, lines: [r.name || '', 'Chart · chat · trade fee-free on FEELESS'] }} />;
  const rep = (r, good) => <Row key={r.address} title={short(r.address)} sub={`${good ? 'trusted' : 'flagged'} · score ${r.score ?? '—'}`} tone={good ? 'positive' : 'negative'} post={r.post}
    card={{ kicker: good ? 'TRUSTED CREATOR · FEELESS REP' : 'FLAGGED CREATOR · FEELESS REP', title: short(r.address), tone: good ? 'up' : 'down', bigValue: r.score ?? 0, bigDigits: 0, bigSuffix: ' rep', lines: [`${r.tokenCount} coins · ${r.bigWinners} big winners`, `${r.dumpedCount} dumps · ${r.ruggedCount} rugs`, 'Check any wallet on FEELESS'] }} />;
  return <section className="cc-panel marketing-panel">
    <nav className="feed-cats">{CATS.map(([id, l]) => <button type="button" key={id} className={cat === id ? 'on' : ''} onClick={() => setCat(id)}>{l}</button>)}</nav>
    {!d ? <p className="cc-empty">Measuring 3-day moves from FEELESS candles…</p> : cat === 'movers' ? <div className="mk-cols">
      <div><h4>Biggest gainers</h4>{(d.movers?.up || []).map(mover)}</div>
      <div><h4>Biggest drops</h4>{(d.movers?.down || []).length ? d.movers.down.map(mover) : <p className="cc-empty">No coin fell over 3 days.</p>}</div>
    </div> : <div className="mk-cols">
      <div><h4>Most trusted creators</h4>{(d.reps?.good || []).map(r => rep(r, true))}</div>
      <div><h4>Flagged creators</h4>{(d.reps?.bad || []).map(r => rep(r, false))}</div>
    </div>}
    {d?.snapshots?.length > 0 && <p className="cc-empty">3-day snapshots kept: {d.snapshots.map(x => `${new Date(x.at * 1000).toLocaleDateString()} ($${x.top || '—'})`).join(' · ')}</p>}
  </section>;
}

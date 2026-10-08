import React, { useEffect, useState } from 'react';
import { sharedJson } from '../lib/sharedJson';
import { ShareGifButton } from './ShareGif';
import '../styles/trackRecord.css';

import { tiny } from '../lib/num';
// 📜 TRACK RECORD (beside the raw swap list in ReceiptsCard): proof of what a wallet really did — verified FEELESS trades (closed pieces + open lots priced live) and its chat calls with the
// result since. From FEELESS's own records, price result, fees apart (GET /receipts/{address}). A losing entry shows as losing. Never self-reported.
const pct = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${(v * 100).toFixed(Math.abs(v) >= 1 ? 0 : 1)}%`);
const px = v => (!(v > 0) ? '—' : v >= 1 ? `$${v.toFixed(2)}` : `$${tiny(v, 3)}`);
const ago = at => { const m = Math.max(1, Math.round((Date.now() / 1000 - at) / 60)); return m < 60 ? `${m}m` : m < 2880 ? `${Math.round(m / 60)}h` : `${Math.round(m / 1440)}d`; };
const hold = m => (m < 60 ? `${Math.round(m)}m` : m < 2880 ? `${(m / 60).toFixed(1)}h` : `${(m / 1440).toFixed(1)}d`);
export const KINDS = { trade: ['✅', 'closed trade'], open: ['🟢', 'still holding'], call: ['📣', 'call'] };

export function receiptLine(r) {
  const [ico, label] = KINDS[r.kind] || KINDS.trade;
  const sub = r.kind === 'call' ? `called at ${px(r.entryPx)}${r.peakX ? ` · peaked ${r.peakX}×` : ''}` : r.kind === 'open' ? `in at ${px(r.entryPx)} · now ${px(r.exitPx)}` : `in ${px(r.entryPx)} → out ${px(r.exitPx)} · held ${hold(r.holdMin || 0)}`;
  return { ico, label, title: `$${r.symbol}`, pct: pct(r.ret), up: r.ret != null && r.ret >= 0, sub, when: ago(r.at) };
}

export function TrackRecord({ address, limit = 12 }) {
  const [d, setD] = useState(null);
  useEffect(() => { let alive = true; if (!address) return undefined; sharedJson(`/api/reputation/track-record/${address}`, { maxAge: 60000 }).then(x => alive && setD(x)).catch(() => {}); return () => { alive = false; }; }, [address]);
  const rs = d?.record || [];
  if (!rs.length) return null;
  const s = d.summary || {};
  return <details className="trk m-card" data-testid="track-record">
    <summary data-tip="Proof from FEELESS's own records: your verified trades matched buy → sell, and your chat calls with the result since. Price result, fees apart. A losing entry shows as losing.">
      📜 Track record · {s.trades ? `${s.trades} trades · ${s.wonPct}% won · median ${s.medianPct >= 0 ? '+' : ''}${s.medianPct}%` : `${rs.length} on record`}{s.calls ? ` · ${s.calls} calls` : ''}</summary>
    <ul className="trk-list">{rs.slice(0, limit).map((r, i) => { const l = receiptLine(r); return <li key={`${r.at}-${r.mint}-${i}`} className={l.up ? 'is-up' : r.ret == null ? '' : 'is-dn'} style={{ '--i': i }}>
      <span className="trk-kind" data-tip={l.label}>{l.ico}</span><b>{l.title}</b><em className="m-num">{l.pct}</em><small>{l.sub}</small><i>{l.when}</i>
      <span className="trk-acts">{r.tx ? <a className="m-btn" href={`https://solscan.io/tx/${r.tx}`} target="_blank" rel="noopener noreferrer" data-tip="The sell, on-chain">🔗</a> : null}
        {r.ret != null && <ShareGifButton className="m-btn" label="🎞" card={{ mascot: 'feecat', tone: r.ret >= 0 ? 'up' : 'down', kicker: `FEELESS · ${l.label.toUpperCase()}`, title: l.title, big: l.pct, lines: [l.sub, `${l.when} ago · verified by FEELESS`, 'price result · fees shown apart'], footer: 'feeless · track record 📜' }} />}</span></li>; })}</ul>
    {rs.length > limit && <small className="m-dim">Newest {limit} of {rs.length}.</small>}
  </details>;
}

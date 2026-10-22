import React, { Suspense, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
const EcosystemChat = React.lazy(() => import('./EcosystemChat'));

// ⚔ FAMILY FUSE — the Fuse Arena's board (owner, 2026-10-21: "two families' Fuse cards (same coin count ±1), paper or MP (2K min), spectator
// bids, played live on the pitch"). The fight itself is drawn on the stadium's pitch (FeeCapital); this board is its scoreboard: sparks,
// the six seat duels, the clock, the crowd's pool and the one-tap bid, plus the Don's challenge / accept. Every number is the server's.
const n = x => Math.round(Number(x) || 0).toLocaleString('en-US');
const pc = x => (x == null ? '—' : `${x >= 0 ? '+' : ''}${Number(x).toFixed(2)}%`);
const clock = s => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
const post = body => fetch(apiUrl('/api/reputation/familia-fuse/act'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  .then(async r => { const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || 'Failed'); return j; });

// pure: the cards a family may answer a challenge with (same coin count or one apart)
export const fits = (cards, coins) => (cards || []).filter(c => Math.abs(c.coins - coins) <= 1);

function Ticking({ left }) {
  const [s, setS] = useState(left);
  useEffect(() => { setS(left); const t = setInterval(() => setS(x => Math.max(0, x - 1)), 1000); return () => clearInterval(t); }, [left]);
  return <b className="ffb-clock">{clock(s)}</b>;
}

// 💬 one room per fight — mounted only once opened (a board of fights never loads a chat nobody is reading)
function FightChat({ f }) {
  const [open, setOpen] = useState(false);
  return <details className="ffb-chat" data-testid={`ffb-chat-${f.id}`} onToggle={e => setOpen(e.currentTarget.open)}><summary data-tip="Everyone watching this fight, one room">💬 Fight chat <small>[{f.a.tag}] vs [{f.b.tag}]</small></summary>
    {open ? <Suspense fallback={<small className="m-dim">Opening the room…</small>}><EcosystemChat compact room={`ffuse-${f.id}`} ecosystem={{ id: `ffuse-${f.id}`, name: `Family Fuse · ${f.a.tag} vs ${f.b.tag}` }} /></Suspense> : null}</details>;
}

function Fight({ f, me, cards, act, busy }) {
  const [side, setSide] = useState('a'); const [amt, setAmt] = useState(100); const [pick, setPick] = useState('');
  const d = f.duel; const mineA = me?.id === f.a.id; const mineB = me?.id === f.b.id;
  const ok = fits(cards, f.a.card?.coins || 0);
  const pool = f.crowd.pool; const tot = Math.max(1, f.crowd.total);
  return <article className={`ffb-fight s-${f.status} ${f.winner ? `w-${f.winner}` : ''}`} data-testid={`ff-${f.id}`}>
    <header className="ffb-score">
      <span className="ffb-side a" style={{ '--fc': f.a.color || '#45e486' }}><i>{f.a.tag}</i>{f.a.bracket ? <b className="ffb-br" data-tip={`Fuse rating ${n(f.a.rating)} · ${f.a.bracket} bracket`}>{f.a.bracket} · {n(f.a.rating)}</b> : null}<small>{f.a.card?.name} · {f.a.card?.coins} coins</small><em className={f.a.pct >= 0 ? 'm-pos' : 'm-neg'} key={f.a.pct}>{pc(f.a.pct)}</em></span>
      <span className="ffb-mid"><b key={`${d?.a}-${d?.b}`}>{d ? `${d.a} ⚡ ${d.b}` : 'VS'}</b>
        <small>{f.status === 'live' ? <Ticking left={f.left} /> : f.status === 'open' ? 'waiting for an answer' : f.winner === 'draw' ? 'DRAW' : f.status === 'done' ? `[${f[f.winner]?.tag}] WINS` : 'nobody answered'}</small>
        <em>{f.stake === 'mp' ? `${n(f.mp)} MP each` : 'paper'} · {f.mins}m</em>
        <span className={`ffb-kind ${f.ranked ? 'is-ranked' : ''}`} data-tip={f.ranked ? 'RANKED: the families are at most one bracket apart — the Fuse ratings move at the final bell' : 'EXHIBITION: more than one bracket apart — glory only, the ratings stay put'}>{f.ranked ? '🎖 RANKED' : 'EXHIBITION'}</span>
        {f.by ? <small className="ffb-by">called by {f.by}</small> : null}</span>
      <span className="ffb-side b" style={{ '--fc': f.b.color || '#ff8fa3' }}><i>{f.b.tag}</i>{f.b.bracket ? <b className="ffb-br" data-tip={`Fuse rating ${n(f.b.rating)} · ${f.b.bracket} bracket`}>{f.b.bracket} · {n(f.b.rating)}</b> : null}<small>{f.b.card ? `${f.b.card.name} · ${f.b.card.coins} coins` : 'no card yet'}</small><em className={f.b.pct >= 0 ? 'm-pos' : 'm-neg'} key={f.b.pct}>{pc(f.b.pct)}</em></span>
    </header>
    {f.status === 'live' ? <u className="ffb-time"><s style={{ transform: `scaleX(${Math.max(0.02, f.left / (f.mins * 60))})` }} /></u> : null}
    {d?.seats?.length ? <ol className="ffb-seats">{d.seats.map(x => <li key={x.seat} className={x.win ? `w-${x.win}` : ''}>
      <span>{x.a.symbol}</span><em className={x.a.pct >= 0 ? 'm-pos' : 'm-neg'}>{pc(x.a.pct)}</em>
      <u><s className="a" style={{ transform: `scaleX(${Math.min(1, Math.abs(x.a.pct) / 20)})` }} /><s className="b" style={{ transform: `scaleX(${Math.min(1, Math.abs(x.b.pct) / 20)})` }} /></u>
      <em className={x.b.pct >= 0 ? 'm-pos' : 'm-neg'}>{pc(x.b.pct)}</em><span>{x.b.symbol}</span></li>)}</ol> : null}
    <div className="ffb-crowd" data-tip={`The crowd: ${n(f.crowd.total)} points from ${f.crowd.bidders} bidders. Winners share the pool (the house keeps 5 %).`}>
      <u><s className="a" style={{ transform: `scaleX(${pool.a / tot})` }} /><s className="b" style={{ transform: `scaleX(${pool.b / tot})` }} /></u>
      <small>{n(pool.a)} pts{f.crowd.pays.a ? ` · pays ×${f.crowd.pays.a}` : ''}</small><small>{f.crowd.bidders} in the crowd</small><small>{f.crowd.pays.b ? `×${f.crowd.pays.b} pays · ` : ''}{n(pool.b)} pts</small></div>
    {f.bidsOpen && me ? <form className="ffb-bid" onSubmit={e => { e.preventDefault(); act({ act: 'bid', fight: f.id, side, amount: +amt }, 'Bid placed'); }}>
      <div className="m-seg">{['a', 'b'].map(s => <button key={s} type="button" className={side === s ? 'active' : ''} onClick={() => setSide(s)} disabled={(mineA && s === 'b') || (mineB && s === 'a')} data-testid={`ffb-side-${s}`}>Back {f[s].tag}</button>)}</div>
      <input className="m-input" type="number" min="10" max="5000" value={amt} onChange={e => setAmt(e.target.value)} aria-label="Points to bid" data-testid="ffb-amt" />
      <button type="submit" className="m-btn m-go" disabled={busy} data-tip={`Your member points (you have ${n(me.pts)}). Bids close in ${clock(f.lockIn)}.`} data-testid="ffb-bid">Bid</button></form> : null}
    {f.status === 'open' && mineB && (me?.boss || f.stake !== 'mp') ? <div className="ffb-answer">
      <select className="m-input" value={pick} onChange={e => setPick(e.target.value)} aria-label="Your card" data-testid="ffb-card"><option value="">Pick your card ({Math.max(1, (f.a.card?.coins || 1) - 1)}–{(f.a.card?.coins || 0) + 1} coins)</option>
        {ok.map(c => <option key={c.key} value={c.key}>{c.name} · {c.coins} coins</option>)}</select>
      <button type="button" className="m-btn m-go" disabled={busy || !pick} onClick={() => act({ act: 'accept', fight: f.id, card: pick }, 'The bell rang — fight!')} data-testid="ffb-accept">Accept</button>
      <button type="button" className="m-btn" disabled={busy} onClick={() => act({ act: 'decline', fight: f.id }, 'Declined')}>Decline</button>
      {!ok.length ? <small className="m-dim">No card with {(f.a.card?.coins || 0) - 1}–{(f.a.card?.coins || 0) + 1} coins — build one in the Fuse tab.</small> : null}</div> : null}
    {f.status === 'open' && mineA && (me?.boss || f.stake !== 'mp') ? <button type="button" className="m-btn" disabled={busy} onClick={() => act({ act: 'cancel', fight: f.id }, 'Challenge pulled')}>Pull the challenge</button> : null}
    {f.status === 'done' && f.paid ? <p className="ffb-paid">{f.winner === 'draw' ? 'Draw — stakes and bids refunded.' : `[${f[f.winner].tag}] took ${f.mp ? `${n((f.paid.fam || {})[f[f.winner].id])} MP` : 'the paper win'} · ${Object.keys(f.paid.bids || {}).length} bidders paid · house ${n(f.paid.house)}`}</p> : null}
    {f.elo ? <p className="ffb-elo" data-tip="Ranked: the Fuse ratings after the final bell">🎖 [{f.a.tag}] {n(f.elo.a[0])} → <b className={f.elo.a[1] >= f.elo.a[0] ? 'm-pos' : 'm-neg'}>{n(f.elo.a[1])}</b> · [{f.b.tag}] {n(f.elo.b[0])} → <b className={f.elo.b[1] >= f.elo.b[0] ? 'm-pos' : 'm-neg'}>{n(f.elo.b[1])}</b></p> : null}
    <FightChat f={f} />
  </article>;
}

// 🎖 THE FUSE LADDER: every family's Fuse rating, its bracket band filled to the next one (ranked fights move it, exhibitions don't)
export function nextBand(rating, brackets) {
  const bs = (brackets || []).map(b => b.from).sort((a, b) => a - b); const lo = [...bs].reverse().find(x => rating >= x) ?? 0; const hi = bs.find(x => x > rating);
  return hi == null ? 1 : Math.max(0.03, Math.min(1, (rating - lo) / (hi - lo)));
}
function FuseLadder({ rows, brackets, me }) {
  return <div className="ffb-ladder" data-testid="ffb-ladder"><span className="m-label">🎖 FUSE LADDER · {(brackets || []).map(b => b.word).join(' → ')}</span>
    <ol>{rows.map((r, i) => <li key={r.id} className={me?.id === r.id ? 'is-me' : ''} style={{ '--i': i }}><b>{i + 1}</b><i>[{r.tag}]</i><span>{r.name}</span><em data-tip={`${r.bracket} bracket`}>{r.bracket}</em>
      <u aria-hidden="true"><s style={{ transform: `scaleX(${nextBand(r.rating, brackets)})` }} /></u><strong>{n(r.rating)}</strong></li>)}</ol></div>;
}

function Challenge({ v, act, busy }) {
  const me = v.me; const ff = v.ffuse;
  const rivals = [...new Map([...(v.ranked || []), ...(v.blocks || []).filter(b => b.kind === 'family' && b.owner)].map(r => [r.id || r.owner, { id: r.id || r.owner, tag: r.tag, name: r.name }])).values()].filter(r => r.id !== me.id);
  const [vs, setVs] = useState(''); const [card, setCard] = useState(''); const [stake, setStake] = useState('paper'); const [mp_, setMp] = useState(500); const [mins, setMins] = useState(15);
  const need = Math.max(v.rules?.fuseMinMp || 2000, +mp_ || 0);
  if (!ff.cards?.length) return <p className="ffb-hint">Your family has no Fuse card yet — <a href="/terminal/fuse?tab=lab">build one in the Fuse tab</a>, then call a rival out.</p>;
  return <form className="ffb-call" onSubmit={e => { e.preventDefault(); act({ act: 'challenge', vs, card, stake, mp: stake === 'mp' ? +mp_ : 0, mins }, 'Challenge sent'); }} data-testid="ffb-call">
    <span className="m-label">📣 CALL A FAMILY OUT</span>
    <select className="m-input" value={vs} onChange={e => setVs(e.target.value)} aria-label="Rival family" data-testid="ffb-vs"><option value="">Rival family…</option>{rivals.map(r => <option key={r.id} value={r.id}>[{r.tag}] {r.name}</option>)}</select>
    <select className="m-input" value={card} onChange={e => setCard(e.target.value)} aria-label="Your card" data-testid="ffb-mycard"><option value="">Your card…</option>{ff.cards.map(c => <option key={c.key} value={c.key}>{c.name} · {c.coins} coins</option>)}</select>
    <div className="m-seg">{['paper', 'mp'].map(s => <button key={s} type="button" className={stake === s ? 'active' : ''} disabled={s === 'mp' && !me.boss} onClick={() => setStake(s)} data-tip={s === 'mp' ? `Both banks put up the stake; needs ${n(v.rules?.fuseMinMp)} MP in the bank` : 'Glory + the ladder, nothing staked'} data-testid={`ffb-stake-${s}`}>{s === 'mp' ? 'MP' : 'Paper'}</button>)}</div>
    {stake === 'mp' ? <input className="m-input" type="number" min="100" value={mp_} onChange={e => setMp(e.target.value)} aria-label="MP stake" data-testid="ffb-mp" /> : null}
    <div className="m-seg">{(ff.mins || [15, 30, 60]).map(m => <button key={m} type="button" className={mins === m ? 'active' : ''} onClick={() => setMins(m)}>{m}m</button>)}</div>
    <button type="submit" className="m-btn m-go" disabled={busy || !vs || !card || (stake === 'mp' && me.bank < need)} data-tip={stake === 'mp' && me.bank < need ? `Your bank needs ${n(need)} MP` : 'Send the challenge'} data-testid="ffb-send">⚔ Challenge</button>
  </form>;
}

export function FamilyFuseBoard({ v, setV, addr, sess }) {
  const [busy, setBusy] = useState(false);
  const ff = v.ffuse || { fights: [] };
  const act = async (body, ok) => {
    if (!sess) { toast.error('Connect your wallet + open chat once to sign in first.'); return; }
    setBusy(true);
    try { const r = await post({ address: addr, session: sess, ...body }); const { result, ...rest } = r; setV(x => ({ ...x, ffuse: { ...x.ffuse, ...rest } })); toast.success(ok); }
    catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const mine = v.me && ff.fights.find(f => ['open', 'live'].includes(f.status) && [f.a.id, f.b.id].includes(v.me.id));
  return <section className="ffb m-card m-live" id="family-fuse" data-testid="family-fuse">
    <header><span className="m-label">⚔ FUSE ARENA · FAMILY FUSE</span><small>Two families' Fuse cards · same coin count or one apart · six seat duels, most sparks wins · paper or MP ({n(v.rules?.fuseMinMp)} MP in the bank) · the crowd bids its points</small></header>
    {ff.fights.length ? ff.fights.map(f => <Fight key={f.id} f={f} me={v.me} cards={ff.cards} act={act} busy={busy} />) : <p className="ffb-hint">The stadium is quiet. The first family to call a rival out fills it.</p>}
    {v.me && !mine ? <Challenge v={v} act={act} busy={busy} /> : null}
    {ff.ladder?.length ? <FuseLadder rows={ff.ladder} brackets={ff.brackets} me={v.me} /> : null}
  </section>;
}

// ⚔ the Fuse tab's window into the stadium: live + open Family Fuse fights, one tap into Fee City
export function FamilyFuseStrip() {
  const [d, setD] = useState(null);
  useEffect(() => { let on = true; const go = () => fetch(apiUrl('/api/reputation/familia-fuse')).then(r => (r.ok ? r.json() : null)).then(x => on && x && setD(x)).catch(() => {});
    go(); const t = setInterval(() => { if (!document.hidden) go(); }, 20000); return () => { on = false; clearInterval(t); }; }, []);
  const rows = (d?.fights || []).filter(f => ['live', 'open'].includes(f.status));
  return <a className="ffs m-card" href="/terminal/leaderboard?lens=crews" data-testid="family-fuse-strip" data-tip="Family Fuse fights live in Fee City's Fuse Arena">
    <b>⚔ FAMILY FUSE</b>{rows.length ? rows.slice(0, 3).map(f => <span key={f.id} className={`s-${f.status}`}><i>{f.a.tag}</i>{f.duel ? ` ${f.duel.a} ⚡ ${f.duel.b} ` : ' vs '}<i>{f.b.tag}</i><small>{f.status === 'live' ? clock(f.left) : 'open'}</small></span>)
      : <span className="is-quiet">families battle their Fuse cards in Fee City's stadium — build yours here, call a rival out there</span>}<em>Enter the stadium ▸</em></a>;
}

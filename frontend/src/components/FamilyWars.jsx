import React, { useEffect, useMemo, useState } from 'react';
import { sharedJson } from '../lib/sharedJson';
import { FamilyBadge } from './FamilyBadge';
import NumInput from './NumInput';
import '../styles/familyWars.css';

// ⚔ THE WAR ROOM (family_wars.py): families call each other out, bid up a POINTS pot, set a bell and fight a battle trench — each team's verified
// FEELESS trades inside the window decide it; allies can join a side. Points only, never money. GET /crews/wars · POST /crews/act war|answer|raise|join|ally|unally.
const STATE_WORD = { open: '📣 CALLED OUT', set: '🔔 BELL SET', live: '⚔ LIVE', done: '🏁 SETTLED', void: '∅ VOID', declined: '✕ DECLINED' };
const STAKES = [25, 100, 250, 500, 1000];
const BELLS = [['1h', 3600], ['6h', 6 * 3600], ['12h', 12 * 3600], ['24h', 86400], ['3d', 3 * 86400]];
export const clockWord = s => { if (s == null) return '—'; s = Math.max(0, Math.round(s)); const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  return d ? `${d}d ${h}h` : h ? `${h}h ${m}m` : m ? `${m}m ${s % 60}s` : `${s}s`; };
// pure: the tug position 0–1 (side A's share) from both sides' live % — even when nobody traded
export const tug = sc => { const a = sc?.a?.pct, b = sc?.b?.pct; if (a == null && b == null) return 0.5; const x = (a ?? -5) - (b ?? -5); return Math.max(0.06, Math.min(0.94, 0.5 + x / 40)); };

export function useWars(every = 15000) {
  const [d, setD] = useState(null);
  useEffect(() => { let on = true; let t = null;
    const go = () => sharedJson('/api/reputation/crew-wars', { maxAge: 10000 }).then(x => on && x && setD(x)).catch(() => {}).finally(() => { if (on) t = setTimeout(go, document.hidden ? every * 3 : every); });
    go(); return () => { on = false; clearTimeout(t); }; }, [every]);
  return d;
}

function Side({ f, sc, win, pot }) {
  return <div className={`fwr-side ${win ? 'is-win' : ''}`}>
    {f?.badge?.emblem ? <FamilyBadge b={{ ...f.badge, tag: f.tag, name: f.name }} size="sm" /> : <span className="fwr-tag">{f?.tag}</span>}
    <b>[{f?.tag}] {f?.name}</b>
    <em className={sc?.pct == null ? '' : sc.pct >= 0 ? 'm-pos' : 'm-neg'} key={sc?.pct}>{sc?.pct == null ? '—' : `${sc.pct >= 0 ? '+' : ''}${sc.pct}%`}</em>
    <small>{sc ? `${sc.trades} trades · ${sc.team} on the team` : ''}{pot != null ? ` · put in ${pot}` : ''}</small>
  </div>;
}

function WarCard({ w, myId, owner, act, busy, now }) {
  const [stake, setStake] = useState(String(w.potSides?.a || 25));
  const mySide = w.a.id === myId ? 'a' : w.b.id === myId ? 'b' : (w.allies?.a || []).some(x => x.id === myId) ? 'a' : (w.allies?.b || []).some(x => x.id === myId) ? 'b' : null;
  const clock = w.state === 'open' || w.state === 'set' ? w.startAt - now : w.state === 'live' ? w.endAt - now : null;
  const t = tug(w.score);
  return <article className={`fwr-war s-${w.state} ${mySide ? 'is-mine' : ''}`} data-testid={`war-${w.id}`}>
    <header><span className="fwr-state">{STATE_WORD[w.state] || w.state}</span><span className="fwr-pot" key={w.pot}><i>🪙</i>{w.pot.toLocaleString('en-US')}<small>PTS POT</small></span>
      <span className="fwr-clock">{clock != null ? <>{w.state === 'live' ? 'ENDS IN' : 'BELL IN'} <b>{clockWord(clock)}</b></> : `${w.hours}h war`}</span></header>
    <div className="fwr-vs">
      <Side f={w.a} sc={w.score?.a} win={w.winner === 'a'} pot={w.potSides?.a} />
      <span className="fwr-x" aria-hidden>VS</span>
      <Side f={w.b} sc={w.score?.b} win={w.winner === 'b'} pot={w.potSides?.b} />
    </div>
    {(w.state === 'live' || w.state === 'done') && <div className="fwr-tug" aria-label="who is winning"><i style={{ transform: `scaleX(${t})` }} /><span style={{ transform: `translateX(${(t - 0.5) * 100}%)` }}>⚔</span></div>}
    {(w.allies?.a?.length || w.allies?.b?.length) ? <p className="fwr-allies">🤝 {[...(w.allies.a || []).map(x => `[${x.tag}] with [${w.a.tag}]`), ...(w.allies.b || []).map(x => `[${x.tag}] with [${w.b.tag}]`)].join(' · ')}</p> : null}
    <ol className="fwr-log">{(w.log || []).slice(-3).reverse().map(([at, line]) => <li key={at + line}>{line}</li>)}</ol>
    {owner && w.state === 'open' && w.b.id === myId && <div className="fwr-acts">
      <span className="fwr-unit"><NumInput className="m-input" value={stake} onChange={e => setStake(e.target.value)} aria-label="Your stake" /><i>pts</i></span>
      <button type="button" className="m-btn m-go" disabled={!!busy} onClick={() => act('answer', { id: w.id, ok: true, stake: Number(stake) }, '⚔ accepted — the bell is set')} data-testid="war-accept">Accept · match {w.potSides?.a}+</button>
      <button type="button" className="m-btn" disabled={!!busy} onClick={() => act('answer', { id: w.id, ok: false }, 'declined')}>Decline</button></div>}
    {owner && mySide && (w.state === 'open' || w.state === 'set') && clock > 0 && <div className="fwr-acts">
      {[25, 100, 250].map(n => <button key={n} type="button" className="m-btn" disabled={!!busy} onClick={() => act('raise', { id: w.id, stake: n }, `🔥 +${n} in the pot`)} data-testid={`war-raise-${n}`}>🔥 +{n}</button>)}</div>}
    {owner && !mySide && w.state === 'set' && clock > 0 && <div className="fwr-acts"><button type="button" className="m-btn" disabled={!!busy} onClick={() => act('join', { id: w.id, stake: 50 }, '🤝 joined your ally')} data-testid="war-join">🤝 Join your ally · 50 pts</button></div>}
  </article>;
}

function CallOut({ mine, rows, act, busy }) {
  const others = (rows || []).filter(r => r.id !== mine.id);
  const [vs, setVs] = useState(''); const [stake, setStake] = useState(100); const [bell, setBell] = useState(3600); const [hours, setHours] = useState(4);
  const [team, setTeam] = useState(() => mine.members.slice(0, 5).map(m => m.address));
  const flip = a => setTeam(t => (t.includes(a) ? t.filter(x => x !== a) : t.length >= 5 ? t : [...t, a]));
  return <form className="fwr-call" onSubmit={e => { e.preventDefault(); act('war', { vs, stake: Number(stake), startAt: Date.now() / 1000 + bell, hours, team }, `📣 [${vs}] called out — they have until the bell to answer`); }} data-testid="war-callout">
    <b className="fwr-h">📣 CALL A FAMILY OUT</b>
    <div className="fwr-field"><span>Family</span><select className="m-input" value={vs} onChange={e => setVs(e.target.value)} aria-label="Family to call out"><option value="">pick a family…</option>{others.map(r => <option key={r.id} value={r.tag}>[{r.tag}] {r.name}{r.warW != null ? ` · ${r.warW}W ${r.warL}L` : ''}</option>)}</select></div>
    <div className="fwr-field"><span>Stake</span><div className="m-seg">{STAKES.map(n => <button type="button" key={n} className={stake === n ? 'active' : ''} onClick={() => setStake(n)}>{n}</button>)}</div><small>from the war chest · {mine.war?.chest ?? 500} pts in it</small></div>
    <div className="fwr-field"><span>Bell in</span><div className="m-seg">{BELLS.map(([l, s]) => <button type="button" key={l} className={bell === s ? 'active' : ''} onClick={() => setBell(s)}>{l}</button>)}</div></div>
    <div className="fwr-field"><span>Length</span><div className="m-seg">{[1, 4, 12, 24].map(h => <button type="button" key={h} className={hours === h ? 'active' : ''} onClick={() => setHours(h)}>{h}h</button>)}</div></div>
    <div className="fwr-field"><span>Team ({team.length}/5)</span><div className="fwr-team">{mine.members.map(m => <button type="button" key={m.address} className={team.includes(m.address) ? 'active' : ''} onClick={() => flip(m.address)}>{m.rankLabel ? m.rankLabel.split(' ')[0] : ''} {m.name}</button>)}</div></div>
    <button type="submit" className="m-btn m-go" disabled={!vs || !!busy} data-testid="war-send">⚔ Send the call-out · {stake} pts</button>
    <small className="m-dim">The pot is family points, never money. Each member signs their own trades; only verified trades inside the window count.</small>
  </form>;
}

export function WarRoom({ mine, owner, rows, act, busy }) {
  const d = useWars(); const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => { const t = setInterval(() => setNow(Date.now() / 1000), 1000); return () => clearInterval(t); }, []);
  const [ally, setAlly] = useState('');
  const wars = d?.wars || [];
  const mineWars = useMemo(() => wars.filter(w => [w.a.id, w.b.id, ...(w.allies?.a || []).map(x => x.id), ...(w.allies?.b || []).map(x => x.id)].includes(mine.id)), [wars, mine.id]);
  const rest = wars.filter(w => !mineWars.includes(w) && ['live', 'set'].includes(w.state));
  const myAllies = (d?.alliances || []).filter(a => a.a === mine.tag || a.b === mine.tag).map(a => (a.a === mine.tag ? a.b : a.a));
  const asks = (d?.asks || []).filter(a => a.to === mine.tag);
  return <div className="fwr" data-testid="war-room">
    <div className="fwr-vitals">{[['🪙 WAR CHEST', mine.war?.chest ?? 500], ['🏆 WARS WON', mine.war?.wins ?? 0], ['☠ LOST', mine.war?.losses ?? 0], ['⚔ ON NOW', mineWars.filter(w => w.state === 'live').length], ['🤝 ALLIES', myAllies.length]].map(([k, v], i) =>
      <span key={k} style={{ '--i': i }}><em>{k}</em><b key={v}>{Number(v).toLocaleString('en-US')}</b></span>)}</div>
    <section className="fwr-list">{mineWars.length ? mineWars.map(w => <WarCard key={w.id} w={w} myId={mine.id} owner={owner} act={act} busy={busy} now={now} />)
      : <p className="m-dim fwr-empty">No war on. {owner ? 'Call a family out below — set a pot and a bell.' : 'Your Don calls the wars.'}</p>}</section>
    {owner && <CallOut mine={mine} rows={rows} act={act} busy={busy} />}
    <section className="fwr-ally"><b className="fwr-h">🤝 ALLIANCES</b>
      <p>{myAllies.length ? myAllies.map(t => <span key={t} className="m-chip">[{t}]{owner && <button type="button" onClick={() => act('unally', { vs: t }, `alliance with [${t}] broken`)} aria-label={`break alliance with ${t}`}>✕</button>}</span>) : <small className="m-dim">No allies yet — an ally can join your side of any war.</small>}</p>
      {asks.map(a => <p key={a.from} className="fwr-ask">[{a.from}] wants an alliance {owner && <button type="button" className="m-btn" onClick={() => act('ally', { vs: a.from }, `🤝 allied with [${a.from}]`)}>Seal it</button>}</p>)}
      {owner && <form onSubmit={e => { e.preventDefault(); act('ally', { vs: ally }, `🤝 alliance offered to [${ally}]`); setAlly(''); }}><select className="m-input" value={ally} onChange={e => setAlly(e.target.value)} aria-label="Family to ally with"><option value="">offer an alliance…</option>{(rows || []).filter(r => r.id !== mine.id && !myAllies.includes(r.tag)).map(r => <option key={r.id} value={r.tag}>[{r.tag}] {r.name}</option>)}</select><button type="submit" className="m-btn" disabled={!ally}>Offer</button></form>}
    </section>
    {rest.length ? <section className="fwr-list"><b className="fwr-h">🔭 OTHER WARS</b>{rest.map(w => <WarCard key={w.id} w={w} myId={mine.id} owner={owner} act={act} busy={busy} now={now} />)}</section> : null}
  </div>;
}

// 🏟 the public war strip (no family needed): live + upcoming wars with pot and clock
export function WarStrip() {
  const d = useWars(20000); const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => { const t = setInterval(() => setNow(Date.now() / 1000), 1000); return () => clearInterval(t); }, []);
  const ws = (d?.wars || []).filter(w => ['live', 'set', 'open'].includes(w.state)).slice(0, 4);
  if (!ws.length) return null;
  return <section className="fwr-strip" data-testid="war-strip"><b className="fwr-h">⚔ FAMILY WARS</b>{ws.map(w => <span key={w.id} className={`s-${w.state}`}>[{w.a.tag}] <i>vs</i> [{w.b.tag}] · 🪙 {w.pot} · {w.state === 'live' ? `ends ${clockWord(w.endAt - now)}` : `bell ${clockWord(w.startAt - now)}`}</span>)}</section>;
}


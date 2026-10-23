import React, { useEffect, useMemo, useState } from 'react';
import { sharedJson } from '../lib/sharedJson';
import { FamilyBadge } from './FamilyBadge';
import NumInput from './NumInput';
import { useGlide } from '../lib/useGlide';
import { useCrewBoard } from './CrewCard';
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

// 🏟 the arena behind every war card (drawn, no emoji): two spotlights from the rafters onto the ring, the ropes, the crowd's heads in the dark,
// haze on the floor. The lights take each family's colour (--ca / --cb); a live war's lights sway slowly, a settled one is lit for the winner only.
function ArenaArt() {
  return <svg className="fwr-arena" viewBox="0 0 400 170" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <path className="sp sp-a" d="M30,-10 L70,-10 L210,170 L110,170 Z" /><path className="sp sp-b" d="M330,-10 L370,-10 L290,170 L190,170 Z" />
    <ellipse className="fl" cx="200" cy="168" rx="190" ry="26" />
    <path className="rope" d="M40,128 Q200,138 360,128 M40,112 Q200,122 360,112" />
    <path className="post" d="M40,100 V150 M360,100 V150" />
    <g className="crowd">{Array.from({ length: 34 }, (_, i) => <circle key={i} cx={6 + i * 11.8} cy={160 - (i % 3) * 4} r={4.6 + (i % 2)} />)}</g>
  </svg>;
}
// the VS mark: a ring, a bolt through it, the two letters
function VsMark({ live }) {
  return <svg className={`fwr-vsm ${live ? 'is-live' : ''}`} viewBox="0 0 64 64" aria-hidden="true">
    <circle cx="32" cy="32" r="26" className="r1" /><circle cx="32" cy="32" r="20" className="r2" />
    <path d="M36,6 L22,34 H31 L26,58 L44,26 H34 Z" className="bolt" />
    <text x="32" y="38" textAnchor="middle" className="vs">VS</text>
  </svg>;
}
function Side({ f, sc, win, lose, pot, max = 1, side }) {
  const pct = useGlide(sc?.pct == null ? null : Number(sc.pct));
  return <div className={`fwr-side s-${side} ${win ? 'is-win' : ''} ${lose ? 'is-lose' : ''}`}>
    {win ? <span className="fwr-laurel" aria-label="winner"><i aria-hidden="true" />WINNER<i aria-hidden="true" /></span> : null}
    <span className="fwr-crest">{f?.badge?.emblem ? <FamilyBadge b={{ ...f.badge, tag: f.tag, name: f.name }} size="md" px={74} chips={false} /> : <span className="fwr-tag">{f?.tag}</span>}</span>
    <b>{f?.name}</b>
    <em className={pct == null ? '' : pct >= 0 ? 'm-pos' : 'm-neg'} data-tip="Their members' verified FEELESS trades inside the war window (price result, fees apart)">{pct == null ? '—' : `${pct >= 0 ? '+' : ''}${pct}%`}</em>
    {sc ? <span className="fwr-meters"><span data-tip={`${sc.trades} closed trades in the window`}><small>TRADES</small><u><i style={{ transform: `scaleX(${Math.max(0.04, Math.min(1, (sc.trades || 0) / Math.max(1, max)))})` }} /></u><b>{sc.trades}</b></span>
      <span data-tip={`${sc.team} of 5 on the team`}><small>TEAM</small><s>{[0, 1, 2, 3, 4].map(k => <i key={k} className={k < (sc.team || 0) ? 'on' : ''} />)}</s></span></span> : null}
    {pot != null ? <small className="fwr-put">put in <b>{pot}</b> pts</small> : null}
  </div>;
}

function WarCard({ w, myId, owner, act, busy, now }) {
  const [stake, setStake] = useState(String(w.potSides?.a || 25));
  const mySide = w.a.id === myId ? 'a' : w.b.id === myId ? 'b' : (w.allies?.a || []).some(x => x.id === myId) ? 'a' : (w.allies?.b || []).some(x => x.id === myId) ? 'b' : null;
  const clock = w.state === 'open' || w.state === 'set' ? w.startAt - now : w.state === 'live' ? w.endAt - now : null;
  const t = tug(w.score); const max = Math.max(w.score?.a?.trades || 0, w.score?.b?.trades || 0, 1);
  const win = w.state === 'done' ? w.winner : null;
  return <article className={`fwr-war s-${w.state} ${mySide ? 'is-mine' : ''} ${win ? `won-${win}` : ''}`} style={{ '--ca': w.a.badge?.c1 || '#d4af37', '--cb': w.b.badge?.c1 || '#b3122e' }} data-testid={`war-${w.id}`}>
    <ArenaArt />
    {w.state === 'live' ? <span className="fwr-sparks" aria-hidden="true">{[0, 1, 2, 3, 4, 5, 6].map(i => <i key={i} style={{ '--i': i }} />)}</span> : null}
    <header><span className="fwr-state">{STATE_WORD[w.state] || w.state}</span>
      <span className="fwr-pot" key={w.pot} data-tip="Family points both sides put in — the winner takes the pot. Points, never money."><span className="fwr-coins" aria-hidden="true"><i /><i /><i /></span>{w.pot.toLocaleString('en-US')}<small>PTS POT</small></span>
      <span className="fwr-clock">{clock != null ? <>{w.state === 'live' ? 'ENDS IN' : 'BELL IN'} <b>{clockWord(clock)}</b></> : `${w.hours}h war`}</span></header>
    <div className="fwr-vs">
      <Side f={w.a} sc={w.score?.a} win={win === 'a'} lose={win === 'b'} pot={w.potSides?.a} max={max} side="a" />
      <VsMark live={w.state === 'live'} />
      <Side f={w.b} sc={w.score?.b} win={win === 'b'} lose={win === 'a'} pot={w.potSides?.b} max={max} side="b" />
    </div>
    {(w.state === 'live' || w.state === 'done') && <div className="fwr-tug" aria-label={`who is winning: [${w.a.tag}] ${Math.round(t * 100)}%`} data-tip="The rope: whoever's members trade better pulls it their way">
      <i className="ra" style={{ transform: `scaleX(${t})` }} /><i className="rb" style={{ transform: `scaleX(${1 - t})` }} /><span className="fwr-knot" style={{ transform: `translateX(${(t - 0.5) * 100}%)` }}><b /></span></div>}
    {(w.allies?.a?.length || w.allies?.b?.length) ? <p className="fwr-allies">🤝 {[...(w.allies.a || []).map(x => `[${x.tag}] with [${w.a.tag}]`), ...(w.allies.b || []).map(x => `[${x.tag}] with [${w.b.tag}]`)].join(' · ')}</p> : null}
    <ol className="fwr-log">{(w.log || []).slice(-3).reverse().map(([at, line], i) => <li key={at + line} style={{ '--i': i }}>{line}</li>)}</ol>
    {owner && w.state === 'open' && w.b.id === myId && <div className="fwr-acts">
      <span className="fwr-unit"><NumInput className="m-input" value={stake} onChange={e => setStake(e.target.value)} aria-label="Your stake" /><i>pts</i></span>
      <button type="button" className="m-btn m-go" disabled={!!busy} onClick={() => act('answer', { id: w.id, ok: true, stake: Number(stake) }, '⚔ accepted — the bell is set')} data-testid="war-accept">Accept · match {w.potSides?.a}+</button>
      <button type="button" className="m-btn" disabled={!!busy} onClick={() => act('answer', { id: w.id, ok: false }, 'declined')}>Decline</button></div>}
    {owner && mySide && (w.state === 'open' || w.state === 'set') && clock > 0 && <div className="fwr-acts">
      {[25, 100, 250].map(n => <button key={n} type="button" className="m-btn" disabled={!!busy} onClick={() => act('raise', { id: w.id, stake: n }, `🔥 +${n} in the pot`)} data-testid={`war-raise-${n}`}>🔥 +{n}</button>)}</div>}
    {owner && !mySide && w.state === 'set' && clock > 0 && <div className="fwr-acts"><button type="button" className="m-btn" disabled={!!busy} onClick={() => act('join', { id: w.id, stake: 50 }, '🤝 joined your ally')} data-testid="war-join">🤝 Join your ally · 50 pts</button></div>}
  </article>;
}

// 🏟 THE QUIET FRONT (owner: "no dead text"): an empty war room is the drawn ring with nobody in it, the families that could step in (their
// crest + this week's verified %, ranked), and how a war runs as four lit steps — never a bare line
const HOWTO = [['📣', 'CALL OUT', 'a Don picks a family'], ['🪙', 'POT', '25 – 1,000 pts from the war chest'], ['🔔', 'BELL', '1 h – 3 d to answer'], ['⚔', 'FIGHT', 'verified trades in the window decide it']];
export function QuietFront({ rows, note, cta = null }) {
  const fams = (rows || []).filter(r => r.tag).slice(0, 6); const top = Math.max(5, ...fams.map(r => Math.abs(Number(r.pct) || 0)));
  return <div className="fwr-quiet" data-testid="war-quiet">
    <div className="fwr-quiet-ring"><ArenaArt /><VsMark /><span className="fwr-quiet-sign"><b>THE RING IS EMPTY</b><small>{note}</small></span></div>
    {fams.length ? <div className="fwr-contenders"><em>WHO COULD STEP IN · THIS WEEK</em><ol>{fams.map((r, i) => <li key={r.id || r.tag} style={{ '--i': i }} data-tip={`[${r.tag}] ${r.name}: ${r.members}/${r.seats} seats · verified trades this week`}>
      {r.badge?.emblem ? <FamilyBadge b={{ ...r.badge, tag: r.tag, name: r.name }} size="sm" px={30} chips={false} /> : <span className="fwr-tag">{r.tag}</span>}
      <span className="fwr-cname"><b>{r.name}</b><small>{r.members}/{r.seats} seats</small></span>
      <u aria-hidden="true"><s className={(Number(r.pct) || 0) >= 0 ? 'up' : 'dn'} style={{ transform: `scaleX(${Math.max(0.04, Math.min(1, Math.abs(Number(r.pct) || 0) / top))})` }} /></u>
      <em className={r.pct == null ? '' : r.pct >= 0 ? 'm-pos' : 'm-neg'}>{r.pct == null ? '—' : `${r.pct >= 0 ? '+' : ''}${r.pct}%`}</em></li>)}</ol></div> : null}
    <ol className="fwr-howto">{HOWTO.map(([ic, k, d], i) => <li key={k} style={{ '--i': i }}><i aria-hidden="true">{ic}</i><b>{k}</b><small>{d}</small></li>)}</ol>
    {cta}
  </div>;
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
      : <QuietFront rows={(rows || []).filter(r => r.id !== mine.id)} note={owner ? 'Call a family out below — set a pot and a bell.' : 'Your Don calls the wars.'} />}</section>
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


// 🏟 every war, for anyone (no family needed): live first, then set, open, finished — read-only cards
export function PublicWars({ onJoin }) {
  const d = useWars(); const board = useCrewBoard(); const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => { const t = setInterval(() => { if (!document.hidden) setNow(Date.now() / 1000); }, 1000); return () => clearInterval(t); }, []);
  const wars = (d?.wars || []).slice(0, 12);
  return <div className="fwr" data-testid="public-wars">{wars.length ? <section className="fwr-list">{wars.map(w => <WarCard key={w.id} w={w} myId={null} owner={false} act={() => {}} busy now={now} />)}</section>
    : d ? <QuietFront rows={board?.board} note="No family wars yet — join a family and your Don can call one out."
      cta={onJoin ? <button type="button" className="m-btn m-go fwr-quiet-go" onClick={onJoin} data-tip="Start a family or join one — then your Don can call a war" data-testid="war-join">🌹 Join a family</button> : null} />
      : <p className="m-dim fwr-empty">Reading the war room…</p>}</div>;
}

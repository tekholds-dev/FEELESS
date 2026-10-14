import React, { useState } from 'react';
import { toast } from 'sonner';
import { hubLoad } from '../../lib/agentHub';
import { VITAL_GROUPS, vitalTiles, vitalScore } from '../../lib/vitalBoard';
import { openCoin } from '../CoinDrawer';
import { SocialIcons } from '../QuickPulse';
import { mergedVit } from '../../lib/vitalBoard';
import '../../styles/vitalBoard.css';

const MODE_WORD = { off: 'off', flag: '👀 flag only', rank: '⬇ rank down', skip: '✋ skip' };
const VERDICT = { right: ['✅ RIGHT', 'the coins it hit typically fell — the lesson holds'], wrong: ['❌ WRONG', 'the coins it hit typically ROSE — it ranks winners down'], open: ['⏳ PROVING', 'under 10 coins judged yet'] };

// 🎓 ONE lesson-rule, tunable in place: what it catches (plain words) · what it does (off · flag · rank down · skip) · how hard · its knob ·
// the coins it hits right now · its own record (coins it hit, graded 30 min later). Used by the Teach box and the vital board.
export function RuleCard({ r, call, isOwner, compact }) {
  const [busy, setBusy] = useState(false);
  if (!r) return null;
  const set = async change => {
    if (!isOwner || busy) return;
    setBusy(true);
    try { await call('/admin/agents', { method: 'POST', body: JSON.stringify({ taughtRule: { key: r.key, ...change } }) }); await hubLoad(); toast.success(`${r.label}: saved — the agents use it on the next pass`); }
    catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const rec = r.record || {}; const [vw, vtip] = VERDICT[rec.verdict] || VERDICT.open;
  return <div className={`trl is-${r.mode} ${compact ? 'is-compact' : ''}`} aria-busy={busy} data-testid={`rule-${r.key.replace(/\W+/g, '-')}`}>
    <header><b>{r.icon} {r.label}</b><em className={`trl-mode is-${r.mode}`}>{MODE_WORD[r.mode] || r.mode}</em>
      {r.now ? <i className="trl-now" data-tip="coins on the desk this rule hits right now">{r.now} hit now</i> : null}</header>
    <p className="trl-what">Catches: {r.what}.</p>
    <div className="trl-row"><small>DOES</small><div className="m-seg trl-seg" role="group" aria-label="What this rule does">
      {[['off', 'Off', 'ignored'], ['flag', '👀 Flag', 'shown on the coin + graded — changes nothing'], ['rank', '⬇ Rank down', 'the agents rank the coin lower (still buyable)'], ['skip', '✋ Skip', 'the agents never buy it — your own picks still can']].map(([k, l, tip]) =>
        <button key={k} type="button" className={r.mode === k ? 'active' : ''} disabled={!isOwner} onClick={() => set({ mode: k })} data-tip={tip} data-testid={`rule-${r.key.replace(/\W+/g, '-')}-${k}`}>{l}</button>)}</div></div>
    {r.mode === 'rank' || r.mode === 'skip' ? <div className="trl-row"><small>HOW HARD</small><div className="m-seg trl-seg">
      {[['soft', 'Soft −6'], ['normal', 'Normal −12'], ['hard', 'Hard −20']].map(([k, l]) => <button key={k} type="button" className={r.strength === k ? 'active' : ''} disabled={!isOwner} onClick={() => set({ strength: k })}
        data-tip="points off the coin's rank (together with other rules never below ×0.75)">{l}</button>)}</div></div> : null}
    {r.knob ? <div className="trl-row"><small>{r.knob.word.toUpperCase()}</small><div className="m-seg trl-seg">
      {r.knob.options.map(o => <button key={o} type="button" className={r.knob.value === o ? 'active' : ''} disabled={!isOwner} onClick={() => set({ [r.knob.key]: o })}>{o}</button>)}</div></div> : null}
    <p className="trl-rec" data-tip={vtip}><b className={`is-${rec.verdict || 'open'}`}>{vw}</b>
      {rec.n ? <span>{rec.n} coins judged · typical {rec.med > 0 ? '+' : ''}{rec.med}% 30 min later · {rec.up} went up</span> : <span>no coin judged yet — every coin it hits is graded 30 min later</span>}</p>
    {!compact && (r.examples || []).length ? <p className="trl-ex">{r.examples.map(x => <button key={x.mint} type="button" onClick={() => openCoin({ mint: x.mint, symbol: x.sym })} data-tip={x.why}>${x.sym || x.mint.slice(0, 4)}</button>)}</p> : null}
  </div>;
}

// 📣 the socials report: one line per channel with its proof
export function SocialReport({ s }) {
  if (!s || s.grade === 'UNREAD') return <p className="vbd-soc-none">📣 {s?.line || 'not researched yet — the research worker reads the strongest coins first; the links above are the coin\'s own'}</p>;
  return <div className={`vbd-soc is-${s.grade}`} data-testid="soc-report">
    <p className="vbd-soc-head"><b>{s.grade}</b>{s.line}{s.ageMin != null ? <small> · read {s.ageMin}m ago</small> : null}{s.narr ? <small> · story: {s.narr}</small> : null}</p>
    <ul>{(s.ch || []).map(ch => <li key={ch.k} className={`is-${ch.state}`}><i>{ch.icon}</i>
      {ch.url ? <a href={ch.url} target="_blank" rel="noreferrer noopener nofollow">{ch.word}</a> : <span>{ch.word}</span>}
      {ch.age ? <em className={`vbd-age ${ch.young ? 'is-young' : ''}`} data-tip={ch.registrar ? `registrar ${ch.registrar}` : 'how old the account / domain is'}>{ch.young ? '⚠ ' : ''}{ch.age}</em> : null}
      {ch.detail ? <small>{ch.detail}</small> : null}
      {ch.post ? <small className="vbd-post">💬 latest post: “{ch.post}”{ch.postUrl ? <> · <a href={ch.postUrl} target="_blank" rel="noreferrer noopener nofollow">open</a></> : null}</small> : null}</li>)}</ul>
    {(s.flags || []).length ? <p className="vbd-soc-flags">{s.flags.map(f => <span key={f}>{f}</span>)}</p> : null}
  </div>;
}

// 🔗 the coin's socials, always on top: clickable icons (its own links, else its Pump page) + the report's grade and ages in one line
function SocStrip({ c, pos, open, onOpen }) {
  const v = mergedVit(c, pos); const s = v.soc || {}; const ln = { ...(v.links || {}), ...(s.links || {}) };
  const ages = (s.ch || []).filter(ch => ch.age).map(ch => [ch.k, ch.age, ch.young]);
  return <div className="vbd-socs" data-testid="vital-socials"><b>📣</b><SocialIcons r={{ mint: c?.mint, ...ln }} />
    <button type="button" className={`vbd-sgrade is-${s.grade || 'UNREAD'} ${open ? 'is-open' : ''}`} aria-expanded={open} onClick={onOpen} data-testid="vital-soc"
      data-tip="the socials report: each channel with its proof">{s.grade && s.grade !== 'UNREAD' ? s.grade : 'not researched yet'} ▾</button>
    {ages.map(([k, a, y]) => <i key={k} className={`vbd-age ${y ? 'is-young' : ''}`}>{k === 'site' ? '🌐' : '𝕏'} {a}</i>)}</div>;
}

// 🫀 every vital the agents read on THIS coin — tap one: what it is, the line it is judged against, who reads it, what it does
export function VitalBoard({ c, pos, rules, call, isOwner }) {
  const [open, setOpen] = useState(null);
  const tiles = vitalTiles(c, pos); const sc = vitalScore(tiles);
  const v = mergedVit(c, pos);
  const sel = open === 'soc' ? { key: 'soc', icon: '📣', label: 'SOCIALS', value: v.soc?.grade || 'UNREAD', tone: 'unk', line: v.soc?.line || 'not researched yet',
    who: '🔍 Sherlock · ⚖ Devil', effect: 'a CA mismatch / a different X = Devil warning; never a veto by itself', soc: v.soc || null } : tiles.find(t => t.key === open);
  const rule = sel?.rule ? (rules?.rules || []).find(r => r.key === sel.rule) : null;
  return <section className="vbd" data-testid="vital-board">
    <header><b>🫀 VITALS</b><em className={`vbd-word is-${sc.word.replace(/\W+/g, '-').toLowerCase()}`}>{sc.word}</em>
      <span className="vbd-tally"><i className="is-good">{sc.good}</i><i className="is-watch">{sc.watch}</i><i className="is-bad">{sc.bad}</i>{sc.unk ? <i className="is-unk">{sc.unk} unread</i> : null}</span>
      <small>tap a vital</small></header>
    <SocStrip c={c} pos={pos} open={open === 'soc'} onOpen={() => setOpen(open === 'soc' ? null : 'soc')} />
    {VITAL_GROUPS.map(([g, label]) => { const ts = tiles.filter(t => t.group === g); if (!ts.length) return null;
      return <div key={g} className="vbd-group"><small>{label}</small><div className="vbd-tiles">{ts.map((t, i) =>
        <button key={t.key} type="button" className={`vbd-tile is-${t.tone} ${open === t.key ? 'is-open' : ''}`} style={{ '--i': i }} aria-expanded={open === t.key}
          onClick={() => setOpen(open === t.key ? null : t.key)} data-testid={`vital-${t.key.replace(/\W+/g, '-')}`}>
          <i>{t.icon}</i><span><small>{t.label}</small><b>{t.value}</b></span>
          {t.meter != null ? <u className={`vbd-meter ${t.bad ? 'is-risk' : ''}`} aria-hidden="true"><s style={{ transform: `scaleX(${t.meter})` }} /></u> : null}
          {t.split != null ? <u className="vbd-split" aria-hidden="true" data-tip="green = $ bought · red = $ sold"><s style={{ transform: `scaleX(${t.split})` }} /></u> : null}</button>)}</div></div>; })}
    {sel ? <div className={`vbd-detail is-${sel.tone}`} data-testid="vital-detail">
      <p><b>{sel.icon} {sel.label}: {sel.value}</b><button type="button" className="vbd-x" aria-label="close" onClick={() => setOpen(null)}>✕</button></p>
      <dl><dt>LINE</dt><dd>{sel.line}</dd><dt>READ BY</dt><dd>{sel.who}</dd><dt>WHAT IT DOES</dt><dd>{sel.effect}</dd></dl>
      {rule ? <RuleCard r={rule} call={call} isOwner={isOwner} compact /> : null}
      {sel.key === 'soc' ? <SocialReport s={sel.soc} /> : null}
      {c?.mint ? <p className="vbd-acts"><button type="button" className="m-btn" onClick={() => openCoin({ mint: c.mint, symbol: c.symbol, pairAddress: c.pair })}>🪙 Open coin</button>
        <button type="button" className="m-btn" onClick={() => { navigator.clipboard?.writeText(c.mint); toast.success('CA copied'); }}>📋 Copy CA</button></p> : null}
    </div> : null}
  </section>;
}

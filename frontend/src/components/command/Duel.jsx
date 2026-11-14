import React, { useMemo, useState } from 'react';
import '../../styles/duel.css';

// ⚔ AGX-4 · THE TWO-MIND DUEL (owner 2026-11-14): with "Both" on, MIND A and MIND B answer side by side, the strip between them marks where they
// disagree (the call, the numbers, the coins) and how much they share, and one tap picks the winner. The pick is a right-vs-wrong pair in COMP's
// dataset (the stash, category Duels), once: a pick is final.
const YES = ['buy', 'long', 'yes', 'bullish', 'enter', 'ape', 'go', 'up', 'safe', 'legit'];
const NO = ['sell', 'short', 'no', 'skip', 'bearish', 'pass', 'avoid', 'down', 'rug', 'scam', 'wait', 'exit'];
const STOP = new Set('the and for that this with from have will your they them their there what when which about into than then just only also been were very more most some such over its it\'s are was not but can could would should'.split(' '));
const words = t => String(t || '').toLowerCase().match(/[$a-z0-9][a-z0-9.%'-]*/g) || [];
const stance = t => { const w = words(t); for (const x of w) { if (YES.includes(x)) return ['yes', x]; if (NO.includes(x)) return ['no', x]; } return null; };
const nums = t => new Set((String(t || '').match(/[-+]?\$?\d[\d,.]*\s?(?:%|(?:x|k|m|b|h|d|min|sol|usd)(?![a-z]))?/gi) || []).map(s => s.replace(/\s+/g, '').replace(/[.,]$/, '').toLowerCase()));
const coins = t => new Set((String(t || '').match(/\$[a-z][a-z0-9]{1,11}\b/gi) || []).map(s => s.toUpperCase()));
const only = (a, b) => [...a].filter(x => !b.has(x));

/** Pure: where two answers part ways. → { agree 0..1, points: [{ what, a, b }] } */
export function disagree(a, b) {
  const sa = stance(a); const sb = stance(b); const points = [];
  if (sa && sb && sa[0] !== sb[0]) points.push({ what: 'The call', a: sa[1], b: sb[1] });
  else if (!!sa !== !!sb) points.push({ what: 'The call', a: sa ? sa[1] : 'no call', b: sb ? sb[1] : 'no call' });
  const ca = coins(a); const cb = coins(b); if (only(ca, cb).length || only(cb, ca).length) points.push({ what: 'Coins', a: only(ca, cb).join(' ') || '—', b: only(cb, ca).join(' ') || '—' });
  const na = nums(a); const nb = nums(b); if (only(na, nb).length || only(nb, na).length) points.push({ what: 'Numbers', a: only(na, nb).slice(0, 3).join(' · ') || '—', b: only(nb, na).slice(0, 3).join(' · ') || '—' });
  const wa = new Set(words(a).filter(w => w.length > 3 && !STOP.has(w))); const wb = new Set(words(b).filter(w => w.length > 3 && !STOP.has(w)));
  const all = new Set([...wa, ...wb]); const both = [...wa].filter(w => wb.has(w)).length;
  return { agree: all.size ? Math.round((both / all.size) * 100) / 100 : 1, points };
}

/** Both minds' answers to one ask as a duel. `pick` = the saved winner (0 / 1) or undefined; `onPick(i)` files it. */
export default function Duel({ job, pick, onPick }) {
  const minds = (job?.minds || []).slice(0, 2); const [busy, setBusy] = useState(false); const [err, setErr] = useState('');
  const gap = useMemo(() => disagree(minds[0]?.answer, minds[1]?.answer), [minds]);
  const done = pick === 0 || pick === 1;
  const choose = async i => { if (done || busy || !onPick) return; setBusy(true); setErr(''); try { await onPick(i); } catch (e) { setErr(e?.message || 'Could not file it'); } finally { setBusy(false); } };
  const col = i => { const x = minds[i]; const won = done && pick === i; const lost = done && pick !== i;
    return <section className={`dsl-mind is-m${i}${won ? ' is-won' : ''}${lost ? ' is-lost' : ''}`} data-testid={`duel-mind-${i}`}>
      <header><b>MIND {'AB'[i]}</b><small>{String(x.model || '').split('/').pop()}</small>{won ? <em className="dsl-tag is-good">RIGHT</em> : lost ? <em className="dsl-tag is-bad">WRONG</em> : null}</header>
      <p>{x.answer}</p>
      {done ? null : <button type="button" className="m-btn dsl-pick" disabled={busy || !onPick} onClick={() => choose(i)} data-tip={`Mind ${'AB'[i]} answered better: filed as a right-vs-wrong pair in COMP's dataset. A pick is final`} data-testid={`duel-pick-${i}`}>👑 {'AB'[i]} is right</button>}</section>; };
  return <div className={`dsl${done ? ' is-done' : ''}`} data-testid="duel" role="group" aria-label="The two minds' answers, side by side">
    {col(0)}
    <div className="dsl-gap" data-testid="duel-gap"><small>AGREE</small><b className="m-num">{Math.round(gap.agree * 100)}%</b>
      <i className="dsl-meter" aria-hidden="true"><u style={{ transform: `scaleY(${gap.agree})` }} /></i>
      {gap.points.length ? <ul>{gap.points.map((p, n) => <li key={p.what} style={{ '--i': n }} data-testid={`duel-point-${n}`}><em>{p.what}</em><span><s className="is-a">{p.a}</s><s className="is-b">{p.b}</s></span></li>)}</ul>
        : <p>Same call, same numbers</p>}
      {done ? <strong className="dsl-filed" data-testid="duel-filed">✓ Pair filed · COMP dataset</strong> : null}
      {err ? <strong className="dsl-err" role="alert">{err}</strong> : null}</div>
    {col(1)}</div>;
}

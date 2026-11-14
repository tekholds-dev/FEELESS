import React, { useMemo } from 'react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

// 🏁 AGX-6 · COMP TRAINING AS A RACE (owner 2026-11-14): every exam is the SAME held-out proofs for every model — COMP, the untouched base,
// the owner's OSSY + G4 (each on its own LM Studio), the flagships with a saved key — so its score against all of them, exam after exam,
// makes "COMP #1" a visible fact (or shows how far off it is). Lines = exams so far; the board below is the live one.
const COLOR = { comp: 'var(--m-accent)', comp_mem: 'var(--m-accent)', base: 'var(--m-dim)', baseline: 'var(--m-mute)', ossy: 'var(--m-warn)', g4: 'var(--m-danger)' };
const ours = id => id === 'comp' || id === 'comp_mem';

/** Pure: the race history (+ the exam on screen, if it is newer) → chart rows, the series, and the latest standing. */
export function raceRead(race, exam) {
  const rows = [...(race || [])];
  const live = (exam?.examinees || []).filter(e => e.score?.n);
  const at = exam?.done || exam?.at || 0;
  if (live.length && !rows.some(r => r.at === at)) rows.push({ at, n: exam.n, live: !exam.done, scores: Object.fromEntries(live.map(e => [e.id, e.score.acc])), names: Object.fromEntries(live.map(e => [e.id, e.name])), kinds: Object.fromEntries(live.map(e => [e.id, e.kind])) });
  rows.sort((a, b) => (a.at || 0) - (b.at || 0));
  const names = {}; const kinds = {}; rows.forEach(r => { Object.assign(names, r.names || {}); Object.assign(kinds, r.kinds || {}); });
  const ids = Object.keys(names).sort((a, b) => (ours(b) - ours(a)) || a.localeCompare(b));
  const data = rows.map((r, i) => ({ x: i + 1, at: r.at, live: !!r.live, ...Object.fromEntries(Object.entries(r.scores || {}).map(([k, v]) => [k, Math.round(v * 1000) / 10])) }));
  const last = rows[rows.length - 1];
  const raw = last ? Object.entries(last.scores || {}).filter(([k]) => kinds[k] !== 'baseline') : [];
  const best = raw.filter(([k]) => ours(k)).sort((a, b) => b[1] - a[1])[0];   // COMP's best variant stands for COMP: it never races itself
  const board = [...raw.filter(([k]) => !ours(k)), ...(best ? [best] : [])].sort((a, b) => (b[1] - a[1]) || (ours(b[0]) - ours(a[0])));
  const ci = board.findIndex(([k]) => ours(k)); const comp = ci >= 0 ? board[ci] : null; const lead = board[0];
  const p = v => `${Math.round(v * 100)}%`;
  const say = !last ? '' : !comp ? 'COMP has not sat an exam yet: train it, then run the exam.'
    : ci === 0 ? `COMP is #1 of ${board.length} on ${rows.length > 1 ? `exam ${rows.length}` : 'the exam'} (${p(comp[1])})${board[1] ? `, ahead of ${names[board[1][0]]} at ${p(board[1][1])}` : ''}.`
    : `COMP is #${ci + 1} of ${board.length} (${p(comp[1])}): ${names[lead[0]]} leads at ${p(lead[1])}, ${Math.round((lead[1] - comp[1]) * 100)} points ahead.`;
  const all = data.flatMap(d => ids.map(id => d[id]).filter(v => v != null)); const lo = all.length ? Math.max(0, Math.floor((Math.min(...all) - 10) / 10) * 10) : 0;
  return { data, ids, names, kinds, say, lo, rank: ci >= 0 ? ci + 1 : null, of: board.length, exams: rows.length };
}

const tipStyle = { background: 'var(--m-surface)', border: '1px solid var(--m-line-hi)', borderRadius: 8, fontSize: 11, color: 'var(--m-text)' };
export function CompRace({ race, exam, running }) {
  const r = useMemo(() => raceRead(race, exam), [race, exam]);
  if (!r.data.length) return null;
  return <div className={`crc${running ? ' is-live' : ''}`} data-testid="comp-race">
    <p className={`crc-say${r.rank === 1 ? ' is-top' : ''}`} data-testid="comp-race-say">{r.rank === 1 ? <b className="crc-crown" aria-hidden="true">#1</b> : r.rank ? <b className="crc-crown is-off" aria-hidden="true">#{r.rank}</b> : null}{r.say}</p>
    <div className="crc-chart" data-tip="% right on the same held-out proofs, one point per exam. COMP's own lines are bold"><ResponsiveContainer width="100%" height={190}>
      <LineChart data={r.data} margin={{ top: 8, right: 10, bottom: 0, left: 0 }}>
        <CartesianGrid vertical={false} stroke="var(--m-line)" />
        <XAxis dataKey="x" tick={{ fontSize: 10, fill: 'var(--m-dim)' }} tickLine={false} axisLine={false} tickFormatter={x => `exam ${x}`} allowDecimals={false} />
        <YAxis domain={[r.lo, 100]} tick={{ fontSize: 10, fill: 'var(--m-dim)' }} tickLine={false} axisLine={false} unit="%" width={44} />
        <Tooltip contentStyle={tipStyle} formatter={(v, k) => [`${v}%`, r.names[k] || k]} labelFormatter={x => { const d = r.data[x - 1]; return d?.at ? `exam ${x} · ${new Date(d.at * 1000).toLocaleDateString()}${d.live ? ' · live' : ''}` : `exam ${x}`; }} />
        {r.ids.map(id => <Line key={id} type="monotone" dataKey={id} name={r.names[id]} stroke={COLOR[id] || (r.kinds[id] === 'flagship' ? 'var(--m-text)' : 'var(--m-dim)')}
          strokeWidth={ours(id) ? 3 : 1.5} strokeDasharray={id === 'comp_mem' ? '5 4' : r.kinds[id] === 'baseline' ? '2 4' : undefined} dot={{ r: ours(id) ? 4 : 2.5 }} connectNulls isAnimationActive={false} />)}
      </LineChart></ResponsiveContainer></div>
    <ul className="crc-key">{r.ids.map(id => <li key={id} className={ours(id) ? 'is-comp' : ''} style={{ '--c': COLOR[id] || (r.kinds[id] === 'flagship' ? 'var(--m-text)' : 'var(--m-dim)') }}><i aria-hidden="true" />{r.names[id]}</li>)}</ul>
  </div>;
}

// 🤖 ONE MEANING OF A DECISION for every HQ surface (the coin board, the agents' screens, the office board, the room, the
// seat board, the swap-in agents list). A row of the Agents tab carries the KERNEL's decision as `k` (backend `_paper_view`):
//   k = { status: READY | CONTENDING | TRACKING | ORDER_PENDING | HELD | EXIT_PENDING | CLOSED, rank, why, trigger, narrative,
//         devil: [[id, INFO | WARNING | STRONG_WARNING | HARD_VETO, words]], hard, size, unknown, courier }
// A kernel candidate (office.kernel.candidates[]) has the same fields at its top level. Nothing here re-decides anything.
//
// ⚖ DEVIL, everywhere: an ordinary concern is a WARNING that lowers a rank → "⚠ DEVIL WARNS". Only the hard wall blocks → "✕ BLOCKED".
// No surface may say "objected" for a warning: it reads as a veto, and Devil does not veto.
//
// The practice desk's own words (`trigger` / `devil` / `go` / `why.lean` on a row) are a graded PAPER record: `practiceOf` reads them
// for the expanded row only — they never decide what a row's state is.
export const pct = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`);
export const tone = v => (v == null ? '' : v > 0 ? 'm-pos' : v < 0 ? 'm-neg' : '');

export const DEVIL_WORD = { veto: '✕ BLOCKED', warn: '⚠ DEVIL WARNS', clear: 'NO OBJECTION' };
export const DEVIL_CLS = { veto: 'is-veto', warn: 'is-warn', clear: 'is-pass' };
const isHard = o => (Array.isArray(o) ? o[1] : o?.severity) === 'HARD_VETO' || o?.hard === true;
// Devil's view of ANYTHING that carries his opinion: a kernel candidate / a row's `k` (devil = [[id, severity, words]] + hard), or the
// office's case block (devil = { verdict, objections: [{ rule, evidence, severity, hard }] }). → { verdict, word, cls, objections, first }
export function devilOf(x) {
  const src = x?.k || x || {}; const dv = src.devil;
  let objs = []; let verdict = 'clear';
  if (Array.isArray(dv)) { objs = dv.map(o => ({ rule: o[0], severity: o[1], evidence: o[2], hard: o[1] === 'HARD_VETO' })); verdict = src.hard || objs.some(isHard) ? 'veto' : objs.length ? 'warn' : 'clear'; }
  else if (dv && typeof dv === 'object') { objs = (dv.objections || []).map(o => ({ ...o, hard: isHard(o) })); verdict = dv.verdict === 'veto' || objs.some(isHard) ? 'veto' : dv.verdict === 'warn' || objs.length ? 'warn' : 'clear'; }
  return { verdict, word: DEVIL_WORD[verdict], cls: DEVIL_CLS[verdict], objections: objs, first: objs[0] || null };
}

// the kernel decision a row / candidate carries (null = the kernel has not judged it: a practice-only row)
export const kOf = x => (x?.k ? x.k : x?.status && x?.rank != null ? x : null);
// ONE state per coin, from the kernel: go (READY) · warn (CONTENDING with Devil warnings) · wait (CONTENDING) · obj (the hard wall) ·
// skip (TRACKING: data pending / outside the universe) · held · pending (the keeper is buying it)
export function rowState(x) {
  const k = kOf(x);
  if (!k) return 'skip';
  if (k.status === 'READY') return 'go';
  if (k.status === 'HELD' || k.status === 'EXIT_PENDING') return 'held';
  if (k.status === 'ORDER_PENDING') return 'pending';
  const dv = devilOf(k);
  if (dv.verdict === 'veto') return 'obj';
  if (k.status === 'CONTENDING') return dv.verdict === 'warn' ? 'warn' : 'wait';
  return 'skip';
}
export const VERD = { go: '🟢 READY', warn: '⚠ DEVIL WARNS', obj: '✕ BLOCKED', wait: 'CONTENDING', skip: 'TRACKING', held: '💼 HELD', pending: '⏳ ORDER PENDING' };
export const rowWhy = x => { const k = kOf(x); const st = rowState(x); const dv = devilOf(k || {});
  if (!k) return 'not judged by the kernel this pass';
  return st === 'obj' || st === 'warn' ? (dv.first?.evidence || dv.word) : (k.why || k.narrative || ''); };
// the four brain-side desks' words on a coin, from the kernel (📊 measured move · 🔍 evidence known / researching · ⏱ timing · ⚖ Devil)
export const pipsOf = x => { const k = kOf(x) || {}; const d5 = Number(x?.nums?.d5); const dv = devilOf(k); const unk = k.unknown || [];
  return [['tally', '📊', Number.isFinite(d5) ? (d5 >= 0 ? 'up' : 'dn') : 'flat', `Tally: ${pct(Number.isFinite(d5) ? d5 : null)} in 5 min`],
    ['sherlock', '🔍', unk.length ? 'wait' : 'go', unk.length ? `Sherlock: researching ${unk.join(', ')} (unknown is not a rejection)` : 'Sherlock: evidence complete'],
    ['trigger', '⏱', k.trigger === 'ENTER' ? 'go' : k.trigger === 'NO' ? 'no' : 'wait', `Trigger: ${k.trigger || '—'}${k.narrative ? ` — ${k.narrative}` : ''}`],
    ['devil', '⚖', dv.verdict === 'veto' ? 'no' : dv.verdict === 'warn' ? 'warn' : 'go', `Devil: ${dv.word}${dv.first ? ` — ${dv.first.evidence}` : ''}`]]; };
export const READY_MIN = 120;   // mirrors trench_kernel.brain.READY_MIN: the rank a candidate needs (with Trigger ENTER) to be READY
export const rankFill = rank => Math.max(0, Math.min(1, (Number(rank) || 0) / (2 * READY_MIN)));
// 📝 the practice desk's own graded paper call on a row (display only)
export const CALL = { enter: ['ENTER', 'is-go'], wait: ['WAIT', 'is-wait'], skip: ['SKIP', 'is-no'] };
export const practiceOf = x => (x?.trigger ? { call: (CALL[x.trigger[0]] || ['—', ''])[0], why: x.trigger[1] || '', devil: x.devil?.[0] === 'object' ? 'paper Devil warned' : x.devil?.[0] === 'agree' ? 'paper Devil: nothing against it' : '', devilWhy: x.devil?.[1] || '',
  go: !!x.go, lean: Number(x.why?.lean) || 0, drivers: x.why?.drivers || [] } : null);

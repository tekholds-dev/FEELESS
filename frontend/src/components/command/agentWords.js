import { usd } from './OfficeBoard';

// 🗣 The words the Agents cockpit uses for each desk — kept from the retired 3D office (OfficeRoom, 2026-10-12): the agents' colours,
// what each desk is doing this pass (`activityOf`, read from the one office payload) and the header ticker. Nothing here fetches.
export const AG = { tally: '#1fd178', sherlock: '#a07bff', weather: '#4fd8ff', trigger: '#f5c451', devil: '#ff6b86', warden: '#6c9bff', courier: '#ffb02e', reaper: '#c77dff', archivist: '#9fb3c8', judge: '#ffd166' };
const URGENT = ['EXIT', 'TAKE PROFIT', 'PROTECT', 'HOLD 5 MORE', 'HOLD'];

// the position Reaper is most pressed on (an exit before a take before a protect before a hold)
export const hotPosition = positions => [...(positions || [])].sort((a, b) => URGENT.indexOf(a.decision) - URGENT.indexOf(b.decision) || (a.nextReview ?? 1e9) - (b.nextReview ?? 1e9))[0] || null;
const STAGE_ACT = { PASS: 'PASS', DONE: 'PASS', WAITING: 'WAIT', WORKING: 'REVIEW', WARN: 'WARNS', VETO: 'VETO', ERROR: 'ERROR', STALE: 'STALE' };
export function activityOf(key, o) {
  const st = (o?.pipeline || []).find(s => s.agent === key); const stage = [STAGE_ACT[st?.state] || 'WAIT', st?.word || 'nothing this pass'];
  if (key === 'tally') return (o?.office?.coins ?? 0) > 0 && st?.state !== 'STALE' ? ['SCAN', `${o.office.coins} coins read this pass`] : stage;
  if (key === 'warden' && o?.currentCase?.warden) { const w = o.currentCase.warden; return [w.veto ? 'VETO' : 'SIZED', `${usd(w.requested)} → ${usd(w.allowed)} (${w.decided})`]; }
  if (key === 'courier') { const x = o?.execution || {}; const la = o?.mission?.lastAction;
    if (x.pending) return ['SUBMITTED', `${x.pending.side} $${x.pending.sym} in flight`];
    if (x.health === 'BAD') return ['VETO', `execution BAD — ${x.why || 'no new money until sends land'}`];
    if (la?.result?.state === 'confirmed' && o?.at && o.at - (la.result.at || la.at) <= 900) return ['CONFIRMED', `$${la.sym} ${la.move} confirmed on the ledger`];
    return stage; }
  if (key === 'reaper') { const p = hotPosition(o?.positions); if (!p) return ['WAIT', 'no open position'];
    const d = p.decision || p.state; return [d === 'TAKE PROFIT' ? 'TAKE' : d === 'EXIT' ? 'EXIT' : d === 'PROTECT' ? 'PROTECT' : 'HOLD', `$${p.symbol}: ${p.rule} — ${p.evidence}`]; }
  if (key === 'archivist') return (o?.office?.cases ?? 0) > 0 ? ['LOGGING', `${o.office.cases} case file${o.office.cases === 1 ? '' : 's'} filed this pass`] : stage;
  if (key === 'judge') return (o?.judge?.rulings ?? 0) > 0 ? ['JUDGE REVIEW', `${o.judge.rulings} real exits reviewed · on probation: ${(o.judge.probation || []).join(', ') || 'nobody'}`] : stage;
  return stage;
}
// where the current candidate stands: the first desk that has not passed it
export const focusOf = o => o?.queue?.[0]?.at || (o?.pipeline || []).find(s => !['PASS', 'DONE'].includes(s.state) && !['archivist', 'judge'].includes(s.agent))?.agent || 'tally';
export function ticker(o) {
  const names = Object.fromEntries((o?.agents || []).map(a => [a.key, a.name])); const c = o?.currentCase; const p = hotPosition(o?.positions);
  if (p && ['EXIT', 'TAKE PROFIT', 'PROTECT'].includes(p.decision)) return `Reaper: ${p.decision} $${p.symbol}${p.rule ? ` — ${p.rule}` : ''}`;
  if (c) { const at = focusOf(o); const st = (o.pipeline || []).find(s => s.agent === at); return `$${c.symbol} at ${names[at] || at} — ${st?.state || ''}: ${st?.word || ''}`; }
  return p ? `Reaper: ${p.decision || p.state || 'HOLD'} $${p.symbol}` : 'no candidate this pass';   // never "Reaper: undefined"
}

// candles → SVG geometry. `levels` = [{ px, label, cls }] drawn as lines; everything is scaled to the candles AND the levels in view.

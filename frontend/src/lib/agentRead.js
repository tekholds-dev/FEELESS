// 🤖 How one coin of an agent pass READS (pure, tested through AgentDesk.test): shared by the coin board (AgentDesk) and the agents' screens
// (AgentScreens). A row = {symbol, mint, nums: {d5, pace, buy}, why: {lean, drivers: [[key, weight, words]]}, trigger: [call, why], devil: [verdict, why], go}.
export const pct = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`);
export const tone = v => (v == null ? '' : v > 0 ? 'm-pos' : v < 0 ? 'm-neg' : '');
export const CALL = { enter: ['ENTER', 'is-go'], wait: ['WAIT', 'is-wait'], skip: ['SKIP', 'is-no'] };
export const VERDICT = { agree: ['agrees', 'is-go'], object: ['objects', 'is-no'], '—': ['—', ''] };
export const rowState = x => (x.go ? 'go' : x.trigger?.[0] === 'enter' ? 'obj' : x.trigger?.[0] === 'skip' ? 'skip' : 'wait');
export const VERD = { go: '🟢 GO', obj: '✕ OBJECTED', wait: 'WAIT', skip: 'SKIP' };
export const rowWhy = x => { const st = rowState(x); const top = (x.why?.drivers || [])[0];
  return st === 'go' ? (top ? top[2] : 'all four agree') : st === 'obj' ? (x.devil?.[1] || 'Devil objects') : (x.trigger?.[1] || (top ? top[2] : 'nothing moving it')); };
export const pipsOf = x => { const d5 = Number(x.nums?.d5); const lean = Number(x.why?.lean) || 0; const t = x.trigger?.[0]; const v = x.devil?.[0];
  return [['tally', '📊', Number.isFinite(d5) ? (d5 >= 0 ? 'up' : 'dn') : 'flat', `Tally: ${pct(Number.isFinite(d5) ? d5 : null)} in 5 min`],
    ['sherlock', '🔍', lean > 0 ? 'up' : lean < 0 ? 'dn' : 'flat', `Sherlock: lean ${lean.toFixed(1)}`],
    ['trigger', '⏱', t === 'enter' ? 'go' : t === 'skip' ? 'no' : 'wait', `Trigger: ${(CALL[t] || ['—'])[0]}${x.trigger?.[1] ? ` — ${x.trigger[1]}` : ''}`],
    ['devil', '⚖', v === 'agree' ? 'go' : v === 'object' ? 'no' : 'idle', `Devil: ${(VERDICT[v] || ['not asked'])[0]}${x.devil?.[1] ? ` — ${x.devil[1]}` : v === 'agree' || v === 'object' ? '' : ' (only ENTER calls are argued)'}`]]; };
export const leanFill = (lean, bar) => Math.max(0, Math.min(1, Math.abs(Number(lean) || 0) / (2 * Math.max(0.5, Number(bar) || 1.5))));

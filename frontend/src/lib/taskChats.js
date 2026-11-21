// 🧵 Slice 35 · task chats: the words and numbers a task card / task chat shows, from the server's own task (fc_taskchat). Pure.

export const STATE_WORD = { queued: 'queued', starting: 'starting', working: 'working', waiting: 'waiting for you', paused: 'paused', done: 'done', failed: 'failed', stopped: 'stopped' };
export const ENDED = ['done', 'failed', 'stopped'];
export const isLive = s => ['queued', 'starting', 'working', 'paused', 'waiting'].includes(s);
export const tone = s => (s === 'waiting' ? 'warn' : s === 'failed' ? 'bad' : s === 'done' ? 'ok' : isLive(s) ? 'live' : '');

/** 75 → "1m 15s" · 9 → "9s". */
export function elapsed(secs) {
  const s = Math.max(0, Math.round(Number(secs) || 0));
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60); return m < 60 ? `${m}m ${s % 60}s` : `${Math.floor(m / 60)}h ${m % 60}m`;
}
export const usd = v => { const n = Number(v); return !Number.isFinite(n) ? '—' : n < 0.01 ? `$${n.toFixed(4)}` : `$${n.toFixed(2)}`; };

/** "/task …" typed in a chat → the brief, else null. */
export function taskCommand(text) {
  const m = /^\/task\s+([\s\S]{3,})$/i.exec(String(text || '').trim());
  return m ? m[1].trim() : null;
}

/** The scope a proof chat splits into: "pow:<folder id>" or just "pow" (its newest folder). */
export const scopeKey = (kind, ref) => (kind && kind !== 'desk' ? `${kind}${ref ? `:${ref}` : ''}` : 'desk');

/** Does a card belong to this scope? A kind-only scope takes every task of that kind. */
export function inScope(card, scope) {
  const [k, ref = ''] = String(scope || 'desk').split(':');
  const s = card?.scope || {};
  return s.kind === k && (!ref || s.ref === ref);
}

/** Thought rows for one checklist step (-1 = the plan), each "Thought for N s". */
export const thoughtsFor = (task, step) => (task?.thoughts || []).filter(t => t.step === step);
export const thoughtLabel = t => `Thought for ${Math.max(1, Math.round(Number(t?.s) || 0))} s`;

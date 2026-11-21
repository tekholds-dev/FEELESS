// 🖥 The Desk look's data: everything a desk shows, built from the agent's real state (`op: state`), its pool and its Approve inbox. Pure.
// Nothing here makes up a number: a missing field stays missing and the widget says it is empty.

const num = v => (v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v));
const usd = v => { const n = num(v); return n == null ? '—' : `$${n < 1 ? n.toFixed(n < 0.01 ? 4 : 2) : n >= 1000 ? `${(n / 1000).toFixed(1)}K` : n.toFixed(2)}`; };
const pct = v => { const n = num(v); return n == null ? '—' : `${n >= 0 ? '+' : '−'}${Math.abs(n).toFixed(1)}%`; };
const short = m => String(m || '').split('/').pop().split(':')[0];
export { usd as deskUsd, pct as deskPct };

// The stages each proof walks through, and where a running one is
export const STAGES = {
  pow: ['propose', 'split', 'scout', 'choose', 'buy', 'watch', 'sell'],
  pop: ['read', 'call', 'agree', 'open', 'exit', 'filed'],
  pob: ['read', 'pick', 'agree', 'slip', 'watch', 'graded'],
  poc: ['trend', 'ideas', 'make', 'check', 'approve', 'post'],
  ps: ['brief', 'build', 'check', 'review', 'filed'],
  poe: ['find', 'bid', 'approve', 'deliver', 'paid'],
};
export const KIND = { pow: ['⛏', 'PoW', 'pow'], pop: ['📉', 'PoP', 'pop'], pob: ['🎲', 'PoB', 'bids'], poc: ['📣', 'PoC', 'poc'], ps: ['💻', 'PoStatic', 'postatic'], poe: ['📊', 'PoEco', 'poe'] };
const FOLDERS = { pow: 'powFolders', pop: 'popFolders', pob: 'pobFolders', poc: 'pocFolders', ps: 'psFolders', poe: 'poeFolders' };

function stageOf(k, f) {
  const list = STAGES[k]; if (!list) return [-1, ''];
  if (f.status === 'closed' || f.closedAt) return [list.length, 'filed'];
  if (k === 'pow') { const ph = f.phase === 'research' ? 'watch' : f.phase === 'decide' ? 'choose' : f.phase; const i = list.indexOf(ph); return [i < 0 ? 0 : i, ph || 'propose']; }
  if (k === 'pop') { const i = f.proposal ? 2 : f.side ? 4 : 0; return [i, list[i]]; }
  if (k === 'pob') { const i = f.kalshi?.orderId ? 4 : (f.calls || []).length ? 2 : 0; return [i, list[i]]; }
  const i = Math.max(0, list.indexOf(String(f.stage || ''))); return [i, list[i]];
}
function mindsOf(f) {
  const ran = f?.stamp?.ran || f?.record?.ran || f?.ran; if (Array.isArray(ran) && ran.length) return [...new Set(ran.map(r => short(typeof r === 'string' ? r : (r.answered || [])[0] || r.asked || r.model || r.mind || '')).filter(Boolean))].slice(0, 3);
  const calls = (f?.calls || []).map(c => short(c.model || c.name)).filter(Boolean); return [...new Set(calls)].slice(0, 3);
}
/** One status row per running or recent proof: kind, title, stage (index / of), minds, cost, next step and whether it waits for you. Running first. */
export function proofStatus(d, approvals = [], n = 6) {
  if (!d) return [];
  const live = [['pow', d.powFolder], ['pop', d.popFolder], ['pob', d.pobRun]].filter(([, f]) => f && f.id);
  const liveIds = new Set(live.map(([, f]) => f.id));
  const filed = Object.entries(FOLDERS).flatMap(([k, key]) => (d[key] || []).filter(f => f && f.id && !liveIds.has(f.id)).map(f => [k, f]));
  filed.sort((a, b) => (num(b[1].closedAt || b[1].at) || 0) - (num(a[1].closedAt || a[1].at) || 0));
  const waitingFor = new Set((approvals || []).filter(r => r.state === 'waiting').map(r => r.ref || r.proof).filter(Boolean));
  return [...live.map(x => [...x, true]), ...filed.map(x => [...x, false])].slice(0, n).map(([k, f, running]) => {
    const [at, word] = stageOf(k, f); const of = (STAGES[k] || []).length; const [e, label, win] = KIND[k];
    const waiting = waitingFor.has(f.id) || f.waiting === true || (k === 'poe' && f.stage === 'approve') || (k === 'poc' && f.status === 'approve');
    const next = waiting ? 'waits for your approve' : running ? (STAGES[k] || [])[Math.min(at + 1, of - 1)] || 'files' : f.review?.verdict ? `Collective: ${f.review.verdict}` : 'filed';
    return { k, e, label, win, id: f.id, n: f.n ?? null, title: String(f.topic || (f.sym ? `$${f.sym}` : '') || f.name || f.title || label).slice(0, 80), running, stage: word, at, of,
      minds: mindsOf(f), cost: num(f.cost), next, waiting, test: !!(f.test || f.isTest), at_: num(f.closedAt || f.at), roe: num(f.roePct ?? f.net) };
  });
}

/** The Collective's agree meters + verdict, from the newest reviewed proof (OSSY / G4 scores as the server filed them). null = none reviewed yet. */
export function collectiveOf(d) {
  const rows = Object.values(FOLDERS).flatMap(k => d?.[k] || []).filter(f => f?.review?.by);
  rows.sort((a, b) => (num(b.closedAt || b.at) || 0) - (num(a.closedAt || a.at) || 0));
  const f = rows[0]; if (!f) return null;
  const by = Object.entries(f.review.by).map(([k, v]) => ({ k: k.toUpperCase(), score: num(v.score), pass: v.verdict === 'pass' }));
  return { by, verdict: f.review.verdict || (by.every(b => b.pass) ? 'pass' : 'fail'), agree: f.review.agree !== false, on: String(f.topic || (f.sym ? `$${f.sym}` : '') || 'its last proof').slice(0, 40) };
}

/** Paper positions open right now (its PoP paper trade + a PoW hold), each with its live return. */
export function paperOf(d) {
  const out = []; const pop = d?.popFolder; const pow = d?.powFolder;
  if (pop?.id) out.push({ k: 'pop', name: `${pop.market || 'PoP'} ${pop.side || ''}`.trim(), size: pop.sizeUsd ?? pop.size ?? null, roe: num(pop.roePct) });
  if (pow?.id && pow.sym && ['buy', 'watch', 'research', 'sell'].includes(pow.phase)) out.push({ k: 'pow', name: `$${pow.sym}`, size: pow.sizeSol ?? pow.sol ?? null, roe: num(pow.pnlPct ?? pow.roePct) });
  return out;
}

/** The clip farm queue: ready / making / posted counts from its PoC folders. */
export function clipQueue(d) {
  const files = (d?.pocFolders || []).flatMap(f => f.clips || f.files || []);
  const ready = files.filter(x => x && (x.status === 'ready' || x.url) && !x.posted).length; const making = files.filter(x => x && (x.status === 'rendering' || x.status === 'running' || x.status === 'queued')).length;
  const posted = files.filter(x => x?.posted).length;
  return { ready, making, posted, folders: (d?.pocFolders || []).length };
}

/** PoEco: open bids, what waits for you, and the newest job. */
export function ecoOf(d, approvals = []) {
  const rows = d?.poeFolders || []; const open = rows.filter(f => f.status !== 'closed');
  const bidsUsd = open.reduce((s, f) => s + (num(f.bid ?? f.listing?.payUsd) || 0), 0);
  const wait = (approvals || []).filter(r => r.state === 'waiting').length;
  return { n: rows.length, open: open.length, bidsUsd, wait, top: open[0] ? { title: String(open[0].topic || open[0].listing?.title || 'a job').slice(0, 40), pay: num(open[0].bid ?? open[0].listing?.payUsd) } : null };
}

/** Its own filed proofs today (local day): how many, how many won. */
export function todayOf(d, now = Date.now()) {
  const day = new Date(now).toDateString();
  const rows = Object.values(FOLDERS).flatMap(k => d?.[k] || []).filter(f => { const t = num(f?.closedAt || f?.at); return t && new Date(t * 1000).toDateString() === day; });
  const won = rows.filter(f => (num(f.roePct ?? f.net) || 0) > 0 || f.graded === 'right' || f.review?.verdict === 'pass').length;
  return { n: rows.length, won, open: rows.filter(f => f.status !== 'closed').length };
}

// 💬 CHAT COMMANDS (owner 2026-11-20: proofs "can be started, steered, paused and approved by chat command … each through the same wired path as the buttons").
// → one action, or null for a plain ask. The desk runs each action through the very op its button calls.
const START = { pow: 'file a PoW', pop: 'file a perp', pob: 'file a pob', poc: 'file a poc', pos: 'file a pos', ps: 'file a pos', poe: 'file a poeco' };
// the ✕ on a running proof's chip calls exactly these (CatWorkbench STOPPABLE)
export const STOP_OPS = { pow: ['ask', { text: 'stop PoW' }], pop: ['pop', { job: 'stop' }] };
export function deskCommand(text, { approvals = [] } = {}) {
  const t = String(text || '').trim(); if (!t) return null;
  const wait = (approvals || []).filter(r => r.state === 'waiting');
  let m = /^\/?(approve|decline|reject)\s*(?:bid|row|#)?\s*(\d+)?\s*$/i.exec(t);
  if (m) { const i = m[2] ? Number(m[2]) - 1 : 0; const row = wait[i]; const yes = /approve/i.test(m[1]);
    return row ? { kind: 'decide', id: row.id, yes, what: row.what } : { kind: 'say', text: wait.length ? `There are ${wait.length} waiting: say ${yes ? 'approve' : 'decline'} 1 to ${wait.length}.` : 'Nothing is waiting for your approve.' }; }
  m = /^\/(pow|pop|pob|poc|pos|ps|poe)\b\s*(.*)$/i.exec(t);
  if (m) { const k = m[1].toLowerCase(); return { kind: 'ask', text: `${START[k]}${m[2] ? ` ${m[2].trim()}` : ''}`.trim(), proof: k }; }
  m = /^\/(stop|pause)\s+(pow|pop|pob)\s*$/i.exec(t);
  if (m) { const k = m[2].toLowerCase(); return STOP_OPS[k] ? { kind: 'op', op: STOP_OPS[k][0], extra: STOP_OPS[k][1], proof: k } : { kind: 'say', text: 'A PoB ends when its games are final.' }; }
  if (/^\/(stop|pause)\s*$/i.test(t)) return { kind: 'stop' };
  m = /^\/open\s+(pow|pop|pob|bids|poc|postatic|pos|ps|poe|vault|browser|stash|tests|proofs)\s*$/i.exec(t);
  if (m) { const w = { pob: 'bids', pos: 'postatic', ps: 'postatic' }[m[1].toLowerCase()] || m[1].toLowerCase(); return { kind: 'open', win: w }; }
  m = /^\/(image|img|video)\s+(.+)$/i.exec(t);
  if (m) return { kind: 'media', media: /video/i.test(m[1]) ? 'video' : 'image', prompt: m[2].trim() };
  if (/^\/(proofs|picker)\s*$/i.test(t)) return { kind: 'picker' };
  return null;
}
export const DESK_HINTS = [['/poc ', 'Start a PoC'], ['approve 1', 'Approve the first waiting'], ['/image ', 'Make an image'], ['/stop pow', 'Stop the PoW']];

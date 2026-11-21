// 🔤 A coin's on-chain symbol shown readably (owner 2026-11-21: "$▇▇▇WIF" drew as a black block on the Fuse arena). Block / box-drawing /
// geometric-shape / zero-width / control characters are dropped, and a symbol that had any is marked "≈" — a look-alike, never passed off
// as the real coin (≈WIF is not WIF). Mints stay the key for everything that trades; only the words on screen change.
const ODD = /[─-◿​-‏⁠﻿\p{Cc}]/gu;
export const symText = s => { const t = String(s ?? ''); const c = t.replace(ODD, '').trim(); return c === t ? t : `≈${c || '?'}`; };
/** Every `symbol` string in a payload, made readable (arrays and objects, any depth). */
export function normSyms(x, depth = 0) {
  if (depth > 8 || x == null || typeof x !== 'object') return x;
  if (Array.isArray(x)) return x.map(v => normSyms(v, depth + 1));
  const o = {}; for (const [k, v] of Object.entries(x)) o[k] = k === 'symbol' && typeof v === 'string' ? symText(v) : normSyms(v, depth + 1); return o;
}

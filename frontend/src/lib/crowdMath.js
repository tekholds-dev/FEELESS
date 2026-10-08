// 🧍 Pure helpers of the ringside crowd (no three.js, so they are unit-tested). See lib/miniCrowd.js.
/** Where each walker of `n` wants to stand: gathered under the LEADING card (a = left, b = right), spread along the whole foot when level. */
export function crowdTargets(lead, width, n) {
  const half = width / 2, out = [];
  for (let i = 0; i < n; i++) {
    const slot = (i + 0.5) / n;
    out.push(lead === 'a' ? -half * 0.82 + slot * half * 0.72 : lead === 'b' ? half * 0.1 + slot * half * 0.72 : -half * 0.8 + slot * half * 1.6);
  }
  return out;
}
export const boneClass = n => (/^pelvis/.test(n) ? 'pelvis' : /^spine/.test(n) ? 'spine' : /neck|head/i.test(n) ? 'head' : /clavicle|upperarm|lowerarm/.test(n) ? 'arm' : /hand|thumb|index|middle|ring|pinky/.test(n) ? 'hand' : /thigh|calf/.test(n) ? 'leg' : /foot|ball/.test(n) ? 'foot' : 'other');
export function garmentPick(kind, spec, cls, h, ax) {   // h = height 0..1, ax = sideways offset / height (rest T-pose)
  if (kind === 'top') return h < 0.86 && ((h > 0.515 && (cls === 'spine' || cls === 'pelvis')) || (cls === 'arm' && ax < spec.arm));
  if (kind === 'pants') return cls === 'pelvis' || (cls === 'spine' && h < 0.58) || (cls === 'leg' && h > spec.minH);
  return cls === 'foot' || (cls === 'leg' && h < 0.05);
}


/** The people for one fight's walkers: each fight takes the next `n` of the list (real people only; fewer people → the rest stay anonymous, null). */
export const pickPeople = (people, fight, n) => Array.from({ length: n }, (_, i) => (people || [])[fight * n + i] || null);

/** The line ABOVE a name: the last Fuse card they bought, else what brought them here. '' = nothing honest to say. */
export const tagTop = p => (!p ? '' : p.lastCard ? `bought ${p.lastCard}` : p.why === 'backer' ? 'backed a fight' : '');

/** Clamp a tag's x so it never leaves the box (half = half the tag width in px). */
export const clampTag = (x, W, half = 46) => Math.max(half, Math.min(W - half, x));

// Preview only (`?crowdDemo=1`): clearly-marked sample people so the tags can be looked at while nobody real is around. Never fetched, never shown otherwise.
export const DEMO_PEOPLE = [
  { address: 'demo1', name: 'demo.ape', why: 'holder', lastCard: 'Prime Diamond', demo: true, badges: [{ id: 'q-trader', label: 'Trader', art: '/assets/badges/feeless/trader' }, { id: 'q-supporter', label: 'Supporter', art: '/assets/badges/feeless/supporter' }] },
  { address: 'demo2', name: 'demo.sol', why: 'holder', lastCard: 'Fuse Madness', demo: true, badges: [{ id: 'q-recruit', label: 'Recruit', art: '/assets/badges/feeless/recruit' }] },
  { address: 'demo3', name: 'demo.cat', why: 'backer', lastCard: null, demo: true, badges: [{ id: 'q-trader', label: 'Trader', art: '/assets/badges/feeless/trader' }, { id: 'q-recruit', label: 'Recruit', art: '/assets/badges/feeless/recruit' }, { id: 'q-supporter', label: 'Supporter', art: '/assets/badges/feeless/supporter' }] },
  { address: 'demo4', name: 'demo.degen', why: 'holder', lastCard: 'Prime Everlasting', demo: true, badges: [] },
  { address: 'demo5', name: 'demo.whale', why: 'holder', lastCard: 'Degen #1 · Oct 5', demo: true, badges: [{ id: 'q-trader', label: 'Trader', art: '/assets/badges/feeless/trader' }] },
  { address: 'demo6', name: 'demo.fee', why: 'backer', lastCard: null, demo: true, badges: [{ id: 'q-supporter', label: 'Supporter', art: '/assets/badges/feeless/supporter' }] },
];

/** Spread name tags so neighbours never overlap: keep each as close to its walker as the spacing allows, inside [half, W − half].
 *  xs = wanted centres; returns centres in the SAME order. */
export function spreadTags(xs, W, gap = 112, half = 58) {
  const idx = xs.map((x, i) => i).sort((a, b) => xs[a] - xs[b]), out = xs.slice();
  idx.forEach((i, k) => { out[i] = Math.max(half, k ? out[idx[k - 1]] + gap : half, xs[i]); });
  for (let k = idx.length - 1; k >= 0; k--) { const i = idx[k], hi = k === idx.length - 1 ? W - half : out[idx[k + 1]] - gap; if (out[i] > hi) out[i] = Math.max(half, hi); }
  return out;
}

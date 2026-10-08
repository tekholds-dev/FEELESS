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


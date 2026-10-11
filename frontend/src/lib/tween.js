// 🎞 ease-out cubic from the drawn close to the new REAL close; k ≥ 1 is exactly the tick (never past it, never a made-up price)
export function tweenClose(from, to, k) {
  if (!(k > 0)) return from;
  if (k >= 1 || !Number.isFinite(from)) return to;
  return from + (to - from) * (1 - Math.pow(1 - k, 3));
}


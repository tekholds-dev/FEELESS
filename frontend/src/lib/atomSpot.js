// Where a thing sits on the Collective's print. A real proof keeps its spot for good, decided by its own id.
export const RIDGES = 46; const TAU = Math.PI * 2; const R0 = 38; const STEP = 9.6;
export const ridgeXY = (ridge, a) => { const r = R0 + ridge * STEP; const wave = Math.sin(a * 3 + ridge * 0.17) * 13 + Math.sin(a * 7 - ridge * 0.12) * 5; return [Math.cos(a) * (r * 0.87 + wave) + Math.sin(ridge * 0.3) * 2, Math.sin(a) * (r * 1.2 + wave) + Math.cos(ridge * 0.22) * 3]; };
const hash = s => { let h = 7; for (const c of String(s)) h = (h * 31 + c.charCodeAt(0)) % 1000003; return h; };
export const atomSpot = id => { const h = hash(id); const ridge = 4 + (h % (RIDGES - 8)); const a = (((h >> 4) % 997) / 997) * TAU * 1.04 - 0.12; const [x, y] = ridgeXY(ridge, a); return { x, y, ridge }; };

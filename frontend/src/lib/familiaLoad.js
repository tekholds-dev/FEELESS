// 🌹 LA FAMILIA AS ITS OWN APP PACKAGE (task D, 2026-10-23): the full Familia app (Crews.jsx → the city, the block, the rooms) is one lazy chunk.
// `loadFamilia()` starts (or reuses) that one download — the MOB & Rewards link calls it on hover / focus so the click opens a warm app.
let p = null;
export const loadFamilia = () => (p = p || import('../components/Crews'));

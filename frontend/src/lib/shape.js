// 🧱 A server reply → the shape a panel reads (H01 "missing-data handling", 2026-10-29: 16 of 32 HQ tabs crashed the whole HQ on an empty
// or partial reply — a 500, a fresh install, a field renamed server-side). `shaped(DEFAULTS)(reply)`: every default key is guaranteed, and a
// reply value of the WRONG KIND (an object where a list belongs, null, a string) falls back to the default. One level of nested objects is
// filled the same way. Pure; never throws.
const kind = v => (Array.isArray(v) ? 'array' : v === null ? 'null' : typeof v);
export function shaped(defaults) {
  return reply => {
    const x = reply && typeof reply === 'object' && !Array.isArray(reply) ? reply : {};
    const out = { ...x };
    Object.entries(defaults).forEach(([k, d]) => {
      const v = x[k];
      if (kind(d) === 'object' && kind(v) === 'object') out[k] = { ...d, ...v };
      else if (kind(v) !== kind(d) || (kind(d) === 'number' && !Number.isFinite(v))) out[k] = d;
    });
    return out;
  };
}

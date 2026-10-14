// 🕯 ONE BAD PRINT NEVER DRAWS A CANDLE (owner, 2026-10-14: "copy pump.fun's chart quickness so prices don't flake live"): a live tick that
// jumps ≥ SPIKE % away from the last drawn price is HELD until the next tick says which it was — another tick near it = a real move (drawn),
// a tick back near the old price = a bad print (dropped). A held tick is drawn anyway after HOLD_MS (a coin that really dumped and went
// quiet). Every normal tick is drawn the moment it lands, exactly at its price. Pure.
export const SPIKE = 0.2;
export const CONFIRM = 0.08;
export const HOLD_MS = 2500;
export function tickGuard() {
  let held = null;
  return (prev, value, now = Date.now()) => {
    if (!(value > 0)) return null;
    if (!(prev > 0)) { held = null; return value; }
    if (held) {
      const h = held; held = null;
      if (Math.abs(value / h.v - 1) <= CONFIRM || now - h.at >= HOLD_MS) return value;   // confirmed (or long enough): draw the new level
      if (Math.abs(value / prev - 1) < SPIKE) return value;                              // back near the old price: the held one was a bad print
      held = { v: value, at: now }; return null;
    }
    if (Math.abs(value / prev - 1) >= SPIKE) { held = { v: value, at: now }; return null; }
    return value;
  };
}

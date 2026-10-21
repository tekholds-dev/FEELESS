// 💬 EVERY AGENTS-TAB BUTTON EXPLAINS ITSELF (owner, 2026-10-21: "btns hover explain stuff"): a button with no tip of its own gets one from
// its test id (first matching prefix) when the pointer reaches it. One list, plain words.
export const TIPS = [
  ['ack-deck-chart', 'The live chart of the coin you picked, with the agents’ lines and calls on it'],
  ['ack-deck-seats', 'The four real seats: live P&L, who holds each one, Reaper’s word, quick trade'],
  ['ack-deck-you', 'What the desk learned from YOUR trades — your stops, holds and picks graded'],
  ['ack-deck-live', 'OSSY × G4 on their seat, the ten agents and every live decision'],
  ['ack-deck-tape', 'Every real trade: entry, fills, why it was bought, how it ended'],
  ['ack-deck-review', 'Coins waiting for your call — review, track, arm or ignore'],
  ['ack-deck-limits', 'Your controls: MC band, exits, seats, the model, the buy gate'],
  ['ack-deck-stats', 'Each desk’s own record on real money'],
  ['ack-deck-office', 'The office: the coin board and the thought feed'],
  ['ack-deck-missed', 'Coins the agents passed on that ran — and why they passed'],
  ['ack-deck-paper', 'The agents’ paper desk: calls graded without real money'],
  ['ack-deck-gens', 'Each agent’s generations: wins, losses, how close to replacement'],
  ['ack-iv-', 'Candle size for the chart'], ['ack-warroom', 'Open this coin’s full war room'],
  ['chart-tool-', 'Switch this chart tool on or off'], ['chart-tools-btn', 'Chart tools: gaps, magnets, gun line, germ, meta edge'],
  ['chart-pin-lens-', 'Show or hide this group’s bubbles on the chart'], ['chart-pin-', 'A call on this candle — tap for who said what'],
  ['grab-stop', 'Drag to set YOUR stop for this coin'], ['grab-tp', 'Drag to set YOUR take-profit for this coin'],
  ['share-gif', 'Make a share card of this ride'],
  ['ack-side-decision', 'Why the desk decided what it did on this coin'], ['ack-side-desk', 'OSSY × G4 and the live decision tape'],
  ['ack-ptab-live', 'The decision right now: score vs the buy line, vitals, Devil'],
  ['ack-ptab-ai', 'What the AI models read on this coin, and their record'],
  ['ack-ptab-inputs', 'Every number the desk fed in'], ['ack-ptab-seats', 'The seats from the decision panel'],
  ['ack-ptab-review', 'Mark the desk’s call right or wrong'], ['ack-ptab-trace', 'Each desk’s answer, step by step'],
  ['vital-', 'Tap for the line it is judged on, who reads it and what it does'],
  ['my-seat-go', 'Put the coin you pasted on a seat (your trade — the agents only take notes)'],
  ['ack-lv-duo', 'OSSY and G4 trading their seat, talking it through'], ['ack-lv-matrix', 'The ten agents and what each said'],
  ['ack-lv-tape', 'Every decision as it happens'], ['duo-room-', 'Open that trade’s chat room'], ['duo-coin-', 'Open that coin’s chat room'],
  ['ctp-show-all', 'Show every trade'], ['dial-', 'How picky Trigger is'], ['kpi-', 'Open the lens behind this number'],
  ['seat-', 'This seat — tap for its chart'], ['qt-', 'Quick trade on this seat'],
];
export const tipFor = id => { const s = String(id || ''); const hit = TIPS.find(([p]) => s.startsWith(p)); return hit ? hit[1] : null; };
export function addTip(el) {
  const b = el?.closest?.('button, [role="button"]');
  if (!b || b.hasAttribute('data-tip') || b.title || b.closest('[data-tip]')) return;
  const t = tipFor(b.dataset?.testid);
  if (t) b.setAttribute('data-tip', t);
}

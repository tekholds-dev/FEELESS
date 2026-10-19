// ⬆⬇ ENTRIES + EXITS = ONE GREEN AND ONE RED ARROW (owner, 2026-10-18: "past entry and exit should show better on chart — just a green and a red
// arrow"). Every buy / sell marker on any chart (your fills, the agents' / models' fills, B / X letters, Fee's trades) is drawn the same way:
// a bigger plain arrow at the fill price, no label clutter. Other pins (calls, READY dots, vetoes) keep their own look.
export const UP = '#15d16a';
export const DOWN = '#ff4d6d';
const FILL_TEXT = /^(YOU |BUY|SELL|Fee (buy|sell)|B$|X$)/;

export function isFill(m) {
  return !!m && (m.shape === 'arrowUp' || m.shape === 'arrowDown') && (Number(m.price) > 0 || FILL_TEXT.test(String(m.text || '')));
}

// pure: markers in → the same markers, every entry / exit as a SMALL green / red dot (owner, 2026-10-19: "don't use the arrow that gets in
// the way") — the live entry vital (ChartLive) tells the trade's story; the dot only marks where a fill happened
export function fillArrows(list) {
  return (list || []).map(m => (isFill(m) ? { ...m, shape: 'circle', color: m.shape === 'arrowUp' ? UP : DOWN, text: '', size: 0.6 } : m));
}

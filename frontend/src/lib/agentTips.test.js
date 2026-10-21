import { tipFor, addTip } from './agentTips';
test('a button gets a plain-words tip from its test id, an own tip is kept', () => {
  expect(tipFor('ack-ptab-ai')).toMatch(/AI models/); expect(tipFor('vital-xl')).toMatch(/judged/); expect(tipFor('nope')).toBeNull();
  const d = document.createElement('div'); d.innerHTML = '<button data-testid="ack-iv-1m">1m</button><button data-testid="ack-iv-5m" data-tip="mine">5m</button>';
  addTip(d.firstChild); addTip(d.lastChild);
  expect(d.firstChild.getAttribute('data-tip')).toMatch(/Candle/); expect(d.lastChild.getAttribute('data-tip')).toBe('mine');
});

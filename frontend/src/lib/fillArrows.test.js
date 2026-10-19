import { fillArrows, UP, DOWN } from './fillArrows';

test('entries and exits become a plain green up / red down arrow; other pins stay', () => {
  const out = fillArrows([
    { time: 1, shape: 'arrowUp', color: '#f5c451', text: 'YOU BUY $5 ✓', price: 2 },
    { time: 2, shape: 'arrowDown', color: '#9fe3ff', text: 'X' },
    { time: 3, shape: 'arrowUp', color: '#e9bd65', text: 'caller @ $40K' },
    { time: 4, shape: 'circle', color: '#45e486', text: 'T' },
  ]);
  expect(out[0]).toMatchObject({ color: UP, text: '', size: 2, price: 2 });
  expect(out[1]).toMatchObject({ color: DOWN, text: '' });
  expect(out[2].text).toBe('caller @ $40K');
  expect(out[3].text).toBe('T');
});

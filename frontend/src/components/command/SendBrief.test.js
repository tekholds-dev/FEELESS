import { sendBrief } from './FeaturesFolder';

test('🔀 a PoC answer becomes another proof\'s start command with its story; it is only written into the chat box, never run', () => {
  const t = 'THE PLAN (2 steps)\nSTILL NO is the ticker and   the whole bit.';
  expect(sendBrief('pow', 'NewTrench coin', t)).toBe('file a PoW from my PoC "NewTrench coin": STILL NO is the ticker and the whole bit.');
  expect(sendBrief('pob', 'x', 'a')).toMatch(/^file a pob from my PoC "x": a$/);
  expect(sendBrief('pop', 'x', 'b'.repeat(900)).length).toBeLessThan(700);
});

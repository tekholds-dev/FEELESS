import { mindModel } from './CatWorkbench';

const cat = { brainsCfg: { brains: ['tencent/hy4', 'openai/gpt-6.1-terra'], byKind: { pob: ['openai/gpt-6.1-sol', 'z-ai/glm-5.3'] } } };
test('the PoB on the desk names its own minds (owner 2026-11-15: cards said hy4 / terra on a Sol + GLM PoB)', () => {
  const d = { deskProof: { kind: 'pob' } };
  expect(mindModel(cat, d, [{ model: 'tencent/hy4', status: 'idle' }], 0)).toBe('openai/gpt-6.1-sol');
  expect(mindModel(cat, d, [], 1)).toBe('z-ai/glm-5.3');
  expect(mindModel(cat, {}, [], 0)).toBe('tencent/hy4');
  expect(mindModel(cat, d, [{ model: 'x/busy', status: 'working' }], 0)).toBe('x/busy');
  expect(mindModel(cat, { deskProof: { kind: 'poc' } }, [], 1)).toBe('openai/gpt-6.1-terra');
});

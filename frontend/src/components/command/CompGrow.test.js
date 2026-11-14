import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { Teacher, growRead } from './CompGrow';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('motion/react', () => { const R = require('react'); return { motion: { button: R.forwardRef(({ initial, animate, transition, ...p }, ref) => R.createElement('button', { ...p, ref })) } }; });
const job = (v, params, val, built) => ({ id: `2026-${v}`, status: 'done', version: v, card: { spec: { paramsTotal: params }, val, built, perplexity: 9, baselinePerplexity: 30 } });

test('the next move follows the numbers: feed it, rebuild, build, teach, exam', () => {
  expect(growRead({ jobs: [] }, {}).next.k).toBe('build');
  const thin = growRead({ corpus: { chars: 1e6 }, jobs: [job('v1.00', 5e6, 2.5, 10)] }, { untaught: 40 });
  expect(thin.next.k).toBe('teach'); expect(thin.ratio).toBeCloseTo(0.2); expect(thin.next.why).toContain('0.20 per parameter');
  expect(growRead({ corpus: { chars: 9e6 }, jobs: [job('v1.00', 1e5, 2.4, 1), job('v1.01', 1e5, 2.9, 2)] }, {}).next.t).toMatch(/got worse/);
  expect(growRead({ corpus: { chars: 9e6 }, jobs: [job('v1.00', 1e5, 2.4, 1)] }, { recent: [{ at: 5 }] }).next.t).toBe('Build the next version');
  expect(growRead({ corpus: { chars: 9e6 }, jobs: [job('v1.00', 1e5, 2.4, 9)] }, { untaught: 3, recent: [{ at: 5 }] }).next.k).toBe('teach');
  expect(growRead({ corpus: { chars: 9e6 }, jobs: [job('v1.00', 1e5, 2.4, 9)] }, { untaught: 0 }).next.k).toBe('v2');
  const read = growRead({ corpus: { chars: 59e3 }, jobs: [{ ...job('v0.01', 5e6, 4.2, 9), files: [{ name: 'corpus.txt', bytes: 1.7e6 }] }] }, {});
  expect(read.chars).toBe(1.7e6); expect(read.ratio).toBeCloseTo(0.34);   // what the version really read, not today's trimmed sources
});

test('the teacher shows the live price, sends the exact quote with Pay, and never more lessons than proofs left', async () => {
  const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host); const onPay = jest.fn();
  const t = { teachers: [{ id: 'anthropic/claude-opus-5.5', family: 'Claude Opus', perLesson: 0.01, inPerM: 4, outPerM: 20 }, { id: 'qwen/qwen3.7-plus', family: 'Qwen 3.7 Plus', perLesson: 0.0007, inPerM: 0.32, outPerM: 1.28 }],
    untaught: 12, lessons: 3, spentUsd: 0.02, keyOk: true, maxUsd: 5, recent: [] };
  await act(async () => root.render(<Teacher t={t} onPay={onPay} onStop={() => {}} />));
  expect(host.querySelector('[data-testid=cg-pay]').textContent).toBe('Pay ≈ $0.12 · teach 12 lessons');   // 25 asked, 12 proofs left
  await act(async () => { host.querySelector('[data-testid="cg-t-qwen/qwen3.7-plus"]').click(); });
  await act(async () => { host.querySelector('[data-testid=cg-n-10]').click(); });
  await act(async () => { host.querySelector('[data-testid=cg-pay]').click(); });
  expect(onPay).toHaveBeenCalledWith({ model: 'qwen/qwen3.7-plus', n: 10, quoteUsd: expect.any(Number) });
  expect(onPay.mock.calls[0][0].quoteUsd).toBeCloseTo(0.007, 5);
  await act(async () => root.render(<Teacher t={{ ...t, keyOk: false }} onPay={onPay} onStop={() => {}} />));
  expect(host.querySelector('[data-testid=cg-pay]').disabled).toBe(true);
  act(() => root.unmount()); host.remove();
});

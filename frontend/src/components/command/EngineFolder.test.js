import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { EngineFolder } from './EngineFolder';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const click = el => act(() => { el.dispatchEvent(new MouseEvent('click', { bubbles: true })); });

test('owner 2026-11-14: a proposal opens to its full check, its counts, the failed proofs with what the reviewers said, and what a yes changes', async () => {
  const calls = [];
  const engines = { reviewer: {}, kits: {}, reads: {}, methods: {}, routes: [], proposals: { canApprove: true, approved: [], history: [], combos: [], proofs: [{ word: 'site', name: 'Site summaries', asks: 3, examples: ['summarise crawlnet.network'] }],
    kits: [{ id: 'fix-pob-2', kind: 'pob', what: 'Each pick has its own reason', full: '2. Each pick has its own reason backed by those sources', failRate: 0.82, seen: 11, failed: 9,
      examples: [{ agent: 'Happy', n: 13, title: 'Jets vs Chiefs', said: [{ who: 'OSSY', note: 'the why says market odds but no page was read' }] }] }] } };
  const work = jest.fn(async (id, body) => { calls.push(body); return body.op === 'engines' ? engines : { approved: [{ id: 'fix-pob-2' }] }; });
  const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host);
  await act(async () => { root.render(<EngineFolder cat={{ id: 'leader' }} work={work} />); });
  expect(host.querySelector('[data-testid="eng-prop-fix-pob-2-body"]')).toBeNull();
  click(host.querySelector('[data-testid="eng-prop-fix-pob-2-open"]'));
  const body = host.querySelector('[data-testid="eng-prop-fix-pob-2-body"]').textContent;
  expect(body).toContain('backed by those sources'); expect(body).toContain('9 of 11'); expect(body).toContain('Jets vs Chiefs');
  expect(body).toContain('OSSY'); expect(body).toContain('no page was read'); expect(body).toContain('If you approve');
  click(host.querySelector('[data-testid="eng-gap-site-open"]'));
  expect(host.querySelector('[data-testid="eng-gap-site-body"]').textContent).toContain('summarise crawlnet.network');
  await act(async () => { host.querySelector('[data-testid="eng-approve-fix-pob-2"]').dispatchEvent(new MouseEvent('click', { bubbles: true })); });
  expect(calls.find(c => c.op === 'kit_method_approve')).toEqual({ op: 'kit_method_approve', text: 'fix-pob-2' });
  act(() => root.unmount()); host.remove();
});

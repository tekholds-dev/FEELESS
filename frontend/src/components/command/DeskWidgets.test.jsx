jest.mock('../perps/PerpsChart', () => ({ PerpsChart: () => null }));
jest.mock('./AtomPrint', () => ({ __esModule: true, default: () => null }));
const signed = [];
jest.mock('../../hooks/useWallet', () => ({ useWallet: () => ({ signMessage: async m => { signed.push(m); return 'SIG'; } }) }));
import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
test('🧾 the desk vitals: every widget opens a real window, and the minds show by their own names', async () => {
  const { AgentDesktop } = require('./CatWorkbench');
  global.fetch = async () => ({ ok: true, json: async () => ({}) }); window.matchMedia = window.matchMedia || (() => ({ matches: true, addEventListener() {}, removeEventListener() {} }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<AgentDesktop cat={{ id: 'g1', name: 'Happy', brainsCfg: { kind: 'general', brains: ['local/ossy', 'local/g4'], mindNames: ['OSSY', 'G4'], credit: 5.8, spent: 1.2 } }} live={null} onClose={() => {}} onReopen={() => {}} />); });
  const out = [];
  for (const k of ['dwg-dash', 'dwg-minds', 'dwg-crm', 'dwg-money']) {
    const b = document.querySelector(`[data-testid="${k}"]`); if (!b) { out.push(`${k}: missing`); continue; }
    const before = new Set([...document.querySelectorAll('[data-testid^="dsk-win-"]')].map(w => w.dataset.testid));
    await act(async () => { b.click(); });
    const now = [...document.querySelectorAll('[data-testid^="dsk-win-"]')].map(w => w.dataset.testid).filter(x => !before.has(x));
    out.push(`${k} -> ${now.join(',') || 'NOTHING'}`);
  }
  expect(out).toEqual(['dwg-dash -> dsk-win-proofs', 'dwg-minds -> dsk-win-manual', 'dwg-crm -> dsk-win-mail', 'dwg-money -> dsk-win-boost']);
  expect(document.querySelector('[data-testid="dwg-minds"]').textContent).toMatch(/OSSY.*G4/);
  const { kindRows } = require('./DeskWidgets');
  expect(kindRows({ psFolders: [{ graded: 'right' }, { graded: 'wrong' }, { hidden: true }], poeFolders: [{ net: 5 }] })).toEqual([{ k: 'PoStatic', n: 2, w: 1, l: 1 }, { k: 'PoEco', n: 1, w: 1, l: 0 }]);
  act(() => root.unmount()); el.remove();
});

import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { PrintChip, FolderRidge, PrintDigests } from './ProofKit';

test('🧬 a proof shows its own print id and how new it is, and its ridge is drawn from what it did', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<PrintChip p={{ id: 'PoB-63B9-8CBB', uniquePct: 81, nearest: 18, shared: ['espn.com'], traits: ['1 game', '1 Kalshi bet'] }} />); });
  const chip = el.querySelector('[data-testid=print-chip]'); expect(chip.textContent).toContain('PoB-63B9-8CBB'); expect(chip.textContent).toContain('81% new');
  expect(chip.getAttribute('data-tip')).toContain('nearest is #18');
  const ridge = async digest => { await act(async () => { root.render(<PrintDigests.Provider value={{ pob1: { digest } }}><FolderRidge fid="pob1" /></PrintDigests.Provider>); }); return el.innerHTML; };
  const a = await ridge('aaaa1111bbbb2222'); const a2 = await ridge('aaaa1111bbbb2222'); const b = await ridge('ffff9999eeee8888');
  expect(a).toBe(a2); expect(a).not.toBe(b);   // same work → same ridge; different work → different ridge
  await act(async () => { root.render(<PrintChip p={null} />); }); expect(el.innerHTML).toBe('');
  act(() => root.unmount());
});

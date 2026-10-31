let mockParams = new URLSearchParams('mode=pools&tab=pools');
jest.mock('react-router-dom', () => { const R = require('react'); return { useSearchParams: () => { const [p, setP] = R.useState(mockParams); return [p, n => { mockParams = n; setP(new URLSearchParams(n)); }]; } }; }, { virtual: true });

test('🧺 Launch › Pools: AutoRange, every pool safe→risky, Night Vault and price gaps — one tab at a time, the tab rides the URL', async () => {
  const React = require('react'); const { act } = React; const { createRoot } = require('react-dom/client'); 
  const { LaunchModes } = require('./LaunchModes');
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  global.fetch = async () => ({ ok: true, json: async () => ({ pools: [{ id: 'a', sym: 'USDC lend', kind: 'lend', proto: 'kamino', tvl: 9e7, apy: 9, tier: 'safe' }, { id: 'b', sym: 'MEME-SOL', kind: 'v2', proto: 'ray', tvl: 3e5, apy: 400, tier: 'risky' }], kinds: { lend: 1, v2: 1 }, gaps: [], strategies: [], rows: [] }) });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<LaunchModes><p>coin</p></LaunchModes>); });
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(el.querySelector('[data-testid="lm-tab-pools"]').getAttribute('aria-selected')).toBe('true');
  expect(el.querySelector('[data-testid="pool-hub"]').className).toContain('is-compact');
  await act(async () => { el.querySelector('[data-testid="phb-tier-risky"]').click(); });
  expect(el.querySelector('[data-testid="pool-hub"]').textContent).toContain('MEME-SOL'); expect(el.querySelector('[data-testid="pool-hub"]').textContent).not.toContain('USDC lend');
  await act(async () => { el.querySelector('[data-testid="lm-tab-gaps"]').click(); });
  expect(el.querySelector('[data-testid="pool-hub"]')).toBeNull(); expect(mockParams.get('tab')).toBe('gaps');
  await act(async () => root.unmount()); el.remove();
});

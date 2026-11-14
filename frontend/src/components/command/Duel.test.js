import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import Duel, { disagree } from './Duel';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('the strip finds where two answers part: the call, the coins, the numbers', () => {
  const g = disagree('Buy $BONK: liquidity up 2x, 40% held by top 10', 'Skip $BONK — dev sold 40%, liquidity thin');
  expect(g.points.map(p => p.what)).toEqual(['The call', 'Numbers']);
  expect(g.points[0]).toEqual({ what: 'The call', a: 'buy', b: 'skip' });
  expect(g.agree).toBeGreaterThan(0); expect(g.agree).toBeLessThan(1);
  expect(disagree('same words here', 'same words here')).toEqual({ agree: 1, points: [] });
  expect(disagree('Buy $WIF', 'Buy $POPCAT').points[0]).toEqual({ what: 'Coins', a: '$WIF', b: '$POPCAT' });
});

test('tap the winner once: it is filed, marked right / wrong, and cannot be picked again', async () => {
  const job = { id: 't1', minds: [{ model: 'or/a', answer: 'Buy it' }, { model: 'b', answer: 'Skip it' }] };
  const picks = []; let pick;
  const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host);
  const draw = () => root.render(<Duel job={job} pick={pick} onPick={async i => { picks.push(i); pick = i; draw(); }} />);
  act(() => draw());
  expect(host.querySelector('[data-testid=duel-point-0]').textContent).toContain('buy');
  await act(async () => { host.querySelector('[data-testid=duel-pick-1]').click(); });
  expect(picks).toEqual([1]);
  expect(host.querySelector('[data-testid=duel-mind-1]').className).toContain('is-won');
  expect(host.querySelector('[data-testid=duel-mind-0]').textContent).toContain('WRONG');
  expect(host.querySelector('[data-testid=duel-pick-0]')).toBeNull(); expect(host.querySelector('[data-testid=duel-filed]')).not.toBeNull();
  act(() => root.unmount()); host.remove();
});

import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { GameLab } from './GameLab';
import FIX from '../../dev/gameLabFixture.json';   // game_lab.py's own output

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mount = async node => { const el = document.body.appendChild(document.createElement('div')); await act(async () => { createRoot(el).render(node); }); return el; };

// The Game desk's Test + port tab: the playtest log and one port checklist per target, opening on the project's own target.
test('the playtest log, the port steps per target, and a tick goes to the desk', async () => {
  const sent = [];
  const lab = async body => { if (body) sent.push(body); return FIX.view; };
  const el = await mount(<GameLab lab={lab} target="gtasa_vita" />);
  expect(el.querySelector('[data-testid="glb-log-list"]').textContent).toContain('Night Run');
  await act(async () => { el.querySelector('[data-testid="glb-tab-port"]').click(); });
  expect(el.querySelector('[data-testid="glb-plat-gtasa_vita"]').getAttribute('aria-pressed')).toBe('true');
  expect(el.textContent).toContain('Never share game files');
  await act(async () => { el.querySelector('[data-testid="glb-step-1"]').click(); });
  expect(sent.at(-1)).toEqual({ check: 'gtasa_vita', step: 1 });
  await act(async () => { el.querySelector('[data-testid="glb-plat-vita"]').click(); });
  expect(el.textContent).toContain('Vita3K');
  expect(el.querySelector('[data-testid="glb-tab-rp"]')).toBeNull();
});

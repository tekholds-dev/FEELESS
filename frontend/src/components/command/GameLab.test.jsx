import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { GameLab } from './GameLab';
import FIX from '../../dev/gameLabFixture.json';   // game_lab.py's own output

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mount = async node => { const el = document.body.appendChild(document.createElement('div')); await act(async () => { createRoot(el).render(node); }); return el; };

// Owner 2026-11-15: a Game lab folder on the desktop for testing, porting (GTA RP, PS Vita…) and building.
test('the game lab shows the log, the porting steps and makes a FiveM resource', async () => {
  const sent = [];
  const call = async (path, o) => { if (o?.body) sent.push(JSON.parse(o.body)); return o?.body && JSON.parse(o.body).resource ? FIX.resource : FIX.view; };
  const el = await mount(<GameLab call={call} />);
  expect(el.querySelector('[data-testid="glb-log-list"]').textContent).toContain('Night Run');
  await act(async () => { el.querySelector('[data-testid="glb-tab-port"]').click(); });
  expect(el.querySelector('[data-testid="glb-step-0"]').checked).toBe(true);
  await act(async () => { el.querySelector('[data-testid="glb-plat-vita"]').click(); });
  expect(el.textContent).toContain('Vita3K');
  await act(async () => { el.querySelector('[data-testid="glb-tab-rp"]').click(); });
  const name = el.querySelector('[data-testid="glb-rp-name"]');
  await act(async () => { const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; set.call(name, 'my_garage'); name.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { el.querySelector('[data-testid="glb-rp-make"]').click(); });
  expect(sent.at(-1).resource.name).toBe('my_garage');
  expect(el.querySelector('[data-testid="glb-rp-out"]').textContent).toContain("fx_version 'cerulean'");
});

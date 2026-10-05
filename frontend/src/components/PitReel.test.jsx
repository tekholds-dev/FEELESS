import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { PitReel, REEL_SCENES, REEL_MS, reelLine } from './PitReel';
import { FuseGuide } from './FuseGuide';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); return el; };
const p = { a: { name: 'Fuse Madness', emoji: '🧬', now: 3.6 }, b: { name: 'Prime Everlasting', emoji: '♾', now: 0.3 } };

test('the Pit reel cycles battle scenes and the leader wins each one', async () => {
  jest.useFakeTimers();
  const el = await mount(<PitReel p={p} />);
  const reel = () => el.querySelector('[data-testid="pit-reel"]');
  expect(reel().dataset.scene).toBe(REEL_SCENES[0][0]);
  expect(reel().className).toContain('lead-a');
  expect(el.textContent).toContain('Fuse Madness wins the clash · +3.3');
  await act(async () => { jest.advanceTimersByTime(REEL_MS); });
  expect(reel().dataset.scene).toBe(REEL_SCENES[1][0]);
  await act(async () => { jest.advanceTimersByTime(REEL_MS * (REEL_SCENES.length - 1)); });
  expect(reel().dataset.scene).toBe(REEL_SCENES[0][0]);   // loops forever
  jest.useRealTimers();
});

test('an off-screen fight holds still, a tie reads even, the beam leans to the trailing side', async () => {
  jest.useFakeTimers();
  const el = await mount(<PitReel p={p} still />);
  await act(async () => { jest.advanceTimersByTime(REEL_MS * 3); });
  expect(el.querySelector('[data-testid="pit-reel"]').dataset.scene).toBe('clash');
  expect(el.querySelector('[data-testid="pit-reel"]').style.getPropertyValue('--lean')).toBe(`${(3.3 * 4).toFixed(1)}%`);
  expect(reelLine('beam', { a: { now: 1 }, b: { now: 1.1 } })).toMatch(/dead even/);
  jest.useRealTimers();
});

test('the guide explains dials / cycles / coins and picks a dial or cycle from inside it', async () => {
  const onDial = jest.fn(); const onCycle = jest.fn();
  const el = await mount(<FuseGuide dial="safe" onDial={onDial} cycle="classic" onCycle={onCycle} />);
  await act(async () => { el.querySelector('[data-testid="fg-open"]').click(); });
  const g = document.querySelector('[data-testid="fuse-guide"]');
  expect(g.textContent).toContain('+30% / −15%');          // safe dial's exact exits
  await act(async () => { g.querySelector('[data-testid="fg-dial-degen"]').click(); });
  expect(onDial).toHaveBeenCalledWith('degen');
  await act(async () => { g.querySelector('[data-testid="fg-tab-cycles"]').click(); });
  await act(async () => { g.querySelector('[data-testid="fg-cycle-rescue"]').click(); });
  expect(onCycle).toHaveBeenCalledWith('rescue');
  await act(async () => { g.querySelector('[data-testid="fg-tab-coins"]').click(); });
  expect(g.textContent).toContain('Dip buy'); expect(g.textContent).toContain('Dex paid'); expect(g.textContent).toMatch(/Stables and staked SOL never anchor/);
  await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' })); });
  expect(document.querySelector('[data-testid="fuse-guide"]')).toBeNull();
});

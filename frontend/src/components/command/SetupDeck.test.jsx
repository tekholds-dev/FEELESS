import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { SetupDeck, TermsFolder, TERMS, securityFacts } from './SetupDeck';
import { SetupDot, Lamp } from './DeskShell';

const steps = (done = {}) => ['use', 'face', 'email', 'sites', 'fund', 'limits', 'colony', 'trades', 'security', 'terms'].map(k => ({ k, done: k === 'face' || !!done[k] }));
const SETUP = { use: null, left: 9, total: 10, termsV: 2, sites: [['pump.fun', 'Coin trades']], steps: steps() };

function Host({ work, d0, kit }) {
  const [d, setD] = useState(d0);
  return <SetupDeck cat={{ id: 'c', agentWallet: { address: 'A'.repeat(44) } }} d={d} setD={setD} work={work} onOpen={() => {}} kit={kit} />;
}
async function mount(node) {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(node); });
  return { el, root, q: id => el.querySelector(`[data-testid="${id}"]`), done: async () => { await act(async () => { root.unmount(); }); el.remove(); } };
}
const click = async b => { await act(async () => { b.click(); }); await act(async () => { await Promise.resolve(); }); };

test('🚀 setup opens on its first ask, an answer goes to the server and moves on', async () => {
  const calls = []; const work = jest.fn(async (_, b) => { calls.push(b); return { setup: { ...SETUP, use: b.text, left: 8, steps: steps({ use: true }) } }; });
  const { q, done } = await mount(<Host work={work} d0={{ setup: SETUP }} />);
  expect(q('am-setup').textContent).toContain('What will this agent be used for?');
  await click(q('stp-use-trade'));
  expect(calls[0]).toEqual({ op: 'setup', job: 'use', text: 'trade' });
  expect(q('am-setup').textContent).toContain('Pick its character');
  expect(q('am-setup').textContent).toContain('8 of 10 left');
  await done();
});

test('🚀 it starts on the first step not done, and an ask can be left for later', async () => {
  const calls = []; const work = jest.fn(async (_, b) => { calls.push(b); return { setup: { ...SETUP, left: 5, steps: steps({ use: true, email: true, sites: true, fund: true }) } }; });
  const { q, done } = await mount(<Host work={work} d0={{ setup: { ...SETUP, left: 6, steps: steps({ use: true, email: true, sites: true }) } }} />);
  expect(q('am-setup').textContent).toContain('Fund it');
  await click(q('stp-later'));
  expect(calls[0]).toEqual({ op: 'setup', job: 'done', text: 'fund' });
  expect(q('am-setup').textContent).toContain('The most one task may spend');
  await done();
});

test('🍯 the colony share signs up to 25%, and no share signs nothing', async () => {
  const signShare = jest.fn(async () => ({})); const useShare = () => [{ on: false, pct: 10 }, null, signShare, true]; const calls = [];
  const work = jest.fn(async (_, b) => { calls.push(b); return { setup: SETUP }; });
  const { q, done } = await mount(<Host work={work} kit={{ useShare, caps: [] }} d0={{ setup: { ...SETUP, steps: steps({ use: true, email: true, sites: true, fund: true, limits: true }) } }} />);
  expect(q('stp-share-30')).toBeNull(); expect(q('stp-share-25')).toBeTruthy();
  await click(q('stp-share-25')); await click(q('stp-share-go'));
  expect(signShare).toHaveBeenCalledWith(true, 25); expect(calls.at(-1)).toEqual({ op: 'setup', job: 'done', text: 'colony' });
  await done();
});

test('📃 terms are readable, can be agreed once, and every security line is on screen', async () => {
  const calls = []; const work = jest.fn(async (_, b) => { calls.push(b); return { setup: { ...SETUP, termsAt: 1800000000 } }; });
  function T() { const [d, setD] = useState({ setup: SETUP, logins: [{}], signedIn: [{}, {}] }); return <TermsFolder cat={{ id: 'c' }} d={d} setD={setD} work={work} />; }
  const { q, el, done } = await mount(<T />);
  expect(el.querySelectorAll('.stp-terms details').length).toBe(TERMS.length);
  securityFacts({}, {}).forEach(([, t]) => expect(el.textContent).toContain(t));
  expect(el.textContent).toContain('3 logins and sign-ins');
  await click(q('terms-agree'));
  expect(calls[0]).toEqual({ op: 'setup', job: 'terms', text: '' }); expect(q('terms-agreed')).toBeTruthy(); expect(q('terms-agree')).toBeNull();
  await done();
});

test('🔴 the Desktop dot stays lit with what is left, and goes out at zero', async () => {
  const { q, done } = await mount(<SetupDot id="c" />);
  expect(q('setup-dot')).toBeNull();
  await act(async () => { window.dispatchEvent(new CustomEvent('feeless:setup-left', { detail: { id: 'other', left: 4 } })); }); expect(q('setup-dot')).toBeNull();
  await act(async () => { window.dispatchEvent(new CustomEvent('feeless:setup-left', { detail: { id: 'c', left: 4 } })); }); expect(q('setup-dot').textContent).toBe('4');
  await act(async () => { window.dispatchEvent(new CustomEvent('feeless:setup-left', { detail: { id: 'c', left: 0 } })); }); expect(q('setup-dot')).toBeNull();
  await done();
});

test('💡 the lamp is on while it works, zaps at 5, 23 and 45 s, and goes out after it finishes', async () => {
  jest.useFakeTimers();
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<Lamp active={false} />); });
  await act(async () => { jest.advanceTimersByTime(700); });
  const lamp = () => el.querySelector('[data-testid="kd-lamp"]');
  expect(lamp().dataset.on).toBe('0');
  await act(async () => { root.render(<Lamp active />); });
  expect(lamp().dataset.on).toBe('1');
  const zap = () => el.querySelector('.lamp-zap'); const first = zap();
  await act(async () => { jest.advanceTimersByTime(4900); }); expect(zap()).toBe(first);
  await act(async () => { jest.advanceTimersByTime(200); }); expect(zap()).not.toBe(first);
  const second = zap();
  await act(async () => { jest.advanceTimersByTime(4800); }); expect(zap()).toBe(second);
  await act(async () => { root.render(<Lamp active={false} />); });
  expect(lamp().dataset.on).toBe('1');
  await act(async () => { jest.advanceTimersByTime(700); }); expect(lamp().dataset.on).toBe('0');
  await act(async () => { root.unmount(); }); el.remove(); jest.useRealTimers();
});

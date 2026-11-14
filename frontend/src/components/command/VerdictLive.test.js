import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import VerdictLive, { meterRead } from './VerdictLive';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('motion/react', () => { const R = require('react'); const tag = t => R.forwardRef(({ initial, animate, transition, ...p }, ref) => R.createElement(t, { ...p, ref })); return { motion: { span: tag('span'), div: tag('div') } }; });

const live = { fid: 'b1', kind: 'pob', n: 3, title: 'JUP bid', at: 1, done: null,
  judges: { collective: { state: 'done', score: 80, verdict: 'pass', why: 'the bid matches the book' }, 'collective-2': { state: 'think', since: 2 }, 'collective-3': { state: 'out' } } };

test('the meter reads each verdict as it lands, then stamps The Collective\'s', () => {
  const r = meterRead(live);
  expect(r.name).toBe('PoB #3'); expect(r.judges.map(x => x.label)).toEqual(['Judge 1', 'Judge 2']);   // a judge who sat out is not on the meter
  expect(r.say).toBe('1 of 2 in · leaning PASS at 80');
  const two = { ...live, judges: { ...live.judges, 'collective-2': { state: 'done', score: 20, verdict: 'fail', why: 'no source' } } };
  expect(meterRead(two).say).toBe('2 of 2 in · leaning FAIL at 50');
  expect(meterRead({ ...two, done: 9, score: 50, verdict: 'fail', agree: false }).say).toBe('The Collective: FAIL at 50 · the judges split');
  expect(meterRead({ ...live, done: 9, score: null, verdict: null, judges: { ossy: { state: 'down' } } }).say).toMatch(/no verdict \(never a pass\)/);
  expect(meterRead({ ...live, judges: { ossy: { state: 'think' }, g4: { state: 'wait' } } }).judges.map(x => x.label)).toEqual(['OSSY', 'G4']);   // staff see the names
  expect(meterRead(null)).toBeNull();
});

test('the card shows a pin per answered judge with its reason, opens the proof, folds to a pill', () => {
  const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host); const onOpen = jest.fn();
  act(() => root.render(<VerdictLive j={live} onOpen={onOpen} />));
  expect(host.querySelector('[data-testid=vlv-say]').textContent).toContain('1 of 2 in');
  expect(host.querySelector('[data-testid=vlv-pin-collective]')).not.toBeNull(); expect(host.querySelector('[data-testid=vlv-pin-collective-2]')).toBeNull();
  expect(host.querySelector('[data-testid=vlv-j-collective]').textContent).toContain('the bid matches the book');
  expect(host.querySelector('[data-testid=vlv-j-collective-2]').textContent).toContain('Reading the proof');
  act(() => { host.querySelector('.vlv-name').click(); }); expect(onOpen).toHaveBeenCalledWith({ win: 'bids', id: 'b1' });
  act(() => { host.querySelector('.vlv-x').click(); }); expect(host.querySelector('[data-testid=vlv-pill]').textContent).toContain('1/2');
  act(() => root.render(<VerdictLive j={null} />)); expect(host.querySelector('[data-testid=vlv]')).toBeNull();
  act(() => root.unmount()); host.remove();
});

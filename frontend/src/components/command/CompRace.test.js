import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CompRace, raceRead } from './CompRace';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const race = [{ at: 100, n: 10, scores: { baseline: 0.5, comp: 0.6, g4: 0.65 }, names: { baseline: 'Majority', comp: 'COMP v2', g4: 'G4' }, kinds: { baseline: 'baseline', comp: 'local', g4: 'own' } }];

test('the race says where COMP stands, and a newer exam on screen joins it live', () => {
  const r = raceRead(race, null);
  expect(r.say).toBe('COMP is #2 of 2 (60%): G4 leads at 65%, 5 points ahead.'); expect(r.ids[0]).toBe('comp');
  const live = { at: 190, n: 10, examinees: [{ id: 'comp', name: 'COMP v2', kind: 'local', score: { n: 10, acc: 0.7 } }, { id: 'g4', name: 'G4', kind: 'own', score: { n: 10, acc: 0.66 } }, { id: 'claude', kind: 'flagship', blocked: 'no key' }] };
  const r2 = raceRead(race, live);
  expect(r2.exams).toBe(2); expect(r2.data[1]).toEqual({ x: 2, at: 190, live: true, comp: 70, g4: 66 });
  expect(r2.say).toBe('COMP is #1 of 2 on exam 2 (70%), ahead of G4 at 66%.'); expect(r2.rank).toBe(1);
  expect(raceRead([], null).data).toEqual([]);
});

test('it draws the crown and one key row per model', () => {
  const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host);
  act(() => root.render(<CompRace race={race} exam={null} />));
  expect(host.querySelector('[data-testid=comp-race-say]').textContent).toContain('#2');
  expect(host.querySelectorAll('.crc-key li')).toHaveLength(3);
  act(() => root.unmount()); host.remove();
});

import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { OwnerStudy } from './OwnerStudy';

test('your study: score ring, a meter per move kind, seats + lines vs the agents, suggestions waiting for you', () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  act(() => { createRoot(el).render(<OwnerStudy study={{ score: 55, graded: 20, kinds: [{ kind: 'pick', label: '🎯 pick', n: 10, goodPct: 70, medPct: 12 }],
    seats: { cmp: { n: 7, you: 14, agents: 4 } }, hand: { yours: { n: 6, med: 3 }, agents: { n: 40, med: -2 } },
    findings: ['🎯 pick: 10 graded'], suggestions: [{ agent: 'reaper', value: 'let winners run' }] }} memory={{ owner: 3, lessons: 20 }} />); });
  expect(el.textContent).toContain('55%'); expect(el.textContent).toContain('70%'); expect(el.textContent).toContain('+14.0%');
  expect(el.textContent).toContain('let winners run'); expect(el.textContent).toContain('lessons 20');
  act(() => { createRoot(document.createElement('div')).render(<OwnerStudy study={null} />); });
});

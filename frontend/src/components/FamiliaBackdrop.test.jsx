import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { FamiliaBackdrop, SCENES } from './FamiliaBackdrop';
import { Podium } from './Crews';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mount = node => { const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); act(() => { root.render(node); }); return { el, root }; };
afterEach(() => { document.body.innerHTML = ''; });

test('🎬 every Familia tab has its own drawn scene behind the page (never a click target); an unknown tab falls back to the harbor', () => {
  const marks = { home: '.fbd-search', family: '.fbd-chand', wars: '.fbd-siren', board: '.fbd-spot', feed: '.fbd-radar' };
  for (const k of Object.keys(SCENES)) {
    const { el, root } = mount(<FamiliaBackdrop scene={k} />);
    const b = el.querySelector('[data-testid="familia-backdrop"]');
    expect(b.className).toContain(`s-${k}`); expect(b.getAttribute('aria-hidden')).toBe('true'); expect(b.querySelector(marks[k])).not.toBeNull();
    act(() => { root.unmount(); });
  }
  expect(mount(<FamiliaBackdrop scene="nope" />).el.querySelector('.fbd').className).toContain('s-home');
});

test('🏆 the podium: #1 in the middle and crowned, #2 left, #3 right; empty plinths wait OPEN for a family that ranks', () => {
  const rows = [{ id: 'a', tag: 'AAA', name: 'Alpha', pct: 12.5, ranked: true, trades: 9, wonPct: 60 }, { id: 'b', tag: 'BBB', name: 'Bravo', pct: -2, ranked: true, trades: 6, wonPct: 40 }];
  const { el } = mount(<Podium rows={rows} />);
  const steps = [...el.querySelectorAll('.fpd-step')];
  expect(steps.map(s => s.className.match(/p\d/)[0])).toEqual(['p2', 'p1', 'p3']);
  expect(steps[1].textContent).toContain('Alpha'); expect(steps[1].querySelector('.fpd-crown')).not.toBeNull(); expect(steps[1].textContent).toContain('+12.5%');
  expect(steps[0].textContent).toContain('Bravo'); expect(steps[2].className).toContain('is-open'); expect(steps[2].textContent).toContain('OPEN');
});

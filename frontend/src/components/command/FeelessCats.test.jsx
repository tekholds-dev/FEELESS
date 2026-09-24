import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FeelessCats } from './FeeBack';

jest.mock('react-router-dom', () => {
  const mockReact = require('react');
  return {
    Link: ({ children, ...props }) => mockReact.createElement('a', props, children),
  };
}, { virtual: true });

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function mount() {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => root.render(<FeelessCats />));
  return { container, root };
}

afterEach(() => {
  document.body.innerHTML = '';
});


test('keeps every fur filter reachable and updates the visible collection', () => {
  const { container, root } = mount();
  const expectedCounts = { all: 50, spots: 34, patch: 8, stripes: 8 };

  Object.entries(expectedCounts).forEach(([filter, count]) => {
    act(() => container.querySelector(`[data-testid="feecats-filter-${filter}"]`).click());
    expect(container.querySelector(`[data-testid="feecats-filter-${filter}"]`).getAttribute('aria-pressed')).toBe('true');
    expect(container.querySelectorAll('.cat-card-grid .cat-card')).toHaveLength(count);
  });

  act(() => root.unmount());
});

test('updates the preview for a selected cat and for Surprise me', () => {
  const { container, root } = mount();
  const randomSpy = jest.spyOn(Math, 'random').mockReturnValue(0);

  act(() => container.querySelector('[data-testid="feecat-card-midnight-patch"]').click());
  expect(container.querySelector('.cat-preview-panel h2').textContent).toBe('Midnight Patch');
  expect(container.querySelector('[role="status"]').textContent).toContain('Midnight Patch selected');

  act(() => container.querySelector('[data-testid="feecats-select"]').click());
  expect(container.querySelector('[role="status"]').textContent).toContain('Midnight Patch is your featured cat');

  act(() => container.querySelector('[data-testid="feecats-random"]').click());
  expect(container.querySelector('.cat-preview-panel h2').textContent).toBe('Solaris');
  expect(container.querySelector('[role="status"]').textContent).toContain('Solaris selected');

  randomSpy.mockRestore();
  act(() => root.unmount());
});

test('clearly keeps the current pick active when a filter excludes it', () => {
  const { container, root } = mount();

  act(() => container.querySelector('[data-testid="feecat-card-midnight-patch"]').click());
  act(() => container.querySelector('[data-testid="feecats-filter-spots"]').click());

  expect(container.querySelector('.cat-preview-panel h2').textContent).toBe('Midnight Patch');
  expect(container.querySelector('[data-testid="feecats-pinned-pick"]')).not.toBeNull();
  expect(container.querySelector('[data-testid="feecats-pinned-pick"]').textContent)
    .toContain('CURRENT PICK');
  expect(container.querySelector('[data-testid="feecats-pinned-pick"]').textContent)
    .toContain('OUTSIDE SPOTTED FILTER');
  expect(container.querySelectorAll('.cat-card-grid .cat-card')).toHaveLength(34);
  expect(container.querySelector('[data-testid="feecats-filter-selection-note"]').textContent)
    .toContain('Current pick: Midnight Patch');
  expect(container.querySelector('[data-testid="feecats-filter-selection-note"]').textContent)
    .toContain('outside the Spotted filter');
  expect(container.querySelector('.cat-preview-top .state-tag').textContent)
    .toBe('CURRENT PICK · OUTSIDE FILTER');
  expect(container.querySelector('.cat-preview-panel > p').textContent)
    .toContain('not in Spotted');

  const pinnedButton = container.querySelector('[data-testid="feecats-pinned-pick"] [data-testid="feecat-card-midnight-patch"]');
  const firstFilteredCard = container.querySelector('.cat-card-grid .cat-card');
  expect(pinnedButton.tagName).toBe('BUTTON');
  expect(pinnedButton.getAttribute('aria-label'))
    .toBe('Midnight Patch, current pick, outside the Spotted filter');
  expect(pinnedButton.getAttribute('aria-describedby'))
    .toBe('feecats-filter-selection-note');
  expect(pinnedButton.getAttribute('aria-pressed')).toBe('true');
  expect(pinnedButton.compareDocumentPosition(firstFilteredCard) & Node.DOCUMENT_POSITION_FOLLOWING)
    .toBeTruthy();
  act(() => pinnedButton.focus());
  expect(document.activeElement).toBe(pinnedButton);

  act(() => pinnedButton.click());
  expect(container.querySelector('.cat-action-notice').textContent).toContain('Midnight Patch selected');
  act(() => container.querySelector('[data-testid="feecats-select"]').click());
  expect(container.querySelector('.cat-action-notice').textContent).toContain('Midnight Patch is your featured cat');

  act(() => container.querySelector('[data-testid="feecats-filter-patch"]').click());
  expect(container.querySelector('[data-testid="feecats-filter-selection-note"]')).toBeNull();
  expect(container.querySelector('[data-testid="feecats-pinned-pick"]')).toBeNull();
  expect(container.querySelector('[data-testid="feecat-card-midnight-patch"]').className).toContain('selected');
  expect(container.querySelector('[data-testid="feecat-card-midnight-patch"]').getAttribute('aria-pressed')).toBe('true');

  act(() => container.querySelector('[data-testid="feecats-filter-stripes"]').click());
  expect(container.querySelector('[data-testid="feecats-filter-selection-note"]').textContent)
    .toContain('outside the Tabby filter');
  expect(container.querySelector('.cat-preview-panel h2').textContent).toBe('Midnight Patch');
  expect(container.querySelector('.cat-preview-panel > p').textContent)
    .toContain('not in Tabby');

  act(() => root.unmount());
});
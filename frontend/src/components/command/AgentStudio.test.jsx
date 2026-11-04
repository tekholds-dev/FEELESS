import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { Creations, PreviewButton, codeIn, lockedPage } from './AgentStudio';

global.IS_REACT_ACT_ENVIRONMENT = true;
const PAGE = 'Here it is:\n```html\n<!doctype html><html><body><h1>Hi</h1></body></html>\n```\nDone.';
async function mount(ui) { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(ui); }); return el; }

test('it finds a page it wrote, and only a page', () => {
  expect(codeIn(PAGE)).toContain('<h1>Hi</h1>');
  expect(codeIn('<html><body>x</body></html>')).toContain('<body>x');
  expect(codeIn('```python\nprint(1)\n```')).toBeNull();
  expect(codeIn('The price is 5')).toBeNull();
});

test('the preview runs sandboxed, with no site access and no network', async () => {
  const el = await mount(<PreviewButton text={PAGE} />);
  await act(async () => { el.querySelector('[data-testid="ast-preview"]').click(); });
  const f = document.querySelector('[data-testid="ast-frame"]');
  expect(f.getAttribute('sandbox')).toBe('allow-scripts');          // never allow-same-origin
  expect(f.getAttribute('srcdoc')).toContain('<h1>Hi</h1>');
  expect(lockedPage('x')).toContain("default-src 'none'");
  await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' })); });
  expect(document.querySelector('[data-testid="ast-frame"]')).toBeNull();
  const none = await mount(<PreviewButton text="no code" />); expect(none.querySelector('[data-testid="ast-preview"]')).toBeNull();
});

test('its creations: images, pages and posts in one folder, only what it made', async () => {
  const files = [{ id: 'a', ext: 'png', name: 'cat.png', url: '/f/a.png' }, { id: 'b', ext: 'pdf', name: 'x.pdf', url: '/f/b.pdf' }];
  const chat = [{ by: 'you', tid: 't0', text: PAGE }, { by: 'cats', tid: 't1', text: PAGE }, { by: 'cats', tid: 't2', text: 'A thread about SOL' }, { by: 'cats', text: 'engine note' }];
  const el = await mount(<Creations files={files} chat={chat} />);
  expect(el.querySelectorAll('.ast-grid img')).toHaveLength(1);
  await act(async () => { el.querySelector('[data-testid="ast-tab-pages"]').click(); });
  expect(el.querySelectorAll('.ast-rows li')).toHaveLength(1);
  await act(async () => { el.querySelector('[data-testid="ast-page-0"]').click(); });
  expect(document.querySelector('[data-testid="ast-frame"]')).not.toBeNull();
  await act(async () => { document.querySelector('[data-testid="ast-close"]').click(); });
  await act(async () => { el.querySelector('[data-testid="ast-tab-posts"]').click(); });
  expect(el.querySelector('.ast-rows').textContent).toContain('A thread about SOL'); expect(el.querySelector('.ast-rows').textContent).not.toContain('engine note');
});

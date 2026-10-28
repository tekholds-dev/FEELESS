import { layoutIssues } from './perfWatch';

test('🧱 the page watcher: a clean page reports nothing; a page wider than the screen reports by how much', () => {
  document.body.innerHTML = '<main><p class="ok">hello</p></main>';
  expect(layoutIssues()).toBeNull();
  Object.defineProperty(document.documentElement, 'scrollWidth', { configurable: true, value: window.innerWidth + 40 });
  expect(layoutIssues().sideways).toBe(40);
  delete document.documentElement.scrollWidth;
});

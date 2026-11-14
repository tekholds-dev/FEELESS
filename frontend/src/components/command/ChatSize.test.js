import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ChatGrip, ChatSizeSeg, clampH, readSize, useChatSize } from './ChatSize';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('a stored size is read safely; a dragged height stays on the screen', () => {
  expect(readSize(null)).toEqual({ mode: 'half', h: null, back: 'half' });
  expect(readSize('{"mode":"focus","back":"dock"}')).toEqual({ mode: 'focus', h: null, back: 'dock' });
  expect(readSize('{"mode":"custom","h":512.4}')).toEqual({ mode: 'custom', h: 512, back: 'half' });
  expect(readSize('{"mode":"custom","h":20}').mode).toBe('half');   // too small to be real
  expect(readSize('not json').mode).toBe('half'); expect(readSize('{"mode":"giant"}').mode).toBe('half');
  expect(clampH(100, 900)).toBe(260); expect(clampH(5000, 900)).toBe(780); expect(clampH(500, 900)).toBe(500);
});

function Box() {
  const s = useChatSize();
  return <section data-testid="dash" {...s.attrs}><ChatSizeSeg size={s.size} pick={s.pick} /><button type="button" data-testid="dbl" onClick={s.toggleFocus}>h</button>
    <ChatGrip measure={() => 480} onDrag={s.drag} /></section>;
}

test('Dock / Half / Focus, double-click = Focus and back, a drag sizes it, and it is remembered', () => {
  localStorage.clear();
  const host = document.createElement('div'); document.body.appendChild(host); let root = createRoot(host);
  act(() => root.render(<Box />));
  const dash = () => host.querySelector('[data-testid=dash]');
  expect(dash().getAttribute('data-chat')).toBe('half');
  act(() => { host.querySelector('[data-testid=csz-dock]').click(); }); expect(dash().getAttribute('data-chat')).toBe('dock');
  act(() => { host.querySelector('[data-testid=dbl]').click(); }); expect(dash().getAttribute('data-chat')).toBe('focus');
  act(() => { host.querySelector('[data-testid=dbl]').click(); }); expect(dash().getAttribute('data-chat')).toBe('dock');   // back to where it was
  const grip = host.querySelector('[data-testid=csz-grip]');
  act(() => { grip.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowUp', bubbles: true })); });   // 480 + 40
  expect(dash().getAttribute('data-chat')).toBe('custom'); expect(dash().style.getPropertyValue('--cwb-h')).toBe('520px');
  act(() => root.unmount()); root = createRoot(host);
  act(() => root.render(<Box />));   // a fresh visit
  expect(dash().getAttribute('data-chat')).toBe('custom'); expect(dash().style.getPropertyValue('--cwb-h')).toBe('520px');
  act(() => root.unmount()); host.remove();
});

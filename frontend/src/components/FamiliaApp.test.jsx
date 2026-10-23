import React, { act } from 'react';
import { createRoot } from 'react-dom/client';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mockGo = jest.fn(); const mockSeg = 'wars';
jest.mock('react-router-dom', () => ({ Link: ({ children, to, ...p }) => <a href={to} {...p}>{children}</a>, useNavigate: () => mockGo, useParams: () => ({ '*': mockSeg }), NavLink: ({ children }) => <a>{children}</a>, useLocation: () => ({ pathname: '/familia/city' }) }), { virtual: true });
jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: null, connect: jest.fn() }) }));
jest.mock('./CrewCard', () => ({ useCrewBoard: () => ({ total: 7 }) }));
jest.mock('./FamiliaBackdrop', () => ({ FamiliaBackdrop: ({ scene }) => <i data-testid="bd" data-scene={scene} />, SCENES: { home: ['Fee City'], wars: ['The War Room'] } }));
jest.mock('../lib/familiaLoad', () => ({ loadFamilia: () => Promise.resolve({ Crews: ({ tab, onTab, bare, onScene }) => { onScene?.(tab); return <div data-testid="crews" data-tab={tab} data-bare={String(bare)}><button type="button" data-testid="join" onClick={() => onTab('family')} /></div>; } }) }));
jest.mock('../lib/sharedJson', () => ({ sharedJson: () => Promise.resolve({ wars: [{ state: 'live' }, { state: 'live' }, { state: 'done' }] }), _resetShared: () => {}, markFresh: () => {} }));

test('🌹 La Familia is its own app: the URL picks the tab, the shell owns the nav, the pulse is live, the terminal tab bar steps aside', async () => {
  const FamiliaApp = require('./FamiliaApp').default; const { FA_NAV } = require('./FamiliaApp');
  expect(FA_NAV.map(n => n[1])).toEqual(['city', 'family', 'wars', 'board', 'live']);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { root.render(<FamiliaApp />); }); await act(async () => { await Promise.resolve(); await Promise.resolve(); });
  expect(document.title).toBe('La Familia · FEELESS'); expect(document.body.classList.contains('in-familia')).toBe(true);
  expect(q('crews').dataset.tab).toBe('wars'); expect(q('crews').dataset.bare).toBe('true');                 // /familia/wars → the Wars tab, Crews draws no nav of its own
  expect(q('fa-tab-wars').getAttribute('aria-selected')).toBe('true'); expect(q('fa-tab-wars').textContent).toContain('2');   // two wars burning
  expect(q('familia-app').textContent).toContain('7'); expect(q('bd').dataset.scene).toBe('wars');
  act(() => q('fa-tab-board').click()); expect(mockGo).toHaveBeenLastCalledWith('/familia/board');
  act(() => q('join').click()); expect(mockGo).toHaveBeenLastCalledWith('/familia/family');                   // the app's own jumps stay in the app
  expect(q('fa-connect')).not.toBeNull(); expect(q('fa-exit').getAttribute('href')).toBe('/terminal');
  await act(async () => { root.unmount(); });
  expect(document.body.classList.contains('in-familia')).toBe(false);
});

test('the phone tab bar hides inside La Familia (it has its own dock)', () => {
  const { MobileTabBar } = require('./MobileTabBar');
  const el = document.createElement('div'); const root = createRoot(el);
  act(() => root.render(<MobileTabBar />)); expect(el.querySelector('.mobile-tabbar')).toBeNull(); act(() => root.unmount());
});

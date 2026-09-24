import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { TerminalSidebar } from './TerminalShell';

let mockPathname = '/terminal';

jest.mock('react-router-dom', () => {
  const mockReact = require('react');
  const renderLink = ({ children, className, to, end: _end, ...props }) => {
    const isActive = mockPathname === to || (to === '/terminal/feecat' && mockPathname.startsWith('/terminal/feecat'));
    const resolvedClassName = typeof className === 'function' ? className({ isActive }) : className;
    const content = typeof children === 'function' ? children({ isActive }) : children;
    return mockReact.createElement('a', { ...props, className: resolvedClassName, href: to }, content);
  };
  return {
    Link: renderLink,
    NavLink: renderLink,
    useLocation: () => ({ pathname: mockPathname }),
    useNavigate: () => jest.fn(),
  };
}, { virtual: true });

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('keeps the FeeCat dropdown reachable from the collapsed mobile sidebar', () => {
  const onClose = jest.fn();
  const host = document.createElement('div');
  document.body.appendChild(host);
  const root = createRoot(host);

  act(() => root.render(<TerminalSidebar open onClose={onClose} savedCount={0} />));
  expect(host.querySelector('[data-testid="feecat-subnav"]')).toBeNull();

  act(() => host.querySelector('[data-testid="nav-feecat-toggle"]').click());
  expect(host.querySelector('[data-testid="feecat-subnav"]')).not.toBeNull();
  expect(host.querySelector('[data-testid="nav-feeless-cats"]').textContent).toContain('Feeless Cats');

  act(() => host.querySelector('[data-testid="nav-feeless-cats"]').click());
  expect(onClose).toHaveBeenCalledTimes(1);

  act(() => root.unmount());
  host.remove();
});
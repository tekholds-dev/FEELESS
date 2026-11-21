import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
jest.mock('./QuickTrade', () => ({ QuickTrade: ({ pair }) => <form data-testid="qt">buy {pair.baseToken.symbol}<input data-testid="qt-amt" defaultValue="" /></form> }));
jest.mock('./DipRipTool', () => ({ DipRipTool: () => <div data-testid="diprip">dip & rip</div> }));
jest.mock('../Shield', () => ({ ShieldBadge: () => <span data-testid="shield" /> }));
jest.mock('./EdgeScore', () => ({ EdgeScore: () => <p data-testid="edge">edge 63</p> }));
jest.mock('./LaunchForensics', () => ({ LaunchForensics: () => <p data-testid="forensics">snipers</p> }));
jest.mock('../CaseFile', () => ({ investigate: jest.fn() }));
// eslint-disable-next-line import/first
import { TradeChatFlip, TrenchTools } from './TrenchFlip';
// eslint-disable-next-line import/first
import { investigate } from '../CaseFile';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const PAIR = { chainId: 'solana', pairAddress: 'P', baseToken: { symbol: 'PENNY', address: 'MintPenny111' } };
function Chat({ ids }) { return <ol>{ids.map(i => <li key={i} data-testid={`chat-message-${i}`}>m{i}</li>)}</ol>; }

test('🔁 the right card flips: Quick trade (Market / Dip & rip) ⇄ chat; a typed amount survives; chat counts unread while hidden', async () => {
  localStorage.removeItem('feeless.trenchFlip'); localStorage.removeItem('feeless.trenchOrder');
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const render = ids => act(async () => { root.render(<TradeChatFlip pair={PAIR} chat={<Chat ids={ids} />} />); });
  await render([1, 2]);
  expect(el.querySelector('[data-testid="tfl-trade"]').hidden).toBe(false); expect(el.querySelector('[data-testid="tfl-chat"]').hidden).toBe(true);
  expect(el.querySelector('[data-testid="qt"]').textContent).toContain('PENNY'); expect(el.querySelector('[data-testid="shield"]')).not.toBeNull();
  el.querySelector('[data-testid="qt-amt"]').value = '0.25';
  await act(async () => { el.querySelector('[data-testid="tfl-order-dr"]').click(); });
  expect(el.querySelector('[data-testid="diprip"]').parentElement.hidden).toBe(false); expect(el.querySelector('[data-testid="qt"]').parentElement.hidden).toBe(true);
  await act(async () => { el.querySelector('[data-testid="tfl-order-mkt"]').click(); });
  expect(el.querySelector('[data-testid="qt-amt"]').value).toBe('0.25');   // never unmounted: nothing typed is lost
  await render([1, 2, 3, 4]);   // two messages land while you trade
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(el.querySelector('[data-testid="tfl-unread"]').textContent).toBe('2');
  await act(async () => { el.querySelector('[data-testid="tfl-to-chat"]').click(); });
  expect(el.querySelector('[data-testid="tfl-chat"]').hidden).toBe(false); expect(el.querySelector('[data-testid="tfl-unread"]')).toBeNull();
  expect(localStorage.getItem('feeless.trenchFlip')).toBe('chat');
  await act(async () => { root.unmount(); }); el.remove();
});

test('🧰 Tools: one popover, each tool in its own window (Calls log, Why this read, forensics), Case file and Wide act directly', async () => {
  const onWide = jest.fn();
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<TrenchTools pair={PAIR} wide={false} onWide={onWide} calls={<p data-testid="calls">hot calls</p>} />); });
  expect(el.querySelector('[data-testid="trench-tools-pop"]')).toBeNull();
  const open = () => act(async () => { el.querySelector('[data-testid="trench-tools"]').click(); });
  await open(); expect(el.querySelectorAll('[data-testid^="trench-tool-"]')).toHaveLength(5);
  await act(async () => { el.querySelector('[data-testid="trench-tool-calls"]').click(); });
  expect(el.querySelector('[data-testid="trench-win"] [data-testid="calls"]')).not.toBeNull();
  await act(async () => { el.querySelector('[data-testid="trench-win-close"]').click(); });
  await open(); await act(async () => { el.querySelector('[data-testid="trench-tool-why"]').click(); });
  expect(el.querySelector('[data-testid="edge"]')).not.toBeNull();
  await act(async () => { el.querySelector('[data-testid="trench-win-close"]').click(); });
  await open(); await act(async () => { el.querySelector('[data-testid="trench-tool-case"]').click(); });
  expect(investigate).toHaveBeenCalledWith('MintPenny111');
  await open(); await act(async () => { el.querySelector('[data-testid="trench-tool-wide"]').click(); });
  expect(onWide).toHaveBeenCalled();
  await act(async () => { root.unmount(); }); el.remove();
});

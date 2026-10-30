import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { mindStats, tradeChat, catLogItems, AgentLog, MindVitals, TradeChat, readSkin } from './CatCockpit';
import { genLog } from './CatWorkbench';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mount = async node => { const el = document.createElement('div'); const root = createRoot(el); await act(async () => { root.render(node); }); return el; };
const CAT = { id: 'c1', brainsCfg: { brains: ['a/ossy', 'b/g4'], decisions: [{ at: 10, word: 'BUY', sym: 'GERM', by: 'ossy', why: 'germ floor', usd: 0.001 }, { at: 20, word: 'SKIP', sym: 'RUG', by: 'g4', why: 'bundlers' }],
  cloud: [{ at: 30, word: 'BUY', sym: 'GERM', by: ['g4', 'ossy'] }], chime: [{ at: 15, text: 'watch SOL' }] } };

test('🧠 each mind\'s vitals come from its own calls; the chat puts A left, B right, you on the right', () => {
  expect(mindStats(CAT, 'a/ossy')).toMatchObject({ calls: 1, buys: 1, agreed: 1, spark: ['up'] });
  expect(mindStats(CAT, 'b/g4')).toMatchObject({ calls: 1, buys: 0, agreed: 1 });
  expect(tradeChat(CAT).map(r => r.side)).toEqual(['a', 'you', 'b']);
});

test('📁 the log files every kind of thing in its folder, newest first', async () => {
  const ev = [{ type: 'BUY', ts: 40000, detail: 'Bought 0.05 SOL of GERM' }, { type: 'STOPPED', ts: 50000, detail: 'paused: cap' }];
  const items = catLogItems(CAT, ev);
  expect(items[0].f).toBe('guards'); expect(new Set(items.map(x => x.f))).toEqual(new Set(['trades', 'guards', 'thoughts', 'cloud']));
  const el = await mount(<AgentLog items={items} />);
  expect(el.querySelectorAll('.ck-rows li')).toHaveLength(items.length);
  await act(async () => { el.querySelector('[data-testid="log-cloud"]').click(); });
  expect(el.querySelectorAll('.ck-rows li')).toHaveLength(1);
  expect(genLog({ chat: [{ by: 'you', text: 'best bet?', at: 5 }], refusals: [{ why: 'Refused: create a coin', at: 9 }] }).map(x => x.f)).toEqual(['guards', 'tasks']);
});

test('🛸 vitals + chat render, the chime goes out, a broken skin falls back', async () => {
  const send = jest.fn(() => Promise.resolve(true));
  const el = await mount(<><MindVitals cat={CAT} model="a/ossy" i={0} live /><TradeChat cat={CAT} onSend={send} /></>);
  expect(el.textContent).toContain('BRAIN A'); expect(el.querySelectorAll('.ck-msg')).toHaveLength(3);
  await act(async () => { const i = el.querySelector('[data-testid="ck-chime"]'); Object.getOwnPropertyDescriptor(Object.getPrototypeOf(i), 'value').set.call(i, 'hold longer'); i.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { el.querySelector('.ck-say').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); });
  expect(send).toHaveBeenCalledWith('hold longer');
  localStorage.setItem('feeless.deskSkin', '{"bg":"lava","acc":"#000"}'); expect(readSkin()).toEqual({ bg: 'ocean', acc: '#b388ff' });
});

test('🔐 the first funding stays locked until "I saved my recovery phrase" is ticked — and it shows ITS wallet', async () => {
  const { FundCat } = require('./CatReal');
  localStorage.removeItem('feeless.recoverySaved.c9');
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ feeUsd: 2, minUsd: 10, topupMinUsd: 1 }) }));
  const onConfirm = jest.fn();
  const el = await mount(<FundCat cat={{ id: 'c9', name: 'Scout', agentWallet: { address: 'AgEnTwa11et1111111111111111111111111111111' } }} addr="OwnerWa11et" session={() => Promise.resolve('s')} sign={jest.fn()} onConfirm={onConfirm} />);
  expect(el.querySelector('[data-testid="cr-safe-addr"]').textContent).toContain('AgEnTwa11et');
  expect(el.querySelector('[data-testid="cr-fund-quote"]').disabled).toBe(true);
  await act(async () => { el.querySelector('[data-testid="cr-safe-check"]').click(); });
  expect(onConfirm).toHaveBeenCalled(); expect(el.querySelector('[data-testid="cr-fund-quote"]').disabled).toBe(false);
});

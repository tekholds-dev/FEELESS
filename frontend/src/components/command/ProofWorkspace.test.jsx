import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ProofWorkspace, MindsThread, readWs } from './ProofWorkspace';
import { StartWizard } from './StartWizard';
import { StartedWith, TrueRecord } from './TrueRecord';

// 🗂 Slice 33: the shared shell every opened filing lives on, the start wizard in front of PoC / PoEco / PoStatic jobs, and the record's STARTED WITH.
global.IS_REACT_ACT_ENVIRONMENT = true;
const W = id => document.querySelector(`[data-testid="${id}"]`);
async function mount(node) { const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); await act(async () => { root.render(node); }); return { el, root, done: async () => { await act(async () => root.unmount()); el.remove(); } }; }
const until = async (fn, n = 60) => { for (let i = 0; i < n && !fn(); i += 1) await act(async () => { await new Promise(r => setTimeout(r, 15)); }); expect(fn()).toBeTruthy(); };   // Motion's exit runs on frames
const tap = async id => { await until(() => W(id)); await act(async () => { W(id).click(); }); };
beforeEach(() => { try { localStorage.clear(); } catch { /* none */ } });

test('the shell: slim bar with name, status, cost and back; chat and tools panes; no pane when a view has none', async () => {
  const back = jest.fn();
  const m = await mount(<ProofWorkspace id="t1" kind="poe" name="PoEco #4" status="paid" tone="good" cost={0.0046} onBack={back} backLabel="PoEco" backId="eco-back" chat={<p>talk</p>} tools={<p>rec</p>}><p data-testid="the-work">work</p></ProofWorkspace>);
  expect(W('pws-name').textContent).toBe('PoEco #4'); expect(W('pws-status').textContent).toContain('paid'); expect(W('pws-cost').textContent).toContain('$0.0046');
  expect(W('the-work')).toBeTruthy(); expect(W('pws-chat').textContent).toContain('talk'); expect(W('pws-tools').textContent).toContain('rec');
  await act(async () => { W('eco-back').click(); }); expect(back).toHaveBeenCalled();
  await m.done();
  const n = await mount(<ProofWorkspace id="t2" kind="pow" name="X"><p>w</p></ProofWorkspace>);
  expect(W('pws-chat')).toBeNull(); expect(W('pws-tools')).toBeNull(); expect(W('pws-tg-chat')).toBeNull();
  await n.done();
});

test('the shell: a pane pops out and docks back, and it remembers that per view', async () => {
  const m = await mount(<ProofWorkspace id="t3" kind="poc" name="PoC #1" chat={<p>talk</p>} chatLabel="Minds"><p>w</p></ProofWorkspace>);
  await act(async () => { W('pws-pop-chat').click(); });
  expect(W('pws-chat')).toBeNull(); expect(W('pws-float-chat')).toBeTruthy(); expect(W('pws-float-chat').textContent).toContain('talk');
  expect(readWs('t3').pop.chat).toBe('float');
  await m.done();
  const again = await mount(<ProofWorkspace id="t3" kind="poc" name="PoC #1" chat={<p>talk</p>}><p>w</p></ProofWorkspace>);
  expect(W('pws-float-chat')).toBeTruthy();   // remembered
  await act(async () => { W('pws-tg-chat').click(); });   // the bar docks it again
  await until(() => !W('pws-float-chat')); expect(W('pws-chat')).toBeTruthy(); expect(readWs('t3').pop.chat).toBe('dock');
  await again.done();
});

test('the minds thread is read-only and says so when empty', async () => {
  const m = await mount(<MindsThread rows={[{ by: 'Mind A', title: 'YES', text: 'because' }, { by: 'Mind B', text: 'no' }]} />);
  expect(document.querySelectorAll('.pws-thread li')).toHaveLength(2); expect(document.querySelector('.pws-thread li.is-b').textContent).toContain('no');
  expect(document.querySelector('.pws-thread input, .pws-thread textarea')).toBeNull();
  await m.done();
});

const OPTS = { kind: 'poe', label: 'PoEco', brief: 'Logo job', goal: 'Win it', pitch: ['Bid $40', 'Ship in a day'], kits: [{ id: 'k1', name: 'Kit one' }, { id: 'k2', name: 'Kit two' }], picks: [], mode: 'auto',
  starts: [{ id: 'f7', label: 'PoEco #7', sub: 'old', good: true }], max: 3, minds: ['m-a', 'm-b'], cost: { usd: 0.02, n: 3 },
  research: [{ by: 'minds', label: 'The minds', tip: '', usd: 0, mind: null }, { by: 'g4', label: 'G4', tip: 'local', usd: 0, mind: 'G4' }] };

test('the start wizard: direction → kits + start → research, minds and cost before Go, every choice in the start call', async () => {
  const work = jest.fn(async () => ({ wizard: OPTS })); const onGo = jest.fn(async () => ({})); const close = jest.fn();
  const m = await mount(<StartWizard open cat={{ id: 'c' }} work={work} kind="poe" job="L1" onGo={onGo} onClose={close} goLabel="Draft the bid" />);
  expect(work).toHaveBeenCalledWith('c', { op: 'wizard_opts', text: 'poe', job: 'L1', cap: '' });
  await until(() => W('swz-brief')); expect(W('swz-brief').textContent).toBe('Logo job'); expect(W('swz').textContent).toContain('Bid $40');
  const ta = W('swz-direction'); await act(async () => { Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(ta, 'Bid $35 instead'); ta.dispatchEvent(new Event('input', { bubbles: true })); });
  expect(W('swz-approve').textContent).toContain('Approve my direction');
  await tap('swz-approve'); await tap('swz-kit-k2'); await tap('swz-start-f7'); await tap('swz-next'); await tap('swz-research-g4');
  expect(W('swz-minds').textContent).toBe('m-a + m-b + G4'); expect(W('swz-cost').textContent).toContain('0.02');
  expect(onGo).not.toHaveBeenCalled();
  await tap('swz-go');
  expect(onGo).toHaveBeenCalledWith({ direction: { text: 'Bid $35 instead', pitch: 'Bid $40 · Ship in a day', approved: true }, kits: ['k2'], start: 'f7', research: { by: 'g4' } });
  expect(close).toHaveBeenCalled();
  await m.done();
});

test('the start wizard: a refused start keeps it open with the reason', async () => {
  const work = jest.fn(async () => ({ wizard: OPTS })); const onGo = jest.fn(async () => { throw new Error('needs model credit'); }); const close = jest.fn();
  const m = await mount(<StartWizard open cat={{ id: 'c' }} work={work} kind="poe" job="L1" onGo={onGo} onClose={close} />);
  await tap('swz-approve'); await tap('swz-next'); await tap('swz-go');
  await until(() => W('swz-err')); expect(W('swz-err').textContent).toContain('needs model credit'); expect(close).not.toHaveBeenCalled();
  await m.done();
});

test('the record shows what he started it with, read from the filing', async () => {
  const w = { kind: 'poe', direction: 'Bid $35 instead', edited: true, kits: ['k2'], start: 'f7', startN: 7, research: { by: 'g4', ok: false, why: 'G4 did not answer. No other model stands in.', refs: [] } };
  const m = await mount(<><StartedWith w={w} /><StartedWith w={w} line /></>);
  expect(W('started-with').textContent).toContain('his direction'); expect(W('started-with').textContent).toContain('from #7'); expect(W('started-with').textContent).toContain('No other model stands in');
  expect(W('trc-wizard').textContent).toContain('kits k2');
  await m.done();
  const n = await mount(<StartedWith w={null} />); expect(W('started-with')).toBeNull(); await n.done();
  expect(typeof TrueRecord).toBe('function');
});

test('PoEco: Draft bid opens the wizard (no bare start); Go sends earn_bid with every choice; the opened filing sits on the shell with STARTED WITH', async () => {
  const { EcoFolder } = require('./EcoFolder');
  const ROW = { id: 'algora:1', src: 'algora', title: 'Fix it', url: 'https://github.com/o/r/issues/1', cat: 'code', pay: '$700', payUsd: 700, rivals: 4, score: 76, parts: {}, expProfit: 48, cost: 0.02, chance: 0.07 };
  const F = { id: 'earn1', n: 2, kind: 'earn', stage: 'bid', listing: ROW, platform: { name: 'Algora' }, cost: 0.018, kept: 0, bid: { bid: 'Kept.' }, bids: [{ mind: 0, score: 91, bid: 'Kept.', plan: [], why: [] }],
    wizard: { kind: 'poe', direction: 'Bid $35', edited: true, kits: ['k2'], start: 'fresh', research: { by: 'g4', ok: true, refs: [{ title: 'a' }] } } };
  const work = jest.fn(async (_, b) => (b.op === 'earn_view' ? { board: { at: 1, best: [ROW], kept: 1, seen: 1, out: [] }, platforms: [] } : b.op === 'wizard_opts' ? { wizard: OPTS } : b.op === 'earn_bid' ? { board: { at: 1, best: [ROW], kept: 1, seen: 1, out: [] }, platforms: [], poeFolders: [F] } : {}));
  let d = { poeFolders: [] }; const setD = fn => { d = fn(d); };
  const m = await mount(<EcoFolder cat={{ id: 'c', name: 'Happy' }} d={d} setD={setD} work={work} />);
  await tap('ern-bid-0');
  expect(work).not.toHaveBeenCalledWith('c', expect.objectContaining({ op: 'earn_bid' }));
  expect(work).toHaveBeenCalledWith('c', { op: 'wizard_opts', text: 'poe', job: 'algora:1', cap: '' });
  await tap('swz-approve'); await tap('swz-kit-k1'); await tap('swz-next'); await tap('swz-go');
  expect(work).toHaveBeenCalledWith('c', { op: 'earn_bid', text: 'algora:1', tools: { wizard: { direction: { text: '', pitch: 'Bid $40 · Ship in a day', approved: true }, kits: ['k1'], start: 'fresh', research: { by: 'minds' } } } });
  expect(d.poeFolders[0].id).toBe('earn1');
  await m.done();
  const n = await mount(<EcoFolder cat={{ id: 'c', name: 'Happy' }} d={{ poeFolders: [F] }} setD={() => {}} work={work} focus={{ id: 'earn1', at: 1 }} />);
  await until(() => W('pws-name')); expect(W('pws-name').textContent).toContain('PoEco #2'); expect(W('pws-cost').textContent).toContain('$0.02');
  expect(W('started-with').textContent).toContain('his direction'); expect(W('started-with').textContent).toContain('(1 found)');
  await n.done();
});

test('PoC: File a PoC opens the wizard first; its Go files the PoC with the typed topic and every choice', async () => {
  const { ProofDesk } = require('./FeaturesFolder');
  const work = jest.fn(async (_, b) => (b.op === 'ws_open' ? { doc: { id: 'w1', messages: [] } } : b.op === 'wizard_opts' ? { wizard: { ...OPTS, kind: 'poc', label: 'PoC' } } : { workspaces: [{ id: 'w1', kind: 'content', name: 'Ideas' }], pocFolders: [], psFolders: [] }));
  const m = await mount(<ProofDesk cat={{ id: 'c' }} kind="content" work={work} d={{}} setD={() => {}} />);
  await tap('ws-w1');
  const t = W('ws-poc-topic'); await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(t, 'AI agents'); t.dispatchEvent(new Event('input', { bubbles: true })); });
  await tap('ws-poc');
  expect(work).not.toHaveBeenCalledWith('c', expect.objectContaining({ op: 'poc' }));
  expect(work).toHaveBeenCalledWith('c', { op: 'wizard_opts', text: 'poc', job: 'w1', cap: 'AI agents' });
  await tap('swz-approve'); await tap('swz-start-f7'); await tap('swz-next'); await tap('swz-research-g4'); await tap('swz-go');
  expect(work).toHaveBeenCalledWith('c', { op: 'poc', text: 'AI agents', job: 'w1', tools: { wizard: { direction: { text: '', pitch: 'Bid $40 · Ship in a day', approved: true }, kits: [], start: 'f7', research: { by: 'g4' } } } });
  await m.done();
});

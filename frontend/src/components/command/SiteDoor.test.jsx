import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { SiteDoor, WatchFolders } from './SiteDoor';

global.IS_REACT_ACT_ENVIRONMENT = true;
const rule = (t, page = 'terms') => ({ t, q: `${t} in its own words`, src: `https://a.io/${page}`, page });
const manual = over => ({ site: 'a.io', slug: 'a', url: 'https://a.io', kinds: ['pow'], at: Date.now() / 1000, state: 'read', botSay: 'silent', pages: [{ kind: 'terms', url: 'https://a.io/t', title: 'Terms', chars: 2000, ok: true, via: 'fetch' }], do: [rule('Keep your wallet safe')], dont: [rule('No bots')], withdraw: [rule('Withdrawals take an hour')], fees: [], bots: [], regions: [], risk: [], ...over });
const q = (el, id) => el.querySelector(`[data-testid="${id}"]`);
const click = async node => { await act(async () => { node.click(); }); };

function Host({ d: first, work }) {
  const [d, setD] = React.useState(first);
  return <SiteDoor kind="pow" cat={{ id: 'c' }} d={d} setD={setD} work={work} />;
}
async function mount(ui) { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(ui); }); return el; }
async function open(over, d = {}, work = jest.fn()) {
  const el = await mount(<Host d={{ ...d, siteManuals: { 'a.io': manual(over) } }} work={work} />);
  await click(q(el, 'sd-site-a.io'));
  return el;
}

test('scan sends what was typed for this proof kind, and shows it is reading', async () => {
  const work = jest.fn().mockResolvedValue({ ok: true, siteScan: 'a.io' });
  const el = await mount(<Host d={{}} work={work} />);
  const input = q(el, 'sd-input-pow');
  await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, 'a.io'); input.dispatchEvent(new Event('input', { bubbles: true })); });
  await click(q(el, 'sd-scan-pow'));
  expect(work).toHaveBeenCalledWith('c', { op: 'site_scan', text: 'a.io', job: 'pow' });
  expect(q(el, 'sd-scanning').textContent).toContain('a.io');
});

test('a site scanned from another folder does not show here', async () => {
  const el = await mount(<Host d={{ siteManuals: { 'a.io': manual({ kinds: ['pob'] }) } }} work={jest.fn()} />);
  expect(q(el, 'sd-site-a.io')).toBeNull();
});

test('the manual opens on its bans, and its command waits for a sign-in', async () => {
  const el = await open();
  expect(q(el, 'sd-rows-dont').textContent).toContain('No bots');
  expect(q(el, 'sd-unlock')).not.toBeNull();
  expect(q(el, 'sd-file')).toBeNull();
});

test('a signed-in manual earns its command, and the button uses the server door', async () => {
  const work = jest.fn().mockResolvedValue({ ok: true, say: 'Filing' });
  const el = await open({}, { signedIn: [{ site: 'a.io' }] }, work);
  await click(q(el, 'sd-file'));
  expect(work).toHaveBeenCalledWith('c', { op: 'site_file', text: 'file a a pow' });
  expect(q(el, 'sd-cmd').textContent).toContain('Filing');
});

test('withdraw lines are numbered as steps only when a model ordered them', async () => {
  const plain = await open();
  await click(q(plain, 'sd-tab-withdraw'));
  expect(q(plain, 'sd-withdraw').tagName).toBe('UL');
  const worded = await open({ model: 'x' });
  await click(q(worded, 'sd-tab-withdraw'));
  expect(q(worded, 'sd-withdraw').tagName).toBe('OL');
});

test('a walled site says so, and offers no command', async () => {
  const el = await open({ state: 'unread', wall: 'a bot check', pages: [], do: [], dont: [], withdraw: [] }, { signedIn: [{ site: 'a.io' }] });
  expect(q(el, 'sd-wall').textContent).toContain('a bot check');
  expect(q(el, 'sd-file')).toBeNull();
});

test('a wallet watch shows the chain check on each address', async () => {
  const el = await mount(<WatchFolders rows={[{ id: 'w', n: 1, at: 1, checked: true, sites: ['pump.fun'], wallets: [{ address: 'A'.repeat(44), txs: 0, lines: ['x'] }, { address: 'B'.repeat(44), txs: null, lines: [] }, { address: 'C'.repeat(44), txs: 20, lines: [] }] }]} />);
  await click(q(el, 'watch-w'));
  const f = q(el, 'watch-folder').textContent;
  expect(f).toContain('NO HISTORY'); expect(f).toContain('NOT CHECKED'); expect(f).toContain('ON CHAIN 20+');
});

jest.mock('../perps/PerpsChart', () => ({ PerpsChart: () => null }));
import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CatWorkbench, CommandList, Window, placeIcons } from './CatWorkbench';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const signed = [];
jest.mock('../../hooks/useWallet', () => ({ useWallet: () => ({ signMessage: async m => { signed.push(m); return 'SIG'; } }) }));

const STATE = { live: true, providers: ['steel', 'reader'], cap: 0.05, credit: 9.2, chat: [{ by: 'you', text: 'hi' }, { by: 'cats', text: 'hello', cost: 0.0004 }],
  task: { id: 't', text: 'research', status: 'working', cap: 0.05, cost: 0.013 },
  windows: [{ i: 0, model: 'qwen/qwen3-32b', status: 'working', provider: 'steel', url: 'https://kalshi.com', bubble: 'reading the YES ladder', steps: [{ action: 'open', thought: 'open Kalshi' }], cost: 0.008 },
    { i: 1, model: 'x/opus', status: 'human', provider: 'reader', url: 'https://site/login', bubble: '✋ needs you', human: { why: 'a sign-in' }, steps: [], cost: 0.005 }] };

test('🧠🧠 two windows with their provider + bubble; a sign-in pauses one with ✋ continue; one chat; the $ cap; the ask is sent', async () => {
  const calls = [];
  global.fetch = async (u, o) => { const b = JSON.parse(o.body); calls.push(b); return { ok: true, json: async () => (b.op === 'state' ? STATE : { ...STATE, task: { ...STATE.task, status: 'done', answer: 'YES at $0.31' }, windows: STATE.windows.map(w => ({ ...w, status: 'done' })) }) }; };
  localStorage.setItem('feeless-paper-owner', 'browser-1');
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CatWorkbench cat={{ id: 'g1', brainsCfg: { kind: 'general', brains: ['qwen/qwen3-32b', 'x/opus'], credit: 9.2 } }} />); });
  expect(calls[0]).toEqual({ ownerId: 'browser-1', session: '', op: 'state', ver: null });   // ⚡ the first poll asks for everything (no folder version yet)
  expect(el.querySelector('[data-testid="cwb-win-0"]').textContent).toContain('STEEL'); expect(el.querySelector('[data-testid="cwb-bubble"]').textContent).toContain('reading the YES ladder');
  expect(el.querySelector('[data-testid="cwb-human"]').textContent).toContain('a sign-in');
  expect(el.textContent).toContain('$0.0130 / $0.0500');
  await act(async () => { el.querySelector('[data-testid="cwb-continue"]').click(); });
  expect(calls.at(-1)).toMatchObject({ op: 'continue', i: 1 });
  expect(el.querySelector('[data-testid="cwb-answer"]')).toBeNull();   // a finished answer lives in the chat — no duplicate card over it (it hid the chat)
  await act(async () => { el.querySelector('[data-testid="cwb-gear"]').click(); });
  await act(async () => { el.querySelector('[data-testid="cwb-cap-0.25"]').click(); });
  expect(calls.at(-1)).toMatchObject({ op: 'cap', cap: 0.25 });
  const inp = el.querySelector('[data-testid="cwb-input"]');
  await act(async () => { const set = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set; set.call(inp, 'find best bids'); inp.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { el.querySelector('[data-testid="cwb-send"]').click(); });
  expect(calls.at(-1)).toMatchObject({ op: 'ask', text: 'find best bids', to: 'both' });
  await act(async () => { el.querySelector('[data-testid="cwb-to-1"]').click(); });
  await act(async () => { const set = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set; set.call(inp, 'only you'); inp.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { el.querySelector('[data-testid="cwb-send"]').click(); });
  expect(calls.at(-1)).toMatchObject({ op: 'ask', text: 'only you', to: '1' });                       // one mind takes the whole task
  await act(async () => { root.unmount(); });
});

test('☁ the + puts an image in its storage, shows a chip + the storage meter, and the next ask carries it; non-images are refused here', async () => {
  const calls = []; const idle = { ...STATE, task: { ...STATE.task, status: 'done', answer: 'ok' }, windows: STATE.windows.map(w => ({ ...w, status: 'idle', human: null })) };
  const FILE = { id: 'a'.repeat(32), name: 'logo.png', mime: 'image/png', size: 2048, url: `/api/cats/g1/files/${'a'.repeat(32)}.png` };
  global.fetch = async (u, o) => { const b = JSON.parse(o.body); calls.push([String(u), b]);
    return { ok: true, json: async () => (String(u).endsWith('/files') ? { file: FILE, used: 2048, quota: 1024 ** 3, ttlDays: 7 } : idle) }; };
  localStorage.setItem('feeless-paper-owner', 'browser-1');
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CatWorkbench cat={{ id: 'g1', brainsCfg: { kind: 'general', brains: ['qwen/qwen3-32b'], credit: 2.5 } }} />); });
  const plus = el.querySelector('[data-testid="cwb-plus"]'); expect(plus.getAttribute('data-tip')).toContain('own storage');
  const input = el.querySelector('[data-testid="cwb-file-input"]');
  const put = async files => { Object.defineProperty(input, 'files', { configurable: true, value: files }); await act(async () => { input.dispatchEvent(new Event('change', { bubbles: true })); await new Promise(r => setTimeout(r, 30)); }); };
  await put([new File(['<html>'], 'x.html', { type: 'text/html' })]);
  expect(el.textContent).toContain('Images only'); expect(calls.some(([u]) => u.endsWith('/files'))).toBe(false);
  await put([new File([new Uint8Array([137, 80, 78, 71])], 'logo.png', { type: 'image/png' })]);
  const up = calls.find(([u]) => u.endsWith('/api/cats/g1/files'));
  expect(up[1]).toMatchObject({ ownerId: 'browser-1', name: 'logo.png' }); expect(up[1].dataUrl).toMatch(/^data:image\/png;base64,/);
  expect(el.querySelector('[data-testid="cwb-files"]').textContent).toContain('logo.png'); expect(el.querySelector('[data-testid="cwb-store"]').textContent).toContain('2 KB / 1.0 GB');
  const inp = el.querySelector('[data-testid="cwb-input"]');
  await act(async () => { const set = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set; set.call(inp, 'launch my coin on pump.fun with this logo'); inp.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { el.querySelector('[data-testid="cwb-send"]').click(); });
  expect(calls.at(-1)[1]).toMatchObject({ op: 'ask', text: 'launch my coin on pump.fun with this logo', files: [FILE.id] });
  expect(el.querySelector('[data-testid="cwb-files"]')).toBeNull();                       // sent: the chips clear
  act(() => root.unmount()); el.remove();
});

test('🔑 a window sign-in is a small card → the credentials drawer opens with the site filled in; saved sealed; rows show the site only until 👁', async () => {
  sessionStorage.setItem('feeless:safe-place', '1');   // the safe-place check answered (its own test below)
  const calls = [];
  const LOGIN = { ...STATE, logins: [{ site: 'x.com', user: 'me@mail.com', at: 1 }],
    windows: [{ i: 0, model: 'm/a', status: 'human', provider: 'steel', url: 'https://www.dropbox.com/login', human: { kind: 'login', site: 'dropbox.com', why: 'log in to dropbox.com' }, steps: [] }] };
  global.fetch = async (u, o) => { const b = JSON.parse(o.body); calls.push(b);
    return { ok: true, json: async () => (b.op === 'reveal' ? { password: 'Sup3r!pw' } : b.op === 'save_login' ? { ok: true, logins: [...LOGIN.logins, { site: 'dropbox.com', user: b.user }] } : LOGIN) }; };
  Element.prototype.scrollIntoView = () => {};
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CatWorkbench cat={{ id: 'g1', brainsCfg: { kind: 'general', brains: ['m/a'], credit: 1 } }} />); });
  const card = document.querySelector('[data-testid="cwb-login"]');
  expect(card.textContent).toContain('dropbox.com needs a sign-in'); expect(card.querySelector('input')).toBeNull();   // no form inside the window
  expect(document.querySelector('[data-testid="cwb-vault"]')).toBeNull();                                                      // in its cabinet drawer, closed
  await act(async () => { card.querySelector('[data-testid="cwb-login-go"]').click(); });
  const vault = document.querySelector('[data-testid="cwb-vault"]');                                                            // the card opened the 🔐 drawer
  expect(vault.textContent).toContain('x.com'); expect(vault.textContent).not.toContain('me@mail.com');                 // site name only
  expect(vault.open).toBe(true); expect(document.querySelector('[data-testid="cwb-cred-site"]').value).toBe('dropbox.com');
  expect(document.querySelector('[data-testid="cwb-signup"]').getAttribute('href')).toBe('https://dropbox.com');
  document.querySelector('[data-testid="cwb-login-user"]').value = 'me@drop.com'; document.querySelector('[data-testid="cwb-login-pass"]').value = 'Dr0p!pw';
  await act(async () => { document.querySelector('[data-testid="cwb-cred-add"]').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); });
  expect(calls.find(c => c.op === 'save_login')).toMatchObject({ text: 'dropbox.com', user: 'me@drop.com', secret: 'Dr0p!pw' });
  expect(document.querySelector('[data-testid="cwb-login-pass"]').value).toBe('');                                            // the form forgets it
  await act(async () => { document.querySelector('[data-testid="cwb-reveal-x.com"]').click(); });
  expect(document.querySelector('[data-testid="cwb-cred-x.com"]').textContent).toContain('Sup3r!pw');
  expect(signed.at(-1)).toMatch(/^FEELESS reveal\nagent:g1\nsite:x\.com\nts:\d+$/); expect(calls.find(c => c.op === 'reveal')).toMatchObject({ sig: 'SIG', text: 'x.com' });   // 🔐 its own wallet signature
  await act(async () => { document.querySelector('[data-testid="cwb-reveal-x.com"]').click(); });
  expect(document.querySelector('[data-testid="cwb-cred-x.com"]').textContent).not.toContain('Sup3r!pw');
  await act(async () => root.unmount()); el.remove();
});

test('☁ the cloud drawer: connect YOUR Drive / Dropbox (FEELESS funds none); then your space left, its 5 newest, and ☁ Keep for a 24 h attachment', async () => {
  const { CloudDrawer } = await import('./CatWorkbench');
  const posts = []; let linked = false; const assign = jest.fn();
  delete window.location; window.location = { assign };
  global.fetch = async (u, o) => { if (o?.method === 'POST') { posts.push([String(u), JSON.parse(o.body)]); if (String(u).endsWith('/cloud/connect')) return { ok: true, json: async () => ({ url: 'https://accounts.google.com/x' }) }; return { ok: true, json: async () => ({ kept: { id: 'k' } }) }; }
    return { ok: true, json: async () => ({ providers: [{ key: 'gdrive', label: 'Google Drive', free: '15 GB free', ready: true }, { key: 'dropbox', label: 'Dropbox', free: '2 GB free', ready: false }],
      link: linked ? { provider: 'gdrive', label: 'Google Drive' } : null, used: 5 * 1024 ** 3, total: 15 * 1024 ** 3, recent: linked ? [{ id: 'r1', name: 'coin.png', size: 72, link: 'https://drive/x' }] : [] }) }; };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const att = { files: [{ id: 'a'.repeat(32), name: 'logo.png', mime: 'image/png', size: 1024 }] };
  await act(async () => { root.render(<CloudDrawer cat={{ id: 'g1' }} attachments={att} />); });
  expect(el.querySelector('[data-testid="cwb-cloud-pick"]').textContent).toContain('never sees that password');
  expect(el.querySelector('[data-testid="cwb-cloud-dropbox"]').disabled).toBe(true);
  await act(async () => { el.querySelector('[data-testid="cwb-cloud-gdrive"]').click(); });
  expect(posts[0][1]).toMatchObject({ provider: 'gdrive' }); expect(assign).toHaveBeenCalledWith('https://accounts.google.com/x');
  linked = true;
  await act(async () => { root.render(<CloudDrawer key="2" cat={{ id: 'g1' }} attachments={att} />); });
  expect(el.querySelector('[data-testid="cwb-cloud-left"]').textContent).toBe('10.0 GB left');
  expect(el.querySelectorAll('[data-testid="cwb-cloud-latest"] a').length).toBe(1);
  await act(async () => { el.querySelector(`[data-testid="cwb-keep-${'a'.repeat(32)}"]`).click(); });
  expect(posts.at(-1)[0]).toContain(`/files/${'a'.repeat(32)}/keep`);
  await act(async () => root.unmount()); el.remove();
});

test('⚡ Earn Mode: the switch, risk and $ save through the owner action; plays show $/day and open their Launch › Pools tab', async () => {
  const { EarnCard } = await import('./CatWorkbench');
  const posts = []; let earn = { on: false, risk: 'safe', budgetUsd: 25 };
  global.fetch = async (u, o) => { if (o?.method === 'POST') { const b = JSON.parse(o.body); posts.push(b); earn = { ...earn, ...b.earn }; return { ok: true, json: async () => ({}) }; }
    return { ok: true, json: async () => ({ earn, gapsOpen: 1, plays: [{ kind: 'vault', title: 'STAKE · JITOSOL', sub: 'staking', tier: 'safe', apy: 7, dayUsd: 0.0048, tab: 'vault', why: 'compounds' }] }) }; };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<EarnCard cat={{ id: 'g1' }} />); });
  expect(el.textContent).toContain('STAKE · JITOSOL'); expect(el.querySelector('[data-testid="cwb-earn-go-0"]').getAttribute('href')).toBe('/terminal/launch?mode=pools&tab=vault');
  await act(async () => { el.querySelector('[data-testid="cwb-earn-sw"]').click(); });
  expect(posts[0]).toMatchObject({ action: 'earn', earn: { on: true, risk: 'safe' } }); expect(el.querySelector('[data-testid="cwb-earn-sw"]').getAttribute('aria-checked')).toBe('true');
  await act(async () => { el.querySelector('[data-testid="cwb-earn-risky"]').click(); });
  expect(posts[1].earn).toMatchObject({ on: true, risk: 'risky' });
  await act(async () => root.unmount()); el.remove();
});

test('🎫 the Pass drawer: blocked until its recovery PIN; shows the mint fee, Solana\'s cost and the 10% royalty; a minted Pass shows its number', async () => {
  const { PassDrawer } = await import('./CatWorkbench');
  global.fetch = async () => ({ ok: true, json: async () => ({ ready: true, why: '', feeWallet: 'F', providerLamports: 3_810_000, feeLamports: 7_620_000, royaltyBps: 1000 }) });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<PassDrawer cat={{ id: 'g1' }} />); });
  expect(el.querySelector('[data-testid="cwb-pass-blocked"]').textContent).toContain('recovery PIN');
  await act(async () => { root.render(<PassDrawer cat={{ id: 'g1', recoveryConfirmedAt: 1 }} key="2" />); });
  expect(el.textContent).toContain('0.0076 SOL'); expect(el.textContent).toContain('10% → FEELESS'); expect(el.querySelector('[data-testid="cwb-pass-mint"]').disabled).toBe(false);
  await act(async () => { root.render(<PassDrawer cat={{ id: 'g1', pass: { number: 7, asset: 'A1' } }} key="3" />); });
  expect(el.textContent).toContain('AGENT PASS #0007');
  await act(async () => root.unmount()); el.remove();
});

test('🏦 the treasury drawer: fees waiting from its vaults, the split as three bars, a preset saves through the owner action', async () => {
  const { TreasuryDrawer } = await import('./CatWorkbench');
  const posts = [];
  global.fetch = async (u, o) => { if (o?.method === 'POST') { posts.push(JSON.parse(o.body)); return { ok: true, json: async () => ({}) }; }
    return { ok: true, json: async () => ({ mint: '', creator: 'AGENTwallet111', split: { holder: 50, credit: 30, buyback: 20 }, fees: { pump: 1_780_000_000, pumpSwap: 0, total: 1_780_000_000 }, plan: { holder: 890_000_000, credit: 534_000_000, buyback: 356_000_000 }, buybackMax: 50 }) }; };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<TreasuryDrawer cat={{ id: 'g1' }} />); });
  expect(el.querySelector('[data-testid="cwb-tre-total"]').textContent).toContain('1.7800 SOL'); expect(el.textContent).toContain('0.8900 SOL');
  await act(async () => { el.querySelector('[data-testid="cwb-tre-Holder first"]').click(); });
  expect(posts[0]).toMatchObject({ action: 'treasury', treasury: { split: { holder: 70, credit: 20, buyback: 10 } } });
  await act(async () => root.unmount()); el.remove();
});

test('⏸ a task nobody answered for 5 min is filed: ▶ resume drops it and asks it again, ✕ drops it', async () => {
  const calls = [];
  const DONE = { ...STATE, task: { ...STATE.task, status: 'parked', why: '⏸ parked: no answer in 5 min — filed', answer: null }, windows: STATE.windows.map(w => ({ ...w, status: 'done', human: null })),
    parked: [{ text: 'B: read my X feed', why: 'a sign-in', at: 1 }] };
  global.fetch = async (u, o) => { const b = JSON.parse(o.body); calls.push(b); return { ok: true, json: async () => DONE }; };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CatWorkbench cat={{ id: 'g1', brainsCfg: { kind: 'general', brains: ['qwen/qwen3-32b', 'x/opus'], credit: 9.2 } }} />); });
  expect(el.querySelector('[data-testid="cwb-parked"]').textContent).toContain('B: read my X feed');
  expect(el.querySelector('[data-testid="cwb-answer"]').textContent).toContain('filed');
  await act(async () => { el.querySelector('[data-testid="cwb-resume-0"]').click(); });
  expect(calls.slice(-2).map(c => c.op)).toEqual(['unpark', 'ask']); expect(calls.at(-1)).toMatchObject({ text: 'B: read my X feed' });
  await act(async () => { el.querySelector('[data-testid="cwb-unpark-0"]').click(); });
  expect(calls.at(-1)).toMatchObject({ op: 'unpark', i: 0 });
  await act(async () => { root.unmount(); });
});

test('⤢ signing in opens the live window BIG (save from inside it; ✕ / Esc shrink it back); a window handed to you has ⤢ Big', async () => {
  const { SignedSites } = require('./CatWorkbench');
  const calls = [];
  global.fetch = async (u, o) => { const b = JSON.parse(o.body); calls.push(b); return { ok: true, json: async () => (b.op === 'signin_open' ? { live: 'https://view/hand', site: 'x.com' } : b.op === 'signin_save' ? { signedIn: [{ site: 'x.com', at: 1, n: 9 }] } : { ...STATE, windows: [{ ...STATE.windows[0], status: 'human', hand: true, live: 'https://view/w0', human: { why: 'a bot check' } }] }) }; };
  const saved = [];
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<SignedSites cat={{ id: 'g1' }} onSaved={r => saved.push(r)} />); });
  const q = id => document.querySelector(`[data-testid="${id}"]`);
  await act(async () => { el.querySelector('.cwb-signed-add .m-seg button').click(); });
  await act(async () => { q('cwb-signed-open').click(); });
  expect(q('cwb-pop-frame').getAttribute('src')).toBe('https://view/hand'); expect(q('cwb-pop').parentElement).toBe(document.body);
  await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' })); }); expect(q('cwb-pop')).toBeNull(); expect(q('cwb-signed-frame')).not.toBeNull();
  await act(async () => { q('cwb-signed-big').click(); }); await act(async () => { q('cwb-pop-save').click(); });
  expect(calls.at(-1)).toMatchObject({ op: 'signin_save' }); expect(saved[0][0].site).toBe('x.com'); expect(q('cwb-pop')).toBeNull();
  act(() => root.unmount());
  const el2 = document.createElement('div'); document.body.appendChild(el2); const root2 = createRoot(el2);
  await act(async () => { root2.render(<CatWorkbench cat={{ id: 'g1', brainsCfg: { kind: 'general', brains: ['qwen/qwen3-32b', 'x/opus'], credit: 9.2 } }} />); });
  await act(async () => { q('cwb-big').click(); }); expect(q('cwb-pop-frame').getAttribute('src')).toBe('https://view/w0'); expect(q('cwb-pop').textContent).toContain('a bot check');
  act(() => root2.unmount());
});

test('🗄 a trader agent gets the same key drawers (Credentials with signed-in sites, API keys) over its log', async () => {
  sessionStorage.setItem('feeless:safe-place', '1');
  const { TraderCabinet } = require('./CatWorkbench');
  const calls = [];
  global.fetch = async (u, o) => { calls.push(JSON.parse(o.body)); return { ok: true, json: async () => ({ logins: [{ site: 'coingecko.com' }], signedIn: [{ site: 'x.com', at: 1, n: 12 }] }) }; };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<TraderCabinet cat={{ id: 't1', brainsCfg: { kind: 'trading' } }} items={[{ f: 'trades', text: 'BUY $BONK', at: 1 }]} />); });
  expect(calls[0]).toMatchObject({ op: 'state' });
  const creds = [...el.querySelectorAll('button')].find(b => b.textContent.includes('Credentials'));
  expect(creds.textContent).toContain('2'); expect([...el.querySelectorAll('button')].some(b => b.textContent.includes('API keys'))).toBe(true);
  await act(async () => { creds.click(); }); expect(el.querySelector('[data-testid="cwb-signed"]').textContent).toContain('x.com');
  act(() => root.unmount());
});

test('🔏 the sealed drawer asks "somewhere safe?" first, lists labels only, opens a note with a fresh signature for 15 s, seals a pasted phrase', async () => {
  const { TraderCabinet } = require('./CatWorkbench');
  sessionStorage.clear(); document.body.innerHTML = '';
  const calls = [];
  global.fetch = async (u, o) => { const b = JSON.parse(o.body); calls.push(b);
    return { ok: true, json: async () => (b.op === 'unseal' ? { kind: 'note', label: 'Proton recovery', text: 'apple banana cherry' } : b.op === 'seal' ? { secrets: [{ id: 's1', label: 'Proton recovery', kind: 'note', size: 19, at: 1 }, { id: 's2', label: 'GitHub codes', kind: 'note', size: 40, at: 2 }] }
      : { logins: [], signedIn: [], secrets: [{ id: 's1', label: 'Proton recovery', kind: 'note', size: 19, at: 1 }] }) }; };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<TraderCabinet cat={{ id: 't1' }} items={[]} />); });
  const q = id => document.querySelector(`[data-testid="${id}"]`);
  const creds = [...el.querySelectorAll('button')].find(b => b.textContent.includes('Credentials'));
  await act(async () => { creds.click(); }); expect(q('safe-gate').textContent).toContain('streaming'); expect(q('cwb-sealed')).toBeNull();
  await act(async () => { q('safe-no').click(); }); expect(q('safe-gate')).toBeNull(); expect(q('cwb-sealed')).toBeNull();
  await act(async () => { creds.click(); }); await act(async () => { q('safe-yes').click(); });
  expect(q('cwb-sealed').textContent).toContain('Proton recovery'); expect(q('cwb-sealed').textContent).not.toContain('apple');
  await act(async () => { q('cwb-secret-open-s1').click(); });
  expect(calls.at(-1)).toMatchObject({ op: 'unseal', text: 's1', sig: 'SIG' }); expect(signed.at(-1)).toContain('site:s1'); expect(q('cwb-secret-text').textContent).toBe('apple banana cherry');
  const f = q('cwb-seal-add'); f.querySelector('[name="l"]').value = 'GitHub codes'; f.querySelector('[name="n"]').value = 'codes 1 2 3';
  await act(async () => { f.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); });
  expect(calls.at(-1)).toMatchObject({ op: 'seal', job: 'GitHub codes', secret: 'codes 1 2 3' }); expect(q('cwb-sealed').textContent).toContain('GitHub codes');
  act(() => root.unmount());
  await act(async () => { createRoot(document.createElement('div')).render(<TraderCabinet cat={{ id: 't1' }} items={[]} />); });   // asked once per tab
});

test('🖥 the private desktop: the live window minimizes to the taskbar, the Vault opens like a folder after "somewhere safe?", a 15-min window says when it closed', async () => {
  const { AgentDesktop, chatParts } = require('./CatWorkbench');
  sessionStorage.clear(); document.body.innerHTML = '';
  expect(chatParts('🛟 Backup model, free (OpenRouter has no credit): gpt-6.1-terra · 4')).toEqual({ text: 'gpt-6.1-terra · 4', tags: ['free backup'] });
  expect(chatParts('💳 Paid $0.0020 from its wallet: Raydium').tags).toEqual(['paid from its wallet']);
  global.fetch = async () => ({ ok: true, json: async () => ({ logins: [{ site: 'proton.me', user: 'a' }], secrets: [{ id: 's1', label: 'Proton recovery', kind: 'note', size: 10, at: 1 }], signedIn: [] }) });
  const closed = []; const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<AgentDesktop cat={{ id: 'g1', name: 'Happy' }} live={{ live: 'https://view/x', site: 'proton.me', at: Date.now() }} onClose={() => closed.push(1)} onReopen={() => {}} />); });
  const q = id => document.querySelector(`[data-testid="${id}"]`);
  expect(q('dsk-win-live').textContent).toMatch(/closes in 1[45]:/); expect(q('cwb-pop-frame').getAttribute('src')).toBe('https://view/x');
  await act(async () => { q('dsk-min-live').click(); }); expect(q('dsk-win-live')).toBeNull(); expect(q('dsk-task-live')).not.toBeNull();
  await act(async () => { q('dsk-task-live').click(); }); expect(q('dsk-win-live')).not.toBeNull();
  await act(async () => { q('dsk-vault').click(); }); expect(q('safe-gate')).not.toBeNull(); expect(q('dsk-win-vault')).toBeNull();
  await act(async () => { q('safe-yes').click(); }); expect(q('dsk-win-vault').textContent).toContain('proton.me');
  await act(async () => { q('dsk-tab-sealed').click(); }); expect(q('cwb-sealed').textContent).toContain('Proton recovery'); expect(q('dsk-tab-sealed').textContent).toContain('1');
  await act(async () => { q('dsk-ico-pow').click(); }); expect(q('dsk-win-pow')).not.toBeNull();             // ⛏ its proofs folder
  await act(async () => { q('dsk-ico-honey').click(); }); expect(q('dsk-honey').textContent).toContain('SCORE'); expect(q('honey-tanks')).not.toBeNull(); await act(async () => { q('dsk-ico-pop').click(); }); expect(q('pop-desk')).not.toBeNull(); expect(q('pop-start')).not.toBeNull(); expect(q('ht-owed').textContent).toContain('OWED'); expect(q('dsk-task-honey')).not.toBeNull();   // 🍯 colony vitals + the ways in
  await act(async () => { q('cwb-pop-close').click(); }); expect(closed).toEqual([1]);
  act(() => root.unmount());
  const el2 = document.createElement('div'); document.body.appendChild(el2); const root2 = createRoot(el2);
  await act(async () => { root2.render(<AgentDesktop cat={{ id: 'g1' }} live={{ live: 'https://view/x', site: 'proton.me', at: Date.now() - 16 * 60000 }} onClose={() => {}} onReopen={() => closed.push('again')} />); });
  expect(q('dsk-gone').textContent).toContain('closed'); expect(q('cwb-pop-frame')).toBeNull();
  await act(async () => { q('dsk-reopen').click(); }); expect(closed).toContain('again');
  act(() => root2.unmount());
});

test('🔄 the chat flips into its file cabinet and back; earlier runs fold; a working agent shows the typing line; an empty chat offers starters', async () => {
  document.body.innerHTML = ''; sessionStorage.setItem('feeless:safe-place', '1');
  const chat = [{ by: 'you', text: 'old ask', at: 1 }, { by: 'cats', text: 'old answer', at: 2 }, { by: 'you', text: 'new ask', at: 3 }];
  global.fetch = async (u, o) => ({ ok: true, json: async () => ({ ...STATE, chat }) });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CatWorkbench cat={{ id: 'g1', name: 'Happy', brainsCfg: { kind: 'general', brains: ['qwen/qwen3-32b', 'x/opus'], credit: 9.2 } }} />); });
  const q = id => document.querySelector(`[data-testid="${id}"]`);
  expect(q('cwb-cockpit').textContent).toContain('new ask'); expect(q('cwb-cockpit').textContent).not.toContain('old answer');
  await act(async () => { q('cwb-earlier').click(); }); expect(q('cwb-cockpit').textContent).toContain('old answer');
  expect(q('cwb-typing').textContent).toContain('reading the YES ladder');   // the working window's own words
  await act(async () => { q('cwb-flip').click(); }); expect(el.querySelector('.cwb-flip').className).toContain('is-back'); expect(q('cwb-sheet').hasAttribute('inert')).toBe(false); expect(el.querySelector('.cwb-deck').hasAttribute('inert')).toBe(true);   // the whole desk face (vitals · chat · vitals) turns over
  await act(async () => { q('cwb-flip-back').click(); }); expect(el.querySelector('.cwb-flip').className).not.toContain('is-back');
  act(() => root.unmount());
  global.fetch = async () => ({ ok: true, json: async () => ({ ...STATE, chat: [], task: null, windows: [] }) });
  const el2 = document.createElement('div'); document.body.appendChild(el2); const root2 = createRoot(el2);
  await act(async () => { root2.render(<CatWorkbench cat={{ id: 'g1', name: 'Happy', brainsCfg: { kind: 'general', brains: ['m/a'], credit: 1 } }} />); });
  expect(q('cwb-empty').textContent).toContain('What should it do?');
  await act(async () => { q('cwb-empty').querySelector('.cwb-sugg button').click(); }); expect(q('cwb-input').value).toContain('pump.fun');
  act(() => root2.unmount());
});

test('🛟 the agent service not answering (a restart → 504) says so in words, and the desk never keeps a stale "Working"', async () => {
  document.body.innerHTML = ''; let up = true;
  global.fetch = async () => (up ? { ok: true, status: 200, json: async () => STATE } : { ok: false, status: 504, json: async () => { throw new Error('html'); } });
  jest.useFakeTimers();
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CatWorkbench cat={{ id: 'g1', name: 'Happy', brainsCfg: { kind: 'general', brains: ['qwen/qwen3-32b', 'x/opus'], credit: 9.2 } }} />); });
  const q = id => document.querySelector(`[data-testid="${id}"]`);
  expect(q('cwb-typing')).not.toBeNull();
  up = false; await act(async () => { jest.advanceTimersByTime(1600); }); await act(async () => { await Promise.resolve(); }); jest.useRealTimers();
  expect(document.body.textContent).toContain('not answering right now'); expect(document.body.textContent).not.toContain('HTTP 504'); expect(q('cwb-typing')).toBeNull();
  act(() => root.unmount());
});

test('🖱 the browser stays in view (the FEELESS chart is a tab), the mind not asked says so, and the AI cursor sits where it clicked in the style you pick', async () => {
  const S = { ...STATE, windows: [{ i: 0, model: 'm/a', goal: 'Browse pump.fun', status: 'working', provider: 'steel', live: 'https://view/w0', url: 'https://pump.fun/', coin: { pair: 'P1', mint: 'M', symbol: 'HUSS' }, cursor: { x: 0.25, y: 0.5, act: 'click', at: 7 }, steps: [] },
    { i: 1, model: 'm/b', goal: null, status: 'done', provider: 'reader', note: 'not asked this time', bubble: 'not asked — idle', steps: [] }] };
  global.fetch = async () => ({ ok: true, json: async () => S });
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<CatWorkbench cat={{ id: 'g1', brainsCfg: { kind: 'general', brains: ['m/a', 'm/b'], credit: 1 } }} />); });
  expect(el.querySelector('[data-testid="cwb-live"]')).not.toBeNull(); expect(el.querySelector('[data-testid="cwb-chart"]')).toBeNull();   // it checked a coin — its browser still shows
  expect(el.querySelector('[data-testid="cwb-tab-chart"]').textContent).toContain('$HUSS');
  const cur = el.querySelector('[data-testid="cwb-cursor"]'); expect(cur.style.transform).toBe('translate(25cqw, 50cqh)'); expect(cur.className).toContain('c-arrow');
  expect(el.querySelector('[data-testid="cwb-notasked"]').textContent).toContain('not asked');
  expect(el.querySelectorAll('[data-testid="cwb-input"]')).toHaveLength(1); expect(el.querySelector('.ckit-bar [data-testid="cwb-to-both"]')).not.toBeNull();   // ONE box, the A · B · Both pick in its bar
  await act(async () => { el.querySelector('[data-testid="cwb-gear"]').click(); });
  await act(async () => { el.querySelector('[data-testid="cwb-cur-paw"]').click(); });
  expect(el.querySelector('[data-testid="cwb-cursor"]').className).toContain('c-paw'); expect(localStorage.getItem('feeless:ai-cursor')).toBe('paw');
});

test('📥 a kept note drops from where its cursor was — only a NEW keep, never the ones already there', async () => {
  const { useDrop } = require('./CatWorkbench'); let seen = [];
  const P = ({ w }) => { const d = useDrop(w); seen.push(d.drop); trays.push(d.tray); return null; }; const trays = [];
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const w0 = { cursor: { x: 0.3, y: 0.4 }, steps: [{ action: 'note', thought: 'old', at: 1 }] };
  await act(async () => { root.render(<P w={w0} />); }); expect(seen.at(-1)).toBeNull();   // what was kept before you looked never drops
  await act(async () => { root.render(<P w={{ ...w0, steps: [...w0.steps, { action: 'open', at: 2 }] }} />); }); expect(seen.at(-1)).toBeNull();   // opening a page keeps nothing
  await act(async () => { root.render(<P w={{ ...w0, steps: [...w0.steps, { action: 'feeless', detail: 'coin HUSS', at: 3 }] }} />); });
  expect(seen.at(-1)).toMatchObject({ icon: '📈', label: 'coin HUSS', x: 0.3, y: 0.4 });
  await act(async () => { await new Promise(r => setTimeout(r, 1200)); });
  expect(seen.at(-1)).toBeNull(); expect(trays.at(-1).map(t => t.label)).toEqual(['coin HUSS']);   // then it sits in the tray at the bottom of its monitor
  act(() => root.unmount());
});

test('🗄 the cabinet shows 12, adds 12 at a time to 40, then sends you to its Desktop', async () => {
  const { AgentLog } = require('./CatCockpit');
  const items = Array.from({ length: 50 }, (_, i) => ({ f: 'cloud', text: `note ${i}`, at: 1 }));
  const el = document.createElement('div'); document.body.appendChild(el); const desk = jest.fn();
  await act(async () => { createRoot(el).render(<AgentLog items={items} onDesktop={desk} />); });
  expect(el.querySelectorAll('.ck-rows > li:not(.ck-more)')).toHaveLength(12);
  for (let k = 0; k < 3; k++) await act(async () => { el.querySelector('[data-testid="log-more"]').click(); });
  expect(el.querySelectorAll('.ck-rows > li:not(.ck-more)')).toHaveLength(40); expect(el.querySelector('[data-testid="log-more"]')).toBeNull();
  await act(async () => { el.querySelector('[data-testid="log-desktop"]').click(); }); expect(desk).toHaveBeenCalled();
});

test('💬 the command list: what it understands in the chat — a tap puts the command in the chat box', async () => {
  const picked = []; const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<CommandList rows={[['file a PoW', 'a new 4-coin folder'], ['stop PoW', 'ends it']]} onPick={t => picked.push(t)} />); });
  expect(el.querySelectorAll('[data-testid="dsk-cmds"] li')).toHaveLength(2); expect(el.textContent).toContain('a new 4-coin folder');
  await act(async () => { el.querySelector('[data-testid="cmd-0"]').click(); });
  expect(picked).toEqual(['file a PoW']); expect(el.textContent).toContain('in the chat ✓');
});

test('⛏ the PoW explorer: PoW › dated folders › coin folders (the pick = 👎 bad trade, its chart) › 📋 FINAL REPORT', async () => {
  const { AgentDesktop } = require('./CatWorkbench');
  sessionStorage.clear(); document.body.innerHTML = '';
  const fold = { id: 'pow9', name: 'PoW #9 · Nov 01 · 10:00 UTC', status: 'closed', phase: 'done', coins: [{ mint: 'M1', sym: 'AAA', src: 'pump' }, { mint: 'M2', sym: 'BBB', src: 'dex', safe: false }],
    pick: { mint: 'M1' }, sym: 'AAA', pnlPct: -4.2, entry: 1, tp: 20, sl: 10, sol: 0.006, line: [1, 1.02, 0.97, 0.958], shots: [{ mint: 'M1', site: 'rugcheck.xyz', n: 1, file: 'a.jpg', trade: 'bad' }], evidenceMetrics: { M1: { verified: 5, visits: 2, durationSec: 60, costUsd: 0.006, factsPerVisit: 2.5, factsPerUsd: 833.33, gaps: ['solscan.io'] } },
    vitals: { M1: [{ label: 'liquidity', value: '$35K', site: 'rugcheck.xyz', verified: true, contradiction: true, claims: [{ value: '$35K', site: 'rugcheck.xyz', support: 'Liquidity $35K', at: 100 }, { value: '$18K', site: 'solscan.io', support: 'Liquidity $18K', at: 120 }] }] },
    talk: [{ by: 'A', text: 'buy AAA', at: 1 }], report: { grade: '👎 bad trade', pnlPct: -4.2, researched: 1, coins: [{ mint: 'M1', sym: 'AAA', src: 'Pump', safe: true, vitals: 3, shots: 1, pick: true }], shadow: [{ mint: 'M2', sym: 'BBB', priceMovePct: 2.3 }], pick: 'AAA', sol: 0.006, held: 10, checks: 4, costUsd: 0.05, lesson: 'it lost: stop' } };
  const memoryOps = [];
  global.fetch = async (url, opts) => { if (opts?.body) memoryOps.push(JSON.parse(opts.body).op); return { ok: true, json: async () => ({ powFolders: [fold], rows: [], poi: { v: 1, memoryVersions: 1, versions: [{ generation: 1, at: 100, models: ['old'] }],
    minds: [{ mind: 0, generations: 4, verified: 9, uniqueRoutes: 3, states: { 'solscan.io': 'promoted' }, events: [{ generation: 4, site: 'solscan.io', state: 'promoted' }] },
      { mind: 1, generations: 0, verified: 0, uniqueRoutes: 0, states: {}, events: [] }] } }) }; };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<AgentDesktop cat={{ id: 'g1', name: 'Happy' }} onClose={() => {}} start="pow" />); });
  const q = id => document.querySelector(`[data-testid="${id}"]`);
  expect(q('dsk-pow').textContent).toContain('FOLDERS'); expect(q('dsk-x-pow9').textContent).toContain('PoW #9');
  expect(q('dsk-poi').textContent).toContain('solscan.io promoted'); expect(q('dsk-poi').querySelectorAll('.pf-print').length).toBe(2);   // one mind view, no second diagram
  await act(async () => { q('dsk-memory-1').click(); }); expect(q('dsk-memory-1').textContent).toContain('Tap again');
  await act(async () => { q('dsk-memory-1').click(); }); expect(memoryOps).toContain('memory_restore');
  await act(async () => { q('dsk-x-pow9').click(); }); expect(q('dsk-x-report')).not.toBeNull(); expect(q('dsk-x-coin-M1').querySelector('img').getAttribute('src')).toContain('thumb-down');
  expect(q('dsk-evidence-summary').textContent).toContain('5 verified facts');
  await act(async () => { q('dsk-x-poi').click(); }); expect(q('poi-folder')).not.toBeNull(); expect(q('pf-mind-0')).not.toBeNull();   // 🧬 exactly one PoI child folder
  await act(async () => { document.querySelector('.dsk-xpath .m-btn').click(); });
  expect(q('dsk-pow-replay').textContent).toContain('buy AAA');
  await act(async () => { q('dsk-x-coin-M1').click(); }); expect(q('dsk-pow').textContent).toContain('BAD TRADE'); expect(document.querySelector('.dsk-tl')).not.toBeNull();
  expect(q('dsk-evidence-meter').textContent).toContain('solscan.io'); expect(q('dsk-coin-M1').textContent).toContain('CONFLICT');
  expect(q('dsk-coin-M1').textContent).toContain('👎 rugcheck.xyz');
  await act(async () => { document.querySelector('.dsk-xpath .m-btn').click(); }); await act(async () => { q('dsk-x-report').click(); });
  expect(q('dsk-report').textContent).toContain('it lost: stop'); expect(q('dsk-rep-shadow').textContent).toContain('NO TRADE'); expect(q('dsk-rep-shadow').textContent).toContain('+2.3%'); expect(q('dsk-report').querySelector('a').getAttribute('href')).toContain('/powshot/pow9/report.md');
  act(() => root.unmount());
});

test('👛 the wallet app: live SOL + USDC, pick a direction, Swap sends op wallet_swap with that side and amount', async () => {
  const { AgentDesktop } = require('./CatWorkbench');
  sessionStorage.clear(); document.body.innerHTML = ''; const calls = [];
  global.fetch = async (u, o) => { const b = o?.body ? JSON.parse(o.body) : {}; calls.push(b);
    const w = b.op === 'wallet_swap' ? { address: 'AGT', sol: 0.0179, usdc: 0.35, gas: 0.01, canSwap: true, swap: { landed: true }, swaps: [{ at: Date.now() / 1000, side: 'USDC>SOL', amount: 1, landed: true }] }
      : { address: 'AGT', sol: 0.0075, usdc: 1.35, gas: 0.01, canSwap: true, swaps: [], modelReceipts: [{ id: 'paid1', at: Date.now() / 1000, provider: 'SingIt', model: 'test/model', usd: 0.003, tokens: 120, status: 'provider accepted' }] };
    return { ok: true, json: async () => w }; };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<AgentDesktop cat={{ id: 'g1', name: 'Happy' }} onClose={() => {}} start="wallet" />); });
  const q = id => document.querySelector(`[data-testid="${id}"]`);
  expect(q('dsk-wallet').textContent).toContain('1.35'); expect(q('dsk-wallet').textContent).toContain('0.0075');
  expect(q('dsk-model-receipts').textContent).toContain('$0.0030'); expect(q('dsk-model-receipts').textContent).toContain('120 tokens');
  const inp = q('dsk-wallet').querySelector('input'); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  await act(async () => { set.call(inp, '1'); inp.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { q('dsk-wallet-swap').click(); });
  expect(calls.at(-1)).toMatchObject({ op: 'wallet_swap', text: 'USDC>SOL', cap: 1 }); expect(q('dsk-wallet').textContent).toContain('✓ swapped');
  act(() => root.unmount());
});

test('🐝 its Colony tab: every PoW folder a connected dot (👍 up / 👎 down / ● live), the money pipe lit where money flows, Earn below', async () => {
  const { ColonyTab } = require('./CatWorkbench');
  document.body.innerHTML = '';
  global.fetch = async (u, o) => { const b = o?.body ? JSON.parse(o.body) : {};
    const j = b.op === 'wallet' ? { sol: 0.0179, usdc: 0.35 } : b.op === 'state' ? { powFolder: { id: 'f3', name: 'PoW #3', phase: 'watch' }, powFolders: [{ id: 'f2', name: 'PoW #2', pnlPct: -16, pnlSol: -0.001 }, { id: 'f1', name: 'PoW #1', pnlPct: 12, pnlSol: 0.0012, cost: 0.02 }] } : { earn: { on: false, risk: 'safe', budgetUsd: 25 }, plays: [] };
    return { ok: true, json: async () => j }; };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<ColonyTab cat={{ id: 'h1', colonyShare: { on: true, pct: 10 } }} />); });
  const q = s => document.querySelector(s);
  expect(document.querySelectorAll('.col-dot').length).toBe(3); expect(q('.col-dot.is-good')).not.toBeNull(); expect(q('.col-dot.is-bad')).not.toBeNull(); expect(q('.col-dot.is-live')).not.toBeNull();
  expect(q('[data-testid="col-tab"]').textContent).toContain('+0.0002 SOL'); expect(q('[data-testid="col-tab"]').textContent).toContain('10% of wins'); expect(q('[data-testid="col-tab"]').textContent).toContain('0.0179 SOL');
  await act(async () => { q('.col-dot.is-bad').dispatchEvent(new MouseEvent('click', { bubbles: true })); }); expect(q('[data-testid="col-pick"]').textContent).toContain('PoW #2');
  expect(q('[data-testid="cwb-earn"]')).not.toBeNull();
  act(() => root.unmount());
});

test('⛓ keep on IPFS: ⛓ IPFS asks the price (nothing paid), Pay pays that quote, the file then links to IPFS and lands in the kept list', async () => {
  const { CloudDrawer } = require('./CatWorkbench');
  document.body.innerHTML = ''; const posts = []; const id = 'b'.repeat(32);
  global.fetch = async (u, o) => { if (o?.method === 'POST' && String(u).includes('/ipfs')) { const b = JSON.parse(o.body); posts.push(b);
      return { ok: true, json: async () => (b.pay ? { stored: { file: id, name: 'logo.png', cid: 'bafyX', url: 'https://gw/ipfs/bafyX/logo.png', sol: 0.001326, days: 30, expires: '2026-12-02' } } : { quote: { cid: 'bafyX', sol: 0.001326, days: 30, why: null } }) }; }
    return { ok: true, json: async () => ({ providers: [], link: null }) }; };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CloudDrawer cat={{ id: 'g1' }} attachments={{ files: [{ id, name: 'logo.png', mime: 'image/png', size: 1024 }] }} />); });
  const q = s => el.querySelector(`[data-testid="${s}"]`);
  await act(async () => { q(`cwb-ipfs-quote-${id}`).click(); }); expect(posts[0]).toMatchObject({ pay: false }); expect(q(`cwb-ipfs-${id}`).textContent).toContain('0.001326 SOL');
  await act(async () => { q(`cwb-ipfs-pay-${id}`).click(); }); expect(posts[1]).toMatchObject({ pay: true });
  expect(el.querySelector('.cwb-ipfs-on').getAttribute('href')).toBe('https://gw/ipfs/bafyX/logo.png'); expect(q('cwb-ipfs-list').textContent).toContain('until 2026-12-02');
  act(() => root.unmount());
});

test('⛓ the IPFS picker is there with NO files: pick an image → it is added to its files and its IPFS price shows by itself', async () => {
  const { CloudDrawer } = require('./CatWorkbench');
  document.body.innerHTML = ''; const posts = []; const id = 'd'.repeat(32);
  global.FileReader = class { readAsDataURL() { this.result = 'data:image/png;base64,AA=='; setTimeout(() => this.onload(), 0); } };
  global.fetch = async (u, o) => { if (o?.method === 'POST') { posts.push([String(u), JSON.parse(o.body)]);
      return { ok: true, json: async () => (String(u).endsWith('/files') ? { file: { id, name: 'logo.png', mime: 'image/png', size: 2048 } } : { quote: { cid: 'bafyY', sol: 0.001326, days: 30, why: null } }) }; }
    return { ok: true, json: async () => ({ providers: [], link: null }) }; };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CloudDrawer cat={{ id: 'g1' }} attachments={{ files: [] }} />); });
  const inp = el.querySelector('[data-testid="cwb-ipfs-pick"]'); expect(el.querySelector('[data-testid="cwb-ipfs-add"]').textContent).toContain('KEEP ON IPFS');
  Object.defineProperty(inp, 'files', { value: [new File(['x'], 'logo.png', { type: 'image/png' })] });
  await act(async () => { inp.dispatchEvent(new Event('change', { bubbles: true })); await new Promise(r => setTimeout(r, 20)); });
  expect(posts.some(([url]) => url.endsWith('/files'))).toBe(true);
  expect(posts.find(([url]) => url.endsWith(`/files/${id}/ipfs`))?.[1]).toMatchObject({ pay: false });
  expect(el.querySelector(`[data-testid="cwb-ipfs-${id}"]`).textContent).toContain('0.001326 SOL');
  act(() => root.unmount());
});

test('🤝 the PoW folder shares wins with the pot WITHOUT colonizing: pick 20% → one wallet signature → op share; OFF needs no signature', async () => {
  const { AgentDesktop } = require('./CatWorkbench');
  sessionStorage.clear(); document.body.innerHTML = ''; const posts = []; const before = signed.length;
  global.fetch = async (u, o) => { const b = o?.body ? JSON.parse(o.body) : {}; if (b.op) posts.push(b);
    return { ok: true, json: async () => (b.op === 'share' ? { colonyShare: { on: !!b.on, auto: !!b.on, pct: b.cap || 20 } } : { powFolders: [], rows: [] }) }; };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<AgentDesktop cat={{ id: 'h1', name: 'Happy', colonyShare: { on: false, pct: 10 } }} onClose={() => {}} start="pow" />); });
  const q = id => document.querySelector(`[data-testid="${id}"]`);
  expect(q('dsk-share').textContent).toContain('stay in its wallet');
  await act(async () => { q('dsk-share-20').click(); });
  expect(signed.at(-1)).toMatch(/^FEELESS auto-collect\nSend this % of each winning proof of \+50% or more to the Pool\nagent:h1\npct:20\nts:\d+$/); expect(posts.filter(p => p.op === 'share').at(-1)).toMatchObject({ op: 'share', on: true, cap: 20, sig: 'SIG' });
  expect(q('dsk-share').textContent).toContain('20% of each PoW win');
  const n = signed.length; await act(async () => { q('dsk-share-0').click(); });
  expect(posts.filter(p => p.op === 'share').at(-1)).toMatchObject({ op: 'share', on: false }); expect(signed.length).toBe(n); expect(n).toBe(before + 1);
  act(() => root.unmount());
});

test('🗂 Jobs is a folder tree: Jobs › a request (👍/👎 tinted) › MIND A · MIND B · ANSWER', async () => {
  const { AgentDesktop } = require('./CatWorkbench');
  sessionStorage.clear(); document.body.innerHTML = '';
  const job = { id: 'j1', request: 'find the best SOL pool', at: Date.now() / 1000 - 60, cost: 0.004, status: 'done', answer: 'Meteora SOL/USDC, 38% APY',
    minds: [{ model: 'x/haiku', job: 'pools', plan: ['open pools'], steps: [{ a: 'open', t: 'Pool Hub', d: 'pools' }], answer: '38%' }, { model: 'x/glm', job: 'gaps', steps: [] }] };
  global.fetch = async () => ({ ok: true, json: async () => ({ jobs: [job], jobRates: { j1: 'up' } }) });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<AgentDesktop cat={{ id: 'g1', name: 'Happy' }} onClose={() => {}} start="jobs" />); });
  const q = id => document.querySelector(`[data-testid="${id}"]`);
  expect(q('dsk-job-j1').className).toContain('is-good'); await act(async () => { q('dsk-job-j1').click(); });
  expect(q('job-mind-0').textContent).toContain('MIND A'); expect(q('job-mind-1')).not.toBeNull(); expect(q('job-total')).not.toBeNull();
  expect(q('job-mind-0').textContent).toContain('Pool Hub');
  expect(q('job-tree').textContent).toContain('Meteora SOL/USDC'); expect(q('job-tree').textContent).toContain('YOU LIKED IT');
  act(() => root.unmount());
});

test('📌 keep / 🗑 delete a PoW folder or one coin folder from the desktop (delete asks twice)', async () => {
  const { AgentDesktop } = require('./CatWorkbench');
  sessionStorage.clear(); document.body.innerHTML = ''; const posts = [];
  const fold = { id: 'pow9', name: 'PoW #9 · Nov 01', status: 'closed', phase: 'done', coins: [{ mint: 'M1', sym: 'AAA', src: 'pump' }, { mint: 'M2', sym: 'BBB', src: 'dex' }], shots: [] };
  global.fetch = async (u, o) => { const b = o?.body ? JSON.parse(o.body) : {}; if (b.op === 'pow_folder') posts.push(b);
    const kept = { ...fold, kept: true }; const out = b.op === 'pow_folder' ? { powFolders: b.job === 'delete' ? [] : [b.job === 'delete_coin' ? { ...kept, hidden: ['M2'] } : kept] } : { powFolders: [fold], rows: [] };
    return { ok: true, json: async () => out }; };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<AgentDesktop cat={{ id: 'h1', name: 'Happy' }} onClose={() => {}} start="pow" />); });
  const q = id => document.querySelector(`[data-testid="${id}"]`);
  await act(async () => { q('dsk-x-pow9').click(); }); await act(async () => { q('dsk-fold-keep').click(); });
  expect(posts.at(-1)).toMatchObject({ op: 'pow_folder', job: 'keep', text: 'pow9', on: true }); expect(q('dsk-fold-keep').textContent).toContain('Kept');
  await act(async () => { q('dsk-x-coin-M2').click(); }); await act(async () => { q('dsk-coin-del').click(); });
  expect(posts).toHaveLength(1); await act(async () => { q('dsk-coin-del').click(); });                      // asks twice
  expect(posts.at(-1)).toMatchObject({ job: 'delete_coin', secret: 'M2' }); expect(q('dsk-x-coin-M2')).toBeNull();
  await act(async () => { q('dsk-fold-del').click(); }); await act(async () => { q('dsk-fold-del').click(); });
  expect(posts.at(-1)).toMatchObject({ job: 'delete', text: 'pow9' }); expect(q('dsk-x-pow9')).toBeNull();
  act(() => root.unmount());
});

describe('its window follows the real state of the round', () => {
  const base = { i: 0, slot: 0, model: 'x/a', provider: 'kernel', url: 'https://solscan.io/token/a', live: 'https://live.test/a', hand: null, goal: 'PROOF OF WORK on $A', coin: { pair: 'P', mint: 'M', symbol: 'A' }, steps: [{ action: 'feeless', thought: 'reads the coin on FEELESS first' }], bubble: 'opening solscan.io' };
  const folder = { name: 'PoW #1', phase: 'scout', base: 0, coins: [{ mint: 'M', sym: 'A', pair: 'P' }], rMint: 'M' };
  const paint = async (w, f) => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(<Window w={w} catId="c" tick={0} folder={f} />); }); return el; };
  test('research shows its browser, never the chart, right after the FEELESS pre-read', async () => {
    const el = await paint({ ...base, status: 'working' }, folder);
    expect(el.querySelector('[data-testid=cwb-live]')).toBeTruthy(); expect(el.querySelector('[data-testid=cwb-chart]')).toBeNull(); expect(el.querySelector('[data-testid=cwb-tab-web]').className).toContain('is-on');
  });
  test('a bot check shows the browser and the other sources get their own row', async () => {
    const el = await paint({ ...base, status: 'human', hand: 'https://live.test/hand', human: { kind: 'challenge', why: 'a bot check', alts: ['birdeye.so'] } }, { ...folder, phase: 'watch' });
    expect(el.querySelector('[data-testid=cwb-chart]')).toBeNull(); expect(el.querySelector('[data-testid=cwb-live]')).toBeTruthy(); expect(el.querySelector('[data-testid=cwb-alts]')).toBeTruthy();
  });
  test('a round that ended never shows a dead browser and stops claiming it works', async () => {
    const el = await paint({ ...base, status: 'working' }, { ...folder, coins: [{ mint: 'M', sym: 'A' }], phase: 'buy', sym: 'A', mint: 'M' });
    expect(el.querySelector('[data-testid=cwb-live]')).toBeNull(); expect(el.querySelector('[data-testid=cwb-powscr-0]')).toBeTruthy(); expect(el.textContent).toContain('BUYING'); expect(el.textContent).not.toContain('PROOF OF WORK on'); expect(el.querySelector('[data-testid=cwb-cursor]')).toBeNull();
  });
});
test('a new desktop icon never lands on a saved one, and a full column wraps', () => {
  const saved = Object.fromEntries(['vault', 'pow', 'jobs', 'sources', 'honey', 'wallet', 'files', 'cmds'].map((k, i) => [k, { x: 0, y: i * 96 }]));
  const at = placeIcons(saved, 800); const spots = Object.values(at).map(p => `${p.x},${p.y}`);
  expect(new Set(spots).size).toBe(spots.length); expect(at.pop.x).toBe(96); expect(at.vault).toEqual({ x: 0, y: 0 });
});

test('📉 PoP is folders like PoW: dated folder → report, market folder, discussion, keep; a ghost-free no-trade folder has no result', async () => {
  const j = { ok: true, popFolders: [] };
  const folders = [{ id: 'p2', n: 2, at: 1700000000, status: 'closed', side: 'short', market: 'BTC', lev: 2, tp: 3, sl: 1.5, entry: 100, roePct: -3.2, pnlUsd: -0.32, won: false, why: 'stop', line: [100, 101, 102], reads: [{ market: 'BTC', px: 100, chgPct: -0.6, high: 105, low: 95 }], calls: [{ mind: 0, name: 'mind-a', market: 'BTC', side: 'short', lev: 2, why: 'below the midpoint' }], report: { grade: 'BAD TRADE', lesson: 'short BTC closed at stop', roePct: -3.2, pnlUsd: -0.32, held: 15, minds: 1, costUsd: 0.008 }, talk: [{ at: 1, by: 'Engine', text: 'Closed at stop' }] }, { id: 'p1', n: 1, at: 1700000000, status: 'closed', noTrade: true, why: 'split', calls: [], talk: [] }];
  const f = global.fetch; const asked = [];
  global.fetch = jest.fn((u, o) => { if (o?.body) asked.push(JSON.parse(o.body)); return Promise.resolve({ ok: true, json: async () => (o?.body && JSON.parse(o.body).op === 'pop_folder' ? { ...j, popFolders: folders.map(x => ({ ...x, kept: true })) } : { popFolders: folders }) }); });
  const { AgentDesktop } = require('./CatWorkbench'); const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<AgentDesktop cat={{ id: 'c1', name: 'Happy' }} live={null} onClose={() => {}} start="pop" />); });
  const q = t => document.querySelector(`[data-testid="${t}"]`);
  expect(q('pop-desk')).not.toBeNull(); expect(q('pop-x-p2').textContent).toContain('PoP #2'); expect(q('pop-x-p1').textContent).toContain('no trade');
  await act(async () => { q('pop-x-p2').click(); }); expect(q('pop-x-report').textContent).toContain('BAD TRADE'); expect(q('pop-x-m-BTC').textContent).toContain('-0.60%');
  await act(async () => { q('pop-keep').click(); }); expect(asked.at(-1)).toMatchObject({ op: 'pop_folder', job: 'keep', text: 'p2', on: true }); expect(q('pop-keep').textContent).toContain('Kept');
  await act(async () => { q('pop-x-report').click(); }); expect(q('pop-report').textContent).toContain('short BTC closed at stop');
  await act(async () => { document.querySelector('[aria-label="Up one folder"]').click(); }); await act(async () => { q('pop-x-m-BTC').click(); }); expect(q('pop-market').textContent).toContain('below the midpoint');
  await act(async () => { root.unmount(); }); el.remove(); global.fetch = f;
});

test('🎲 PoB: files from the Bids desk, and a folder shows what each mind read in its own browser', async () => {
  const f = global.fetch; const sent = [];
  const pob = { id: 'b1', n: 1, status: 'closed', won: true, side: 'yes', q: 'SOL higher in 1h?', chips: 50, report: { grade: 'GOOD BID', lesson: 'It bid YES and the market said YES: +40 chips.' }, calls: [{ mind: 0, side: 'yes', why: 'up 4% on dexscreener' }], browsed: { 0: { sites: ['dexscreener.com'], note: 'SOL up 4%' } } };
  global.fetch = jest.fn((u, o) => { const b = o?.body ? JSON.parse(o.body) : {}; sent.push(b); return Promise.resolve({ ok: true, json: async () => (String(u).includes('rep-markets') ? { live: [], settled: [] } : { pobFolders: b.op === 'state' ? [pob] : [], ok: true, chat: [] }) }); });
  const { AgentDesktop } = require('./CatWorkbench'); const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<AgentDesktop cat={{ id: 'c1', name: 'Happy' }} live={null} onClose={() => {}} start="bids" />); });
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  const q = t2 => document.querySelector(`[data-testid="${t2}"]`);
  await act(async () => { q('pob-file').click(); }); expect(sent.some(b => b.op === 'pob')).toBe(true); expect(q('pob-reading')).not.toBeNull();
  await act(async () => { q('pob-b1').click(); });
  expect(q('pob-folder').textContent).toContain('GOOD BID'); expect(q('pop-browsed').textContent).toContain('dexscreener.com');
  await act(async () => { root.unmount(); }); el.remove(); global.fetch = f;
});

test('🎲 the Bids folder opens on a dash, and the USA sites are links that never overclaim', async () => {
  const f = global.fetch; global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: async () => ({ live: [{ id: 'm', kind: 'agent', q: 'Happy: long SOL PoP ends in profit?' }, { id: 'x', kind: 'double', q: 'not an agent' }], settled: [], bank: { chips: 777 } }) }));
  const { AgentDesktop } = require('./CatWorkbench'); const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<AgentDesktop cat={{ id: 'c1', name: 'Happy' }} live={null} onClose={() => {}} start="bids" />); });
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  const q = t => document.querySelector(`[data-testid="${t}"]`);
  expect(q('bd-stats').textContent).toContain('777'); expect(q('bd-live').textContent).toContain('1 open'); expect(q('dsk-bids').textContent).not.toContain('not an agent');
  await act(async () => { q('bd-sites').click(); });
  const links = [...q('bid-sites').querySelectorAll('a')]; expect(links.length).toBeGreaterThan(7); links.forEach(a => { expect(a.href).toMatch(/^https:\/\//); expect(a.rel).toContain('noopener'); expect(a.target).toBe('_blank'); });
  expect(q('bs-fanduel').textContent).toContain('PEOPLE ONLY'); expect(q('bs-kalshi').textContent).toContain('API OK'); expect(q('bid-sites').textContent).toContain('No site says an AI browser may click for you');
  await act(async () => { q('bs-lens-api').click(); }); expect(q('bs-fanduel')).toBeNull(); expect(q('bs-polymarket')).not.toBeNull();
  await act(async () => { root.unmount(); }); el.remove(); global.fetch = f;
});

test('a new icon never lands on one dragged off the grid', () => {
  const { placeIcons } = require('./CatWorkbench');
  const pos = placeIcons({ wallet: { x: 96, y: 92 } }, 800); const all = Object.entries(pos);
  all.forEach(([a, p]) => all.forEach(([b, q]) => { if (a !== b) expect(Math.abs(p.x - q.x) < 84 && Math.abs(p.y - q.y) < 84).toBe(false); }));
});

test('🧭 Browser window: tools box docks left or right, makes its email, shows its code, warns on a money site, saves the sign-in, writes the browse job', async () => {
  const { BrowserWin } = require('./CatWorkbench');
  const calls = []; const realFetch = global.fetch;
  global.fetch = jest.fn(async (_, o) => { const b = JSON.parse(o?.body || '{}'); calls.push(b.op); const j = b.op === 'mail_read' ? { mail: [{ id: 'm', code: '482911' }] } : b.op === 'mail_make' ? { mailbox: { address: 'a@b.co' } } : b.op === 'signin_open' ? { site: b.text, live: 'https://x.test' } : b.op === 'signin_save' ? { signedIn: [{ site: 'pump.fun', at: 1, n: 2 }] } : {}; return { ok: true, json: async () => j }; });
  const said = []; const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  function Box() { const [d, setD] = React.useState({ signedIn: [] }); const [s, setS] = React.useState({ open: true, x: 100, y: 10 }); return <BrowserWin cat={{ id: 'g1' }} d={d} setD={setD} onCommand={t => said.push(t)} s={s} top set={(_, p) => setS(x => ({ ...x, ...p }))} onTop={() => {}} onClose={() => {}} />; }
  await act(async () => { root.render(<Box />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`); const type = async (n, v) => { await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(n, v); n.dispatchEvent(new Event('input', { bubbles: true })); }); };
  expect(q('bwr-dock').className).toContain('is-right'); await act(async () => { q('bwr-dock-left').click(); }); expect(q('bwr-dock').className).toContain('is-left'); expect(q('dsk-win-browser').style.transform).toContain('316px');
  expect(q('bwr-code').textContent).toBe('Needs its email');
  await act(async () => { q('bwr-email-make').click(); }); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(q('bwr-email').textContent).toBe('a@b.co'); expect(q('bwr-code').textContent).toBe('482911');
  expect(q('bwr-money')).toBeNull(); await type(q('bwr-addr'), 'pump.fun'); expect(q('bwr-money')).toBeTruthy();
  await act(async () => { q('bwr-min-5').click(); }); await act(async () => { q('bwr-send').click(); }); expect(said).toEqual(['browse pump.fun for 5 minutes']);
  expect(q('bwr-save')).toBeNull(); await act(async () => { q('bwr-open').click(); }); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(q('cwb-signed-frame')).toBeTruthy(); expect(q('sd-type')).toBeTruthy(); await act(async () => { q('bwr-save').click(); }); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(q('bwr-saved').textContent).toContain('pump.fun'); expect(q('bwr-reopen-pump.fun')).toBeTruthy(); expect(calls).toEqual(expect.arrayContaining(['mail_make', 'mail_read', 'signin_open', 'signin_save']));
  await act(async () => root.unmount()); el.remove(); global.fetch = realFetch;
});

test('🔁 what wants one spot takes turns: one shows at a time and each stays until it is gone', async () => {
  jest.useFakeTimers();
  const { Turns } = require('./CatWorkbench');
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<Turns items={[<b key="bar">bar</b>, null, <b key="note">note</b>]} />); });
  const on = () => [...el.querySelectorAll('.cwb-turn.is-on')].map(n => n.textContent);
  expect(el.querySelectorAll('.cwb-turn').length).toBe(2); expect(on()).toEqual(['bar']);
  await act(async () => { jest.advanceTimersByTime(3600); }); expect(on()).toEqual(['note']);
  await act(async () => { jest.advanceTimersByTime(3600); }); expect(on()).toEqual(['bar']);
  await act(async () => { root.render(<Turns items={[<b key="bar">bar</b>]} />); }); expect(on()).toEqual(['bar']);
  await act(async () => root.unmount()); el.remove(); jest.useRealTimers();
});

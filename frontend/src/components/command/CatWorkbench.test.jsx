import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CatWorkbench } from './CatWorkbench';
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
  expect(calls[0]).toEqual({ ownerId: 'browser-1', session: '', op: 'state' });
  expect(el.querySelector('[data-testid="cwb-win-0"]').textContent).toContain('STEEL'); expect(el.querySelector('[data-testid="cwb-bubble"]').textContent).toContain('reading the YES ladder');
  expect(el.querySelector('[data-testid="cwb-human"]').textContent).toContain('a sign-in');
  expect(el.textContent).toContain('$0.0130 / $0.0500');
  await act(async () => { el.querySelector('[data-testid="cwb-continue"]').click(); });
  expect(calls.at(-1)).toMatchObject({ op: 'continue', i: 1 });
  expect(el.querySelector('[data-testid="cwb-answer"]').textContent).toContain('YES at $0.31');
  await act(async () => { el.querySelector('[data-testid="cwb-cap-0.25"]').click(); });
  expect(calls.at(-1)).toMatchObject({ op: 'cap', cap: 0.25 });
  const inp = el.querySelector('[data-testid="cwb-input"]');
  await act(async () => { const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set; set.call(inp, 'find best bids'); inp.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { el.querySelector('[data-testid="cwb-send"]').click(); });
  expect(calls.at(-1)).toMatchObject({ op: 'ask', text: 'find best bids', to: 'both' });
  await act(async () => { el.querySelector('[data-testid="cwb-to-1"]').click(); });
  await act(async () => { const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set; set.call(inp, 'only you'); inp.dispatchEvent(new Event('input', { bubbles: true })); });
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
  await act(async () => { const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set; set.call(inp, 'launch my coin on pump.fun with this logo'); inp.dispatchEvent(new Event('input', { bubbles: true })); });
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
  await act(async () => { q('cwb-flip').click(); }); expect(el.querySelector('.cwb-flip').className).toContain('is-back'); expect(q('cwb-sheet').hasAttribute('inert')).toBe(false); expect(q('cwb-cockpit').hasAttribute('inert')).toBe(true);
  await act(async () => { q('cwb-flip-back').click(); }); expect(el.querySelector('.cwb-flip').className).not.toContain('is-back');
  act(() => root.unmount());
  global.fetch = async () => ({ ok: true, json: async () => ({ ...STATE, chat: [], task: null, windows: [] }) });
  const el2 = document.createElement('div'); document.body.appendChild(el2); const root2 = createRoot(el2);
  await act(async () => { root2.render(<CatWorkbench cat={{ id: 'g1', name: 'Happy', brainsCfg: { kind: 'general', brains: ['m/a'], credit: 1 } }} />); });
  expect(q('cwb-empty').textContent).toContain('What should it do?');
  await act(async () => { q('cwb-empty').querySelector('.cwb-sugg button').click(); }); expect(q('cwb-input').value).toContain('pump.fun');
  act(() => root2.unmount());
});

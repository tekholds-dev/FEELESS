import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import ClipFarm, { boardRows, fileProblem, linkProblem, platformOf, SAVE_STEPS } from './ClipFarm';
import PocStudio from './PocStudio';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const $ = (el, id) => el.querySelector(`[data-testid="${id}"]`);
const FILES = ['video', 'image'].flatMap(pc => ['story', 'feed', 'wide'].map(fm => ({ piece: pc, format: fm, url: `/api/cats/media/c/m${pc}${fm}.${pc === 'video' ? 'mp4' : 'jpg'}` })))
  .concat(['story', 'feed', 'wide'].map(fm => ({ piece: 'post', format: fm, url: `/api/cats/poc/c/t${fm}.txt`, text: 'cap #x' })));
const CLIP = { id: 'poc1c0', n: 4, at: 10, cost: 0.0012, studio: { hook: 'She wanted to explore', files: FILES, links: { story: '/api/cats/vid/v1', feed: '/api/cats/vid/v2', wide: '/api/cats/vid/v3' }, goal: { type: 'reach', target: 3000, by: 'minds' }, maker: { usd: 0 }, slot: '',
  clip: { run: 'cr1', rank: 1, s: 7.4, e: 44.3, dur: 36.9, from: 'Astronaut talk', both: 8.5, minds: [{ mind: 0, score: 8, why: 'hook' }, { mind: 1, score: 9, why: 'payoff' }], track: { how: 'face' } } } };
const RUN = { id: 'cr1', name: 'Astronaut talk', converted: { from: 'mov', note: 'hevc → h264', url: '/api/cats/vid/v0' }, links: [{ id: 'v0', kind: 'upload', exp: Date.now() / 1000 + 9e5 }], secs: 300, w: 1920, h: 1080, status: 'done', firstClipS: 61, doneS: 104, cost: 0.0024, clips: ['poc1c0'],
  steps: [{ key: 'probe', label: 'Read the file', state: 'done', note: '5:00', secs: 0 }, { key: 'words', label: 'Transcript with word times', state: 'done', note: '907 words', secs: 23 }, { key: 'minds', label: 'Both minds pick blind', state: 'running', note: '' }],
  cands: [{ n: 1, s: 7.4, e: 44.3, first2: "I've wanted to explore", local: 5.2, minds: [{ mind: 0, score: 8, picked: true, why: 'hook' }, { mind: 1, score: 9, picked: true, why: 'payoff' }] },
    { n: 2, s: 58, e: 94, first2: 'and my sister', local: 4.4, minds: [{ mind: 0, score: 3, why: 'slow' }, { mind: 1, score: null, why: '' }] }],
  picks: [{ n: 1 }], minds: [{ mind: 0, model: 'openai/a', name: 'a' }, { mind: 1, model: 'google/b', name: 'b' }] };

test('pure: the limits are said before anything goes up, and YouTube / Twitch / Instagram links are never fetched', () => {
  expect(fileProblem({ name: 'a.mp4', size: 1e6 }, 120)).toBe('');
  expect(fileProblem({ name: 'a.avi', size: 1e6, type: 'video/x-msvideo' }, 120)).toBe(''); expect(fileProblem({ name: 'a.mkv', size: 1e6 }, 120)).toBe('');
  expect(fileProblem({ name: 'a.pdf', size: 1e6, type: 'application/pdf' }, 0)).toMatch(/MP4, MOV, WebM, MKV, AVI/);
  expect(platformOf('https://www.tiktok.com/@a/video/1')).toBe('TikTok'); expect(platformOf('https://bsky.app/x')).toBe(''); expect(SAVE_STEPS.Twitch.length).toBeGreaterThan(0);
  expect(fileProblem({ name: 'a.mov', size: 1e6 }, 364)).toMatch(/6:04 long\. Up to 5:00/);
  expect(fileProblem({ name: 'a.webm', size: 700e6 }, 60)).toMatch(/700 MB/);
  expect(linkProblem('https://www.youtube.com/watch?v=x')).toMatch(/YouTube doesn't allow downloading/);
  expect(linkProblem('https://clips.twitch.tv/x')).toMatch(/Twitch/); expect(linkProblem('https://www.instagram.com/reel/x')).toMatch(/Instagram/);
  expect(linkProblem('https://bsky.app/profile/a/post/b')).toBe(''); expect(linkProblem('http://x.mp4')).toMatch(/https/);
  expect(boardRows([{ id: 'x', studio: {} }, CLIP, { ...CLIP, id: 'b', at: 20 }]).map(f => f.id)).toEqual(['b', 'poc1c0']);
});

test('the run shows a progress line per step and every candidate with each mind’s blind score; the board saves a day', async () => {
  const calls = [];
  global.fetch = jest.fn(async (url, opt) => { calls.push([url, opt]); return { ok: true, json: async () => (String(url).includes('/slot') ? { pocFolders: [{ ...CLIP, studio: { ...CLIP.studio, slot: 'Wed' } }] } : { runs: [RUN], busy: false }) }; });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const onPocs = jest.fn(); const onOpen = jest.fn();
  await act(async () => root.render(<ClipFarm cat={{ id: 'c' }} wsId="w1" pocs={[CLIP]} onPocs={onPocs} onOpen={onOpen} />));
  expect(calls[0][0]).toContain('/api/cats/c/clipfarm?');
  expect($(el, 'cfm-step-words').textContent).toContain('907 words'); expect($(el, 'cfm-step-minds').className).toContain('is-running');
  const rows = el.querySelectorAll('[data-testid="cfm-moments"] tbody tr');
  expect(rows).toHaveLength(2); expect(rows[0].className).toContain('is-made'); expect(rows[0].textContent).toContain('8★9★'); expect(rows[1].textContent).toContain('3—');
  expect($(el, 'cst-vid-poc1c0').getAttribute('src')).toContain('mvideostory');   // Slice 29: the board is a grid of playable tiles
  expect($(el, 'cfm-link-poc1c0-story').querySelector('a').getAttribute('href')).toContain('/api/cats/vid/v1');
  expect($(el, 'cfm-uplink').querySelector('a').getAttribute('href')).toContain('/api/cats/vid/v0');
  await act(async () => $(el, 'cfm-uplink-del').click());
  expect(JSON.parse(calls.find(c => String(c[0]).includes('/unlink'))[1].body)).toMatchObject({ id: 'v0' });
  await act(async () => $(el, 'cst-fmt-feed').click()); expect($(el, 'cst-vid-poc1c0').getAttribute('src')).toContain('mvideofeed');
  await act(async () => $(el, 'cst-fmt-wide').click()); expect($(el, 'cst-vid-poc1c0').getAttribute('src')).toContain('mvideowide');
  const day = $(el, 'cfm-day-poc1c0'); const setSel = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set;
  await act(async () => { setSel.call(day, 'Wed'); day.dispatchEvent(new Event('change', { bubbles: true })); });
  const slot = calls.find(c => String(c[0]).includes('/slot'));
  expect(JSON.parse(slot[1].body)).toMatchObject({ job: 'poc1c0', day: 'Wed' }); expect(onPocs).toHaveBeenCalledWith([expect.objectContaining({ id: 'poc1c0' })]);
  await act(async () => $(el, 'cst-open-poc1c0').click()); expect(onOpen).toHaveBeenCalledWith(CLIP);
  act(() => root.unmount()); el.remove();
});

test('a link to YouTube is refused in the page, and nothing uploads without the rights tick', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ runs: [], busy: false }) }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => root.render(<ClipFarm cat={{ id: 'c' }} pocs={[]} />));
  const inp = $(el, 'cfm-link'); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  await act(async () => { set.call(inp, 'https://youtu.be/abc'); inp.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => $(el, 'cfm-link-go').click());
  expect($(el, 'cfm-redirect').textContent).toMatch(/YouTube doesn't allow downloading/); expect($(el, 'cfm-redirect').querySelectorAll('li').length).toBe(2);
  expect($(el, 'cfm-redirect-upload')).not.toBeNull();
  expect(global.fetch.mock.calls.some(c => String(c[0]).includes('/link'))).toBe(false);
  act(() => root.unmount()); el.remove();
});

test('a clip PoC in the studio says the upload it came from, both minds’ scores and its square feed, with no thread', async () => {
  const work = jest.fn(async () => ({ services: [] }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => root.render(<PocStudio cat={{ id: 'c' }} f={{ ...CLIP, studio: { ...CLIP.studio, slot: 'Fri' } }} work={work} />));
  expect($(el, 'pst-clip-from').textContent).toBe('Astronaut talk');
  expect(el.textContent).toContain('Mind A 8/10 · Mind B 9/10'); expect(el.textContent).toContain('planned Fri'); expect(el.textContent).toContain('9/9');
  expect($(el, 'pst-link-story').getAttribute('href')).toContain('/api/cats/vid/v1');
  expect(el.textContent).not.toContain('THREAD'); expect($(el, 'pst-clipview')).not.toBeNull(); expect(el.querySelectorAll('video')).toHaveLength(1);   // Slice 29: one player, not two giant ones
  act(() => root.unmount()); el.remove();
});

// ✂ Slice 24 (owner's screenshot: a run's notes one letter per line): hive.css, loaded on every agent desk, owned .cfm / .cfm-steps (a 5-column
// steps grid), so each step row shrank to a fifth and its note column to 0 px. Every class the clip farm renders must be styled ONLY by its
// own sheet (or the shared m-* presets), and its step rows keep a note column that never collapses below the label.
test('the clip farm keeps its own class names: no other sheet styles them, so a step note keeps its width', async () => {
  const fs = require('fs'); const path = require('path'); const dir = path.join(__dirname, '..', '..', 'styles');
  const sheets = fs.readdirSync(dir).filter(f => f.endsWith('.css')).map(f => [f, fs.readFileSync(path.join(dir, f), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '')]);
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ runs: [RUN], busy: false }) }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => root.render(<ClipFarm cat={{ id: 'c' }} wsId="w1" pocs={[CLIP]} />));
  const classes = [...new Set([...el.querySelectorAll('[class]')].flatMap(n => [...n.classList]))].filter(c => !/^(m-|is-|active$|lucide)/.test(c));
  expect(classes.length).toBeGreaterThan(10); expect(classes.every(c => /^(clf|cst|cse)/.test(c))).toBe(true);   // + Slice 29's studio (clipStudio.css)
  for (const c of classes) {
    const owners = sheets.filter(([, css]) => new RegExp(`\\.${c.replace(/[-]/g, '\\-')}(?![\\w-])`).test(css)).map(([f]) => f);
    expect([c, owners.filter(f => f !== (c.startsWith('clf') ? 'clipFarm.css' : 'clipStudio.css'))]).toEqual([c, []]);
  }
  const css = sheets.find(([f]) => f === 'clipFarm.css')[1];
  expect(css).toMatch(/\.clf-steps li \{ display: flex; flex-wrap: wrap;/);                       // a row that wraps, needing no measured width
  expect(css).toMatch(/\.clf-steps small \{ flex: 1 1 200px; min-width: 0;/);                       // under 200 px left, the note takes its own full line
  expect(el.querySelector('[data-testid="cfm-step-words"]').className).toBe('is-done');
  act(() => root.unmount()); el.remove();
});

import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { CharacterFolder, nameWait } from './CharacterFolder';
import { AgentPortrait } from './AgentPortrait';
import { ALL_CHARACTERS, headFrom, peopleFile, pickRecorderType, thumbOf, weightsFrom } from '../../lib/wireface';

jest.mock('../../lib/wireface', () => ({ ...jest.requireActual('../../lib/wireface'), load2d: jest.fn(), loadCreate: jest.fn() }));
const lib = require('../../lib/wireface');

let face;
async function mount(node) {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(node); });
  await act(async () => { await Promise.resolve(); });
  return { el, root };
}
const q = (el, id) => el.querySelector(`[data-testid="${id}"]`);

beforeEach(() => {
  face = { useCharacter: jest.fn().mockResolvedValue({}), express: jest.fn(), mood: jest.fn(), destroy: jest.fn(), listenTo: jest.fn(), view: { start: jest.fn(), stop: jest.fn(), setPointer: jest.fn() }, canvas: {} };
  lib.load2d.mockResolvedValue({ createFace2d: () => face, defineExpression: jest.fn(), loadCharacter: jest.fn().mockResolvedValue({ id: 'person' }) });
});

test('all 24 free characters are there, each with a picture, real people first', () => {
  expect(ALL_CHARACTERS).toHaveLength(24); expect(ALL_CHARACTERS[0][2]).toBe('Human');
  expect(thumbOf('sarah')).toContain('/assets/people/sarah-thumb.jpg'); expect(peopleFile('sarah')).toContain('sarah.wireface.json'); expect(peopleFile('sora')).toBeNull();
  expect(thumbOf('sora')).toContain('/wireface/assets/2d/characters/sora-thumb.jpg');
});

test('a camera reading drives the mirrored side of the character', () => {
  expect(weightsFrom([{ categoryName: 'eyeBlinkLeft', score: 0.9 }, { categoryName: 'jawOpen', score: 2 }, { categoryName: 'unknown', score: 1 }])).toEqual({ blinkR: 0.9, jaw: 1 });
  const lm = Array.from({ length: 478 }, () => ({ x: 0.5, y: 0.5 })); lm[234] = { x: 0.3, y: 0.5 }; lm[454] = { x: 0.7, y: 0.5 }; lm[10] = { x: 0.5, y: 0.2 }; lm[152] = { x: 0.5, y: 0.8 }; lm[1] = { x: 0.55, y: 0.5 };
  const h = headFrom(lm); expect(h.x).toBeCloseTo(-0.5); expect(h.y).toBeCloseTo(0); expect(headFrom([])).toBeNull();
});

test('the stream picks a format the browser has, and says so when there is none', () => {
  expect(pickRecorderType(t => t === 'video/webm;codecs=vp8,opus')).toBe('video/webm;codecs=vp8,opus');
  expect(pickRecorderType(() => false)).toBe('');
});

test('it wears its saved character and a pick saves through the owner door', async () => {
  const work = jest.fn().mockResolvedValue({ face: { id: 'rex' } });
  const { el, root } = await mount(<CharacterFolder cat={{ id: 'c', name: 'Mittens', mine: true, face: { id: 'kit' } }} work={work} />);
  expect(face.useCharacter).toHaveBeenCalledWith('kit');
  expect(el.querySelectorAll('.chr-tile').length).toBe(25);   // 24 + your picture
  await act(async () => { q(el, 'chr-rex').click(); });
  expect(face.useCharacter).toHaveBeenCalledWith('rex');
  expect(work).toHaveBeenCalledWith('c', { op: 'face', text: 'rex' });
  await act(async () => { q(el, 'chr-mood-happy').click(); });
  expect(face.express).toHaveBeenCalledWith('happy', 3);
  await act(async () => { root.unmount(); });
  expect(face.destroy).toHaveBeenCalled();
});

test('camera and mic stay off until asked, and a blocked camera says what to do', async () => {
  const getUserMedia = jest.fn().mockRejectedValue(Object.assign(new Error('no'), { name: 'NotAllowedError' }));
  Object.defineProperty(navigator, 'mediaDevices', { value: { getUserMedia }, configurable: true });
  const { el } = await mount(<CharacterFolder cat={{ id: 'c', mine: true }} work={jest.fn()} />);
  await act(async () => { q(el, 'chr-tab-me').click(); });
  expect(getUserMedia).not.toHaveBeenCalled();
  await act(async () => { q(el, 'chr-cam').click(); });
  expect(getUserMedia).toHaveBeenCalledTimes(1);
  expect(el.textContent).toMatch(/blocked the camera/);
  expect(q(el, 'chr-cam').getAttribute('aria-pressed')).toBe('false');
});

test('go live needs a sealed key, and a key is sent once and cleared', async () => {
  const work = jest.fn().mockResolvedValue({ liveKeys: { twitch: { label: 'Twitch', set: true, server: 'rtmps://live.twitch.tv/app' } } });
  const { el } = await mount(<CharacterFolder cat={{ id: 'c', mine: true, liveKeys: { twitch: { label: 'Twitch', set: false, server: 'rtmps://live.twitch.tv/app' } } }} work={work} />);
  await act(async () => { q(el, 'chr-tab-live').click(); });
  expect(q(el, 'chr-go-live').disabled).toBe(true);
  await act(async () => { q(el, 'chr-ch-twitch').querySelector('button').click(); });
  const key = el.querySelector('input[type=password]');
  await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(key, 'live_abc12345'); key.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { q(el, 'chr-save-twitch').click(); });
  expect(work).toHaveBeenCalledWith('c', { op: 'live_key', text: 'twitch', user: 'rtmps://live.twitch.tv/app', secret: 'live_abc12345' });
  expect(q(el, 'chr-go-live').disabled).toBe(false);
  expect(el.querySelector('input[type=password]')).toBeNull();
});

test('a name inside its 7 days cannot be edited, and a visitor gets no controls', async () => {
  expect(nameWait(90000)).toBe('1d 1h');
  const { el } = await mount(<CharacterFolder cat={{ id: 'c', name: 'A', mine: true, nameLeftS: 90000 }} work={jest.fn()} />);
  expect(q(el, 'chr-name').disabled).toBe(true);
  expect(el.textContent).toContain('In 1d 1h');
  const v = await mount(<CharacterFolder cat={{ id: 'c', name: 'A', mine: false }} work={jest.fn()} />);
  expect(q(v.el, 'chr-tab-live')).toBeNull(); expect(q(v.el, 'chr-add')).toBeNull(); expect(q(v.el, 'chr-name')).toBeNull();
});

test('a portrait is a still, and shows live; nothing picked keeps its fallback', async () => {
  const { el } = await mount(<AgentPortrait cat={{ id: 'c', name: 'A', face: { id: 'gus' }, live: { on: true, where: ['Twitch'] } }} />);
  expect(el.querySelector('img').src).toContain('gus-thumb'); expect(el.textContent).toContain('LIVE'); expect(el.querySelector('canvas')).toBeNull();
  const f = await mount(<AgentPortrait cat={{ id: 'c' }} fallback={<i data-testid="fb" />} />);
  expect(q(f.el, 'fb')).not.toBeNull();
});

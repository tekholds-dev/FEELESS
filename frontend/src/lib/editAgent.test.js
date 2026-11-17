import { captionTexts, DEAD_AIR, diffEdit, dropSpans, hookFor, quietSpans, SAFE, SWAP_HERE } from './editAgent';

let n = 0; const uid = p => `${p}new${(n += 1)}`;
const P = (clips, texts = [], aspect = '9:16') => ({ aspect, sources: [], clips, texts, music: [] });

test('🤫 quiet spans: a 1 s silence between two loud parts is found, a 0.3 s gap is not', () => {
  const rate = 1000; const loud = k => Array.from({ length: k }, (_, i) => (i % 2 ? 0.5 : -0.5)); const hush = k => new Array(k).fill(0);
  const s = Float32Array.from([...loud(1000), ...hush(1000), ...loud(500), ...hush(300), ...loud(500)]);
  const spans = quietSpans(s, rate);
  expect(spans).toHaveLength(1); expect(spans[0][0]).toBeCloseTo(1.12, 2); expect(spans[0][1]).toBeCloseTo(1.88, 2);
});

test('✂ dropping spans keeps the rest of the clip, in order, and the first piece keeps the id', () => {
  const c = { id: 'c1', src: 's', in: 1, out: 10, speed: 1 };
  const out = dropSpans(c, [[3, 4], [8, 8.1], [0, 1.05]], uid);
  expect(out.map(x => [x.in, x.out])).toEqual([[1.05, 3], [4, 8], [8.1, 10]]); expect(out[0].id).toBe('c1'); expect(new Set(out.map(x => x.id)).size).toBe(3);
  expect(dropSpans(c, [], uid)).toEqual([c]);
});

test('💬 caption lines land under their clip, moved by its trim and speed; lines it cut are gone', () => {
  const c = { id: 'c', src: 's', in: 2, out: 8, speed: 2 };
  const rows = captionTexts([{ at: 0.5, dur: 1, text: 'gone' }, { at: 3, dur: 1, text: 'this is bishop' }, { at: 7.5, dur: 2, text: 'end' }], c, 10, '9:16');
  expect(rows.map(r => [r.at, r.dur, r.text])).toEqual([[10.5, 0.5, 'THIS IS BISHOP'], [12.75, 0.25, 'END']]); expect(rows[0].cap).toBe(true);
});

test('📐 safe zones per shape, and the hook sits inside them', () => {
  ['9:16', '16:9', '1:1'].forEach(a => { const h = hookFor(a); SAFE[a].forEach(z => expect(h.y < z.y || h.y > z.y + z.h).toBe(true)); });
});

test('🧾 the agent edit in words: cut, trimmed, added words, new length', () => {
  const a = P([{ id: 'c1', src: 's1', in: 0, out: 10 }, { id: 'c2', src: 's2', in: 0, out: 4 }]);
  const b = P([{ id: 'c1', src: 's1', in: 0, out: 6 }], [{ id: 't', at: 0, dur: 2, text: 'WAIT FOR IT' }]);
  const rows = diffEdit(a, b, { s1: 'street.mp4', s2: 'intro.mp4' });
  expect(rows).toEqual(['Trimmed street.mp4: 10.0 s → 6.0 s', 'Cut intro.mp4 (4.0 s)', 'Words “WAIT FOR IT” at 0.0 s', 'Length 14.0 s → 6.0 s']);
  expect(diffEdit(a, a)).toEqual([]);
});

test('🗣 which asks run here: dead air on the device; a swap goes to the PoC folder', () => {
  expect(DEAD_AIR.test('cut dead air')).toBe(true); expect(DEAD_AIR.test('remove the pauses')).toBe(true); expect(DEAD_AIR.test('make it a 30 s short')).toBe(false);
  expect(SWAP_HERE.test('swap the guy for my character')).toBe(true); expect(SWAP_HERE.test('add a hook')).toBe(false);
});

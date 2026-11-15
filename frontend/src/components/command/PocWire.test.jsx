import { startBoard, FRAMES, DAYS } from './PocWire';

jest.mock('@excalidraw/excalidraw', () => ({ Excalidraw: () => null, MainMenu: Object.assign(() => null, { DefaultItems: {} }), convertToExcalidrawElements: x => x, exportToBlob: async () => new Blob(), restoreElements: x => x }));
jest.mock('@excalidraw/excalidraw/index.css', () => ({}), { virtual: true });

test('the board opens with the picture fitted in every frame and a Mon–Sun week below', () => {
  const b = startBoard('f1', 1000, 500, 'Sneaker');
  const frames = b.filter(e => e.type === 'frame');
  expect(frames).toHaveLength(FRAMES.length + DAYS.length);
  const imgs = b.filter(e => e.type === 'image');
  expect(imgs).toHaveLength(3);
  FRAMES.forEach(([k, , fw, fh]) => { const f = b.find(e => e.id === `frame-${k}`); const i = b.find(e => e.id === `img-${k}`);
    expect(f.children).toEqual([`screen-${k}`, `img-${k}`]); expect(b.find(e => e.id === `screen-${k}`)).toMatchObject({ width: fw, height: fh }); expect(i.width).toBeLessThanOrEqual(fw); expect(i.height).toBeLessThanOrEqual(fh); expect(i.width / i.height).toBeCloseTo(2, 1); });
  expect(frames.find(f => f.id === 'day-Sun').name).toContain('week of content');
  expect(startBoard(null).filter(e => e.type === 'image')).toHaveLength(0);
});

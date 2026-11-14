import { applyMask, maskKept, toInput, toMask, CUTOUT_MODEL } from './cutout';

test('the mask becomes the alpha and soft edges stay soft', () => {
  const px = new Uint8ClampedArray([10, 20, 30, 255, 1, 2, 3, 255, 9, 9, 9, 128]);
  applyMask(px, new Uint8Array([255, 0, 128]));
  expect([px[3], px[7], px[11]]).toEqual([255, 0, 64]);
  expect([px[0], px[1], px[2]]).toEqual([10, 20, 30]);          // colours never change
  expect(() => applyMask(px, new Uint8Array([1]))).toThrow(/does not match/);
});

test('an empty or full mask means no subject was found', () => {
  expect(maskKept(new Uint8Array([0, 0, 0, 255]))).toBe(0.25);
  expect(maskKept(new Uint8Array([]))).toBe(0);
});

test('only an Apache-2.0 model, pinned to one revision (RMBG is non-commercial)', () => {
  expect(CUTOUT_MODEL).toMatch(/BritishWerewolf\/U-2-Netp\/resolve\/[0-9a-f]{40}\/onnx\/model\.onnx$/);
});

test('input is channels-first and normalised; the mask is stretched to 0–255', () => {
  const px = new Uint8ClampedArray([255, 0, 0, 255, 0, 255, 0, 255, 0, 0, 255, 255, 0, 0, 0, 255]);
  const f = toInput(px, 2);
  expect(f.length).toBe(12);
  expect(f[0]).toBeCloseTo((1 - 0.485) / 0.229);       // R of pixel 0
  expect(f[4 + 1]).toBeCloseTo((1 - 0.456) / 0.224);   // G of pixel 1
  expect([...toMask(new Float32Array([0.2, 0.6, 1.0]))]).toEqual([0, 128, 255]);
});

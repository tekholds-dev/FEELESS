// 🎭 Wireface 2D (free under its own licence: public/wireface/LICENSE.md), served from our own site and loaded only when a character window opens, so no other page pays for it.
const BASE = `${process.env.PUBLIC_URL || ''}/wireface`;
export const CHARACTERS = [['ava', 'Ava', 'Photo'], ['pip', 'Pip', '3D'], ['sora', 'Sora', 'Anime'], ['mabel', 'Mabel', 'Cartoon'], ['rex', 'Rex', 'Comic'], ['eleanor', 'Eleanor', 'Painting'], ['hazel', 'Hazel', 'Watercolour'],
  ['theo', 'Theo', 'Sketch'], ['kit', 'Kit', 'Pixel'], ['gus', 'Gus', 'Clay'], ['vee', 'Vee', 'Vector'], ['fern', 'Fern', 'Creature'], ['bolt', 'Bolt', 'Robot']];
// Real people first: the SDK's own stock portraits, rigged once and kept in public/wireface/assets/people.
export const PEOPLE = [['sarah', 'Sarah', 'Human'], ['marcus', 'Marcus', 'Human'], ['amara', 'Amara', 'Human'], ['walter', 'Walter', 'Human'], ['lucia', 'Lucia', 'Human'], ['arjun', 'Arjun', 'Human'], ['omar', 'Omar', 'Human'], ['ruth', 'Ruth', 'Human'], ['robot', 'Unit', 'Robot'], ['monster', 'Monster', 'Creature'], ['dracula', 'Dracula', 'Creature']];
export const ALL_CHARACTERS = [...PEOPLE, ...CHARACTERS];
const PEOPLE_IDS = new Set(PEOPLE.map(p => p[0]));
export const STYLES = ['All', ...new Set(ALL_CHARACTERS.map(c => c[2]))];
export const peopleFile = id => (PEOPLE_IDS.has(id) ? `${BASE}/assets/people/${id}.wireface.json` : null);
export const thumbOf = (id, catId) => (id === 'custom' ? `/api/cats/${catId}/face/thumb` : PEOPLE_IDS.has(id) ? `${BASE}/assets/people/${id}-thumb.jpg` : `${BASE}/assets/2d/characters/${id}-thumb.jpg`);
export const load2d = () => import(/* webpackIgnore: true */ `${BASE}/dist/2d.js`);
export const loadCreate = () => import(/* webpackIgnore: true */ `${BASE}/dist/create.js`);
const MEDIAPIPE = { bundle: `${BASE}/assets/mediapipe/vision_bundle.mjs`, wasm: `${BASE}/assets/mediapipe/wasm`, model: `${BASE}/assets/mediapipe/face_landmarker.task` };
export const mediapipePaths = () => ({ ...MEDIAPIPE });

// What a camera's reading turns into on the character. The camera is a mirror, so its left is the character's right. Pure.
const MAP = { eyeBlinkLeft: 'blinkR', eyeBlinkRight: 'blinkL', mouthSmileLeft: 'smileR', mouthSmileRight: 'smileL', jawOpen: 'jaw', browInnerUp: 'browInner', browOuterUpLeft: 'browUpR', browOuterUpRight: 'browUpL',
  browDownLeft: 'browDown', eyeWideLeft: 'eyeWideR', eyeWideRight: 'eyeWideL', mouthPucker: 'round', cheekPuff: 'cheekPuff', mouthFrownLeft: 'frown' };
export function weightsFrom(shapes) {
  const out = {};
  (shapes || []).forEach(s => { const k = MAP[s.categoryName]; if (k) out[k] = Math.round(Math.min(1, Math.max(0, s.score)) * 100) / 100; });
  return out;
}
// Where the head points, -1 to 1 on each side, from the nose against the cheeks and the brow against the chin. Pure.
export function headFrom(lm) {
  if (!lm || lm.length < 455) return null;
  const [nose, l, r, top, chin] = [lm[1], lm[234], lm[454], lm[10], lm[152]];
  const clamp = v => Math.max(-1, Math.min(1, v));
  return { x: clamp(-((nose.x - (l.x + r.x) / 2) / Math.max(0.01, Math.abs(r.x - l.x))) * 4), y: clamp(((nose.y - (top.y + chin.y) / 2) / Math.max(0.01, Math.abs(chin.y - top.y))) * 4) };
}

// 📷 The face tracker. Runs on the owner's device; a camera frame never leaves their browser. `source` is a playing <video>.
export async function startTracker(source, face, sdk, onFrame) {
  const { FaceLandmarker, FilesetResolver } = await import(/* webpackIgnore: true */ MEDIAPIPE.bundle);
  const vision = await FilesetResolver.forVisionTasks(MEDIAPIPE.wasm);
  const lm = await FaceLandmarker.createFromOptions(vision, { baseOptions: { modelAssetPath: MEDIAPIPE.model }, runningMode: 'VIDEO', numFaces: 1, outputFaceBlendshapes: true });
  let raf = 0; let last = 0; let on = true; let worn = false;
  const tick = now => {
    if (!on) return;
    raf = requestAnimationFrame(tick);
    if (now - last < 50 || (source.readyState !== undefined && source.readyState < 2)) return;   // 20 reads a second is plenty for a face
    last = now;
    const got = lm.detectForVideo(source, now);
    const shapes = got.faceBlendshapes?.[0]?.categories; const head = headFrom(got.faceLandmarks?.[0]);
    if (shapes) { sdk.defineExpression('feeless-live', weightsFrom(shapes)); if (!worn) { face.mood('feeless-live', 1); worn = true; } }
    if (head) { const r = face.canvas.getBoundingClientRect(); face.view.setPointer(r.width * (0.5 + head.x * 0.5), r.height * (0.5 + head.y * 0.5)); }
    onFrame?.(!!shapes);
  };
  raf = requestAnimationFrame(tick);
  return () => { on = false; cancelAnimationFrame(raf); face.mood(null); face.view.setPointer(null); lm.close(); };
}

// 🔴 What the stream sends: the character's canvas and a voice, never the camera. A channel needs sound, so no mic means quiet sound.
export function pickRecorderType(can = t => window.MediaRecorder?.isTypeSupported?.(t)) {
  return ['video/webm;codecs=h264,opus', 'video/webm;codecs=vp8,opus', 'video/webm', 'video/mp4'].find(t => can(t)) || '';
}
export function streamTracks(canvas, micStream, audioContext) {
  const video = canvas.captureStream(30).getVideoTracks();
  if (micStream) return { tracks: [...video, ...micStream.getAudioTracks()], stop: () => {} };
  const dest = audioContext.createMediaStreamDestination(); const gain = audioContext.createGain(); gain.gain.value = 0;
  const osc = audioContext.createOscillator(); osc.connect(gain); gain.connect(dest); osc.start();
  return { tracks: [...video, ...dest.stream.getAudioTracks()], stop: () => osc.stop() };
}

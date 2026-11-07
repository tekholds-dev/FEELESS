// 🎞 Renders an edit list to an MP4 in the browser with Mediabunny (WebCodecs). Nothing is uploaded. Video frames come from each clip, are drawn with fades and text at the same places the preview shows them, and audio is mixed in an offline audio graph.
export const SIZES = { '16:9': [1920, 1080], '9:16': [1080, 1920], '1:1': [1080, 1080] };
export const clipLen = c => (c.out - c.in) / (c.speed || 1);
export const totalLen = p => p.clips.reduce((n, c) => n + clipLen(c), 0);
export function clipAt(p, t) { let at = 0; for (const c of p.clips) { const l = clipLen(c); if (t < at + l) return { clip: c, start: at, src: c.in + (t - at) * (c.speed || 1) }; at += l; } return null; }
export function drawText(ctx, t, W, H) { const size = t.size * H; ctx.font = `800 ${size}px Sora, Arial, sans-serif`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.lineJoin = 'round'; ctx.lineWidth = size * 0.14; ctx.strokeStyle = '#000000'; ctx.fillStyle = t.color; const words = t.text.split(' '); const lines = []; let line = ''; words.forEach(w => { const next = line ? `${line} ${w}` : w; if (ctx.measureText(next).width > W * 0.9 && line) { lines.push(line); line = w; } else line = next; }); lines.push(line); lines.forEach((l, i) => { const y = t.y * H + (i - (lines.length - 1) / 2) * size * 1.12; ctx.strokeText(l, W / 2, y); ctx.fillText(l, W / 2, y); }); }

export async function probe(blob) {
  const { Input, ALL_FORMATS, BlobSource, CanvasSink } = await import('mediabunny');
  const input = new Input({ formats: ALL_FORMATS, source: new BlobSource(blob) });
  const video = await input.getPrimaryVideoTrack(); const audio = await input.getPrimaryAudioTrack(); const dur = await input.computeDuration(); let thumb = '';
  if (video && await video.canDecode()) { const sink = new CanvasSink(video, { width: 160, fit: 'contain' }); const f = await sink.getCanvas(Math.min(0.2, dur / 2)); if (f) { const c = document.createElement('canvas'); c.width = f.canvas.width; c.height = f.canvas.height; c.getContext('2d').drawImage(f.canvas, 0, 0); thumb = c.toDataURL('image/jpeg', 0.6); } }
  return { dur, hasVideo: !!video, hasAudio: !!audio, w: video?.displayWidth || 0, h: video?.displayHeight || 0, thumb };
}

export async function render(project, getBlob, onProgress, fps = 30) {
  const M = await import('mediabunny'); const [W, H] = SIZES[project.aspect] || SIZES['16:9']; const total = totalLen(project);
  if (!total) throw new Error('Add a clip first.');
  const codec = await M.getFirstEncodableVideoCodec(['avc', 'vp9', 'av1'], { width: W, height: H });
  if (!codec) throw new Error('This browser cannot make video. Try Chrome, Edge or Safari on a computer.');
  const canvas = document.createElement('canvas'); canvas.width = W; canvas.height = H; const ctx = canvas.getContext('2d', { alpha: false });
  const output = new M.Output({ format: new M.Mp4OutputFormat({ fastStart: 'in-memory' }), target: new M.BufferTarget() }); const videoOut = new M.CanvasSource(canvas, { codec, bitrate: M.QUALITY_HIGH }); output.addVideoTrack(videoOut, { frameRate: fps });
  const sources = new Map(project.sources.map(s => [s.id, s])); const wantsAudio = project.music.length > 0 || project.clips.some(c => !c.mute && sources.get(c.src)?.audio); const audioCodec = wantsAudio ? await M.getFirstEncodableAudioCodec(['aac', 'opus']) : null; const audioOut = audioCodec ? new M.AudioBufferSource({ codec: audioCodec, bitrate: M.QUALITY_HIGH }) : null; if (audioOut) output.addAudioTrack(audioOut);
  await output.start();
  let frame = 0; const frames = Math.max(1, Math.ceil(total * fps)); let at = 0;
  for (const clip of project.clips) {
    const blob = await getBlob(clip.src); if (!blob) throw new Error(`Add ${sources.get(clip.src)?.name || 'that clip'} again: it is not on this device.`);
    const input = new M.Input({ formats: M.ALL_FORMATS, source: new M.BlobSource(blob) }); const track = await input.getPrimaryVideoTrack();
    if (!track || !(await track.canDecode())) throw new Error(`${sources.get(clip.src)?.name || 'A clip'} cannot be read in this browser.`);
    const sink = new M.CanvasSink(track, { poolSize: 2 }); const len = clipLen(clip); const count = Math.max(1, Math.round(len * fps)); const times = Array.from({ length: count }, (_, i) => clip.in + (i / fps) * (clip.speed || 1));
    let i = 0;
    for await (const got of sink.canvasesAtTimestamps(times)) {
      const t = at + i / fps; ctx.globalAlpha = 1; ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
      if (got) { const c = got.canvas; const k = Math.max(W / c.width, H / c.height); const dw = c.width * k; const dh = c.height * k; const local = i / fps; ctx.globalAlpha = clip.fade ? Math.min(1, local / clip.fade, (len - local) / clip.fade) : 1; ctx.globalAlpha = Math.max(0, ctx.globalAlpha); ctx.drawImage(c, (W - dw) / 2, (H - dh) / 2, dw, dh); ctx.globalAlpha = 1; }
      project.texts.filter(x => t >= x.at && t < x.at + x.dur).forEach(x => drawText(ctx, x, W, H));
      await videoOut.add(t, 1 / fps); frame += 1; i += 1; if (frame % 15 === 0) onProgress?.(0.85 * frame / frames);
    }
    at += count / fps;
  }
  if (audioOut) {
    onProgress?.(0.88); const rate = 48000; const off = new OfflineAudioContext(2, Math.ceil(at * rate), rate); const cache = new Map();
    const decode = async id => { if (!cache.has(id)) { const b = await getBlob(id); cache.set(id, b ? await off.decodeAudioData(await b.arrayBuffer()).catch(() => null) : null); } return cache.get(id); };
    let t = 0;
    for (const clip of project.clips) { const len = clipLen(clip); if (!clip.mute && sources.get(clip.src)?.audio) { const buf = await decode(clip.src); if (buf) { const s = off.createBufferSource(); s.buffer = buf; s.playbackRate.value = clip.speed || 1; const g = off.createGain(); if (clip.fade) { g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(1, t + clip.fade); g.gain.setValueAtTime(1, Math.max(t + clip.fade, t + len - clip.fade)); g.gain.linearRampToValueAtTime(0, t + len); } s.connect(g).connect(off.destination); s.start(t, clip.in, clip.out - clip.in); } } t += len; }
    for (const m of project.music) { const buf = await decode(m.src); if (buf) { const s = off.createBufferSource(); s.buffer = buf; const g = off.createGain(); g.gain.value = m.vol; s.connect(g).connect(off.destination); s.start(m.at, m.in, Math.max(0, m.out - m.in)); } }
    await audioOut.add(await off.startRendering());
  }
  onProgress?.(0.97); await output.finalize(); onProgress?.(1);
  return new Blob([output.target.buffer], { type: 'video/mp4' });
}

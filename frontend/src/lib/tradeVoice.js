// 🔊 TRADE CHAT VOICES (owner, 2026-10-18: "text to speech in the AI trade chat, 4 witty voices — a gangster, a mob voice, you pick 2").
// The browser's own speech engine (window.speechSynthesis) reads the line — nothing is sent anywhere. Each voice = a pitch / rate, the
// system voices it prefers (macOS / Chrome names, first one installed wins) and a line it wraps the words in.
export const VOICES = [
  { key: 'gangster', label: '🧢 Gangster', pitch: 0.75, rate: 1.05, prefer: ['Fred', 'Ralph', 'Google US English', 'Alex'],
    open: ['Ayo,', 'Listen up,', 'Real talk,'], close: ['feel me?', "that's on the block.", 'no cap.'] },
  { key: 'mob', label: '🎩 Mob boss', pitch: 0.55, rate: 0.85, prefer: ['Grandpa', 'Daniel', 'Ralph', 'Google UK English Male'],
    open: ['Hey, capisce,', 'Between us,', 'The family says,'], close: ['fuggedaboutit.', "that's business.", 'you understand me?'] },
  { key: 'announcer', label: '🎙 Fight announcer', pitch: 1.1, rate: 1.2, prefer: ['Eddy', 'Reed', 'Google US English', 'Samantha'],
    open: ['Ladies and degens,', 'In this corner,', "Let's get ready —"], close: ['and the crowd goes wild!', "what a play!", 'ding ding ding!'] },
  { key: 'gremlin', label: '👾 Trench gremlin', pitch: 1.8, rate: 1.3, prefer: ['Zarvox', 'Bad News', 'Junior', 'Google US English'],
    open: ['Hehe,', 'Ooh shiny,', 'Gremlin report:'], close: ['send it!', 'wagmi, maybe.', 'snack time.'] },
];

export const voiceOf = key => VOICES.find(v => v.key === key) || VOICES[0];

// pure: the words a voice says for one chat line — emoji, links, $ signs and long numbers made speakable
export function speakText(line, key, seed = 0) {
  const v = voiceOf(key);
  const clean = String(line || '')
    .replace(/https?:\/\/\S+/g, '')
    .replace(/[\u{1F000}-\u{1FFFF}\u{2600}-\u{27BF}\u{FE0F}]/gu, '')
    .replace(/\$([A-Za-z])/g, '$1')
    .replace(/(\d)%/g, '$1 percent')
    .replace(/\s+/g, ' ').trim();
  if (!clean) return '';
  const n = Math.abs(Math.round(seed)) || 0;
  return `${v.open[n % v.open.length]} ${clean} ${v.close[n % v.close.length]}`;
}

export function pickSystemVoice(key, list) {
  const v = voiceOf(key); const all = list || [];
  for (const name of v.prefer) { const hit = all.find(x => String(x.name || '').startsWith(name)); if (hit) return hit; }
  return all.find(x => /^en/i.test(x.lang || '')) || null;
}

export function canSpeak() { return typeof window !== 'undefined' && !!window.speechSynthesis && typeof window.SpeechSynthesisUtterance === 'function'; }

export function say(line, key, seed) {
  if (!canSpeak()) return false;
  const text = speakText(line, key, seed); if (!text) return false;
  const v = voiceOf(key); const u = new window.SpeechSynthesisUtterance(text);
  u.pitch = v.pitch; u.rate = v.rate;
  const sys = pickSystemVoice(key, window.speechSynthesis.getVoices());
  if (sys) u.voice = sys;
  window.speechSynthesis.speak(u);
  return true;
}

export function hush() { if (canSpeak()) window.speechSynthesis.cancel(); }

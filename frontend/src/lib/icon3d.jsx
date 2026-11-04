import React from 'react';

// 🧊 One icon set, sitewide (owner 2026-11-04): 3dicons.co V1 (CC0) and its social set, compressed and served from our own origin (public/icons3d, ~1.6 KB each, lazy).
// A symbol with no match stays as it is, so nothing goes blank. Never fetch an icon from another site.
const MAP = {
  '📁': 'folder', '📂': 'folder', '🗂': 'folder-fav', '🗃': 'folder-new', '📄': 'file', '📃': 'file-text', '📋': 'file-text', '📑': 'file-text', '🧾': 'file-text', '📝': 'notebook', '📓': 'notebook', '📖': 'notebook', '📚': 'notebook', '📰': 'notebook', '📜': 'notebook',
  '⛏': 'axe', '🪓': 'axe', '📉': 'chart', '📈': 'chart', '📊': 'chart', '🎲': 'chess', '♟': 'chess', '🌐': 'explorer', '🌍': 'explorer', '🛰': 'explorer', '🧭': 'explorer', '🗺': 'map-pin', '📍': 'map-pin', '📌': 'pin',
  '🍯': 'bucket', '🏺': 'can', '🐝': 'sphere', '🧬': 'lab', '🧪': 'lab', '🔬': 'lab', '👛': 'wallet', '💼': 'bag', '👜': 'bag', '🛍': 'bag', '☁': 'folder-new', '⌘': 'hash', '#️⃣': 'hash',
  '🎟': 'credit-card', '🎫': 'credit-card', '💳': 'credit-card', '🎚': 'toggle', '🎛': 'toggle', '🧠': 'bulb', '💡': 'bulb', '🎭': 'magic-trick', '🪄': 'magic-trick', '✨': 'magic-trick', '🔮': 'sphere',
  '🔐': 'lock', '🔒': 'lock', '🔏': 'lock', '🔓': 'locker', '🗝': 'key', '🔑': 'key', '🛡': 'shield', '🚀': 'rocket', '🔥': 'fire', '🏆': 'trophy', '🥇': 'medal', '🏅': 'medal', '🎖': 'medal', '👑': 'crown', '⚡': 'flash',
  '💰': 'money-bag', '💸': 'money', '💵': 'dollar', '💲': 'dollar', '🪙': '3d-coin', '🏦': 'money-bag', '🎁': 'gift', '🪂': 'gift', '📣': 'megaphone', '📢': 'megaphone', '🔔': 'bell', '🔕': 'bell', '⭐': 'star', '🌟': 'star', '❤': 'heart', '💚': 'heart', '🎯': 'target',
  '⚙': 'setting', '🛠': 'tools', '🔧': 'tools', '🔨': 'tools', '🧰': 'tools', '🔎': 'zoom', '🔍': 'zoom', '💬': 'chat-bubble', '🗨': 'chat', '🎨': 'color-palette', '🖌': 'brush', '🖼': 'picture', '📷': 'camera', '📸': 'camera', '🎥': 'video-cam', '📺': 'video-cam', '🎬': 'video-cam',
  '🎵': 'music', '🎶': 'music', '🎧': 'headphone', '🎤': 'mic', '🕒': 'clock', '⏱': 'clock', '⏰': 'clock', '⏳': 'clock', '📅': 'calender', '🗓': 'calender', '✉': 'mail', '📧': 'mail', '📨': 'mail', '📬': 'mail', '🗑': 'trash-can',
  '📍️': 'map-pin', '👍': 'thumb-up', '👎': 'thumb-down', '✅': 'tick', '✔': 'tick', '🌙': 'moon', '☀': 'sun', '🌤': 'sun', '🔗': 'link', '🚩': 'flag', '🏁': 'flag', '🧩': 'puzzle', '📱': 'mobile', '💻': 'computer', '🖥': 'computer', '🧮': 'calculator', '✍': 'pencil', '✏': 'pencil', '📦': 'cube', '🧊': 'cube', '🔋': 'battery', '📶': 'wifi', '✂': 'scissor', '🔖': 'bookmark', '☂': 'umbrella', '🏋': 'gym',
};
const SOCIAL = { x: 'x', twitter: 'twitter', telegram: 'message', discord: 'discord', reddit: 'reddit', youtube: 'youtube', tiktok: 'tiktok', instagram: 'instagram', facebook: 'facebook', linkedin: 'linkedin', whatsapp: 'whatsapp', snapchat: 'snapchat', google: 'google', threads: 'threads', bluesky: 'bluesky' };
const clean = e => String(e || '').replace(/️/g, '');
const LEAD = /^\s*(\p{Extended_Pictographic}️?(?:‍\p{Extended_Pictographic}️?)*)\s*/u;

export const ic3Name = e => MAP[clean(e)] || MAP[e] || null;
export const ic3Src = name => `/icons3d/${name}.webp`;

export function Ic3({ e, name, social, size = '1.25em', className = '' }) {
  const n = social ? SOCIAL[social] && `social/${SOCIAL[social]}` : name || ic3Name(e);
  if (!n) return e ? <span className={className}>{e}</span> : null;
  return <img className={`ic3 ${className}`.trim()} src={ic3Src(n)} alt="" aria-hidden="true" width="160" height="160" loading="lazy" decoding="async" draggable="false" style={{ width: size, height: size }} />;
}

// A label that starts with a symbol, from data ("⛏ PoW"): the icon, then its words.
export function Ic3Text({ text, size }) {
  const t = String(text ?? ''); const m = t.match(LEAD);
  if (!m || !ic3Name(m[1])) return t;
  return <><Ic3 e={m[1]} size={size} /> {t.slice(m[0].length)}</>;
}

import '../styles/deskShell.css';
import React, { useSyncExternalStore } from 'react';
import { CircleDot, Atom, Bot, Bug, Building2, Cat, Droplets, Gem, HeartPulse, RadioTower, ScanSearch, Signpost, SprayCan, Stethoscope, TrafficCone, UserRound, Users, Waves, Archive, Banknote, Battery, Bell, Bookmark, Box, Briefcase, Brush, Calculator, Calendar, Camera, ChartCandlestick, Check, Clock, Coins, CreditCard, Crown, Dices, DollarSign, Dumbbell, File, FileText, Flag, Flame, FlaskConical, Folder, FolderOpen, FolderPlus, Gift, Globe, HandCoins, Hash, Headphones, Heart, Image, KeyRound, Lightbulb, Link, Lock, LockOpen, Mail, MapPin, Medal, Megaphone, MessageCircle, MessageSquare, Mic, Monitor, Moon, Music, NotebookPen, Orbit, PaintBucket, Palette, Pencil, Pickaxe, Pin, Puzzle, Rocket, Scissors, Search, Settings, Shield, SlidersHorizontal, Smartphone, Sparkles, Star, Sun, Target, ThumbsDown, ThumbsUp, Trash2, Trophy, Umbrella, Video, Wallet, Wifi, Wrench, Zap } from 'lucide-react';

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

// 🎩 the ELITE edition's line icons (lucide-react, ISC): one per 3D icon, same meaning
const LINE = { '3d-coin': Coins, 'axe': Pickaxe, 'bag': Briefcase, 'battery': Battery, 'bell': Bell, 'bookmark': Bookmark, 'brush': Brush, 'bucket': PaintBucket, 'bulb': Lightbulb, 'calculator': Calculator, 'calender': Calendar, 'camera': Camera, 'can': Archive, 'chart': ChartCandlestick, 'chat': MessageSquare, 'chat-bubble': MessageCircle, 'chess': Dices, 'clock': Clock, 'color-palette': Palette, 'computer': Monitor, 'credit-card': CreditCard, 'crown': Crown, 'cube': Box, 'dollar': DollarSign, 'explorer': Globe, 'file': File, 'file-text': FileText, 'fire': Flame, 'flag': Flag, 'flash': Zap, 'folder': Folder, 'folder-fav': FolderOpen, 'folder-new': FolderPlus, 'gift': Gift, 'gym': Dumbbell, 'hash': Hash, 'headphone': Headphones, 'heart': Heart, 'key': KeyRound, 'lab': FlaskConical, 'link': Link, 'lock': Lock, 'locker': LockOpen, 'magic-trick': Sparkles, 'mail': Mail, 'map-pin': MapPin, 'medal': Medal, 'megaphone': Megaphone, 'mic': Mic, 'mobile': Smartphone, 'money': Banknote, 'money-bag': HandCoins, 'moon': Moon, 'music': Music, 'notebook': NotebookPen, 'pencil': Pencil, 'picture': Image, 'pin': Pin, 'puzzle': Puzzle, 'rocket': Rocket, 'scissor': Scissors, 'setting': Settings, 'shield': Shield, 'sphere': Orbit, 'star': Star, 'sun': Sun, 'target': Target, 'thumb-down': ThumbsDown, 'thumb-up': ThumbsUp, 'tick': Check, 'toggle': SlidersHorizontal, 'tools': Wrench, 'trash-can': Trash2, 'trophy': Trophy, 'umbrella': Umbrella, 'video-cam': Video, 'wallet': Wallet, 'wifi': Wifi, 'zoom': Search };
const EMO_LINE = { '⚛': Atom, '💎': Gem, '🌊': Waves, '🏙': Building2, '🐱': Cat, '🚦': TrafficCone, '💓': HeartPulse, '🪧': Signpost, '👥': Users, '🐞': Bug, '🩺': Stethoscope, '📡': RadioTower, '🕵': ScanSearch, '🎩': Crown, '🤖': Bot, '🧹': SprayCan, '👤': UserRound, '💧': Droplets };   // site emoji with no 3D icon → their line icon (elite only)
const sub = cb => { window.addEventListener('feeless:edition', cb); return () => window.removeEventListener('feeless:edition', cb); };
const isElite = () => typeof document !== 'undefined' && document.documentElement.dataset.edition === 'elite';
export const useElite = () => useSyncExternalStore(sub, isElite, () => false);

export const ic3Name = e => MAP[clean(e)] || MAP[e] || null;
export const ic3Src = name => `/icons3d/${name}.webp`;

export function Ic3({ e, name, social, size = '1.25em', className = '' }) {
  const n = social ? SOCIAL[social] && `social/${SOCIAL[social]}` : name || ic3Name(e);
  const elite = useElite();
  const Emo = !n && elite && e ? EMO_LINE[clean(e)] : null;
  if (Emo) return <><Emo className={`ic3 ic3-line ${className}`.trim()} aria-hidden="true" strokeWidth={1.75} style={{ width: size, height: size }} /><span hidden style={{ display: 'none' }}>{e}</span></>;
  if (!n && elite && e && /\p{Extended_Pictographic}/u.test(e)) return <><CircleDot className={`ic3 ic3-line ${className}`.trim()} aria-hidden="true" strokeWidth={1.75} style={{ width: size, height: size }} /><span hidden style={{ display: 'none' }}>{e}</span></>;   // 🎩 elite: an unmapped emoji becomes a quiet mark, never a cartoon
  if (!n) return e ? <span className={className}>{e}</span> : null;
  const Line = elite && !social ? LINE[n] : null;   // 🎩 elite edition: the line icon in the accent colour, the symbol kept for copy and search
  if (Line) return <><Line className={`ic3 ic3-line ${className}`.trim()} aria-hidden="true" strokeWidth={1.75} style={{ width: size, height: size }} />{e ? <span hidden style={{ display: 'none' }}>{e}</span> : null}</>;
  // The symbol stays in the page's text, unseen: copy, search and anything reading the words still get it.
  return <><img className={`ic3 ${className}`.trim()} src={ic3Src(n)} alt="" aria-hidden="true" width="160" height="160" loading="lazy" decoding="async" draggable="false" style={{ width: size, height: size }} />{e ? <span hidden style={{ display: 'none' }}>{e}</span> : null}</>;
}

// A label that starts with a symbol, from data ("⛏ PoW"): the icon, then its words.
export function Ic3Text({ text, size }) {
  const t = String(text ?? ''); const m = t.match(LEAD);
  if (!m || !ic3Name(m[1])) return t;
  return <><Ic3 e={m[1]} size={size} /> {t.slice(m[0].length)}</>;
}

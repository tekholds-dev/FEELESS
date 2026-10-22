// 📱 HQ opened from the phone (components/HqLink.jsx): the session the phone's wallet signed, kept like a normal sign-in. No QR code here,
// so the HQ launcher can read it without loading the QR page for every visitor.
export const SESSION_KEY = 'feeless:cc-session';
export const PAIRED_KEY = 'feeless:hq-paired';

// a computer HQ paired from the phone (no wallet here): the address the session belongs to, while it is fresh
export function pairedAddress() {
  try {
    const s = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null');
    return s && localStorage.getItem(PAIRED_KEY) === s.address && Date.now() / 1000 - s.ts < 86000 ? s.address : null;
  } catch { return null; }
}

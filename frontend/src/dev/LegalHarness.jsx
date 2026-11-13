import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { WalletContext } from '../hooks/useWallet';
import { LegalConsent, MyDataCard } from '../components/LegalConsent';
import { LegalRegions } from '../components/command/LegalRegions';

// 🧪 DEV ONLY (`/dev/legal`, never in a production build): LEGAL-1 slice 2 on fixtures with a fake connected wallet (nothing is signed,
// nothing reaches the server — the legal endpoints answer from here). ?view=accept (default) · data · hq · day (HQ in the day theme).
const W = 'DEVdevDEVdevDEVdevDEVdevDEVdevDEVdev1234';
const now = Date.now() / 1000;
const CFG = { version: '2026-11-13', minAge: 18, everywhere: ['CU', 'IR', 'KP', 'SY'], requireAccept: true,
  features: { site: { blocked: [], ageGate: true }, swap: { blocked: [], ageGate: true }, perps: { blocked: ['GB', 'US'], ageGate: true }, agents: { blocked: [], ageGate: true }, launch: { blocked: ['GB'], ageGate: true }, games: { blocked: [], ageGate: true }, brokers: { blocked: [], ageGate: true } } };
const FEATURES = { site: 'The whole site', swap: 'Swaps (Jupiter route, user-signed)', perps: 'Perps + leverage (Jupiter Perps / Lend)', agents: 'Agents that trade on their own (auto wallets)', launch: 'Launching coins', games: 'Points, raffles, prizes and games', brokers: 'Broker links (stocks via SnapTrade)' };
let cfg = CFG;
const VIEW = () => ({ version: '2026-11-13', cfg, features: FEATURES, sanctioned: ['CU', 'IR', 'KP', 'SY'], accepted: 41, stale: 6,
  byCountry: [['US', 14], ['DE', 7], ['BR', 6], ['GB', 5], ['NG', 4], ['PH', 3], ['FR', 2]],
  requests: [{ wallet: '9xQpAAAAbbbbccccHe11o', kind: 'delete', at: now - 600, counts: { profile: 1, chat: 12, follows: 3, sessions: 2 } }, { wallet: '7kLmAAAAbbbbccccZz99', kind: 'export', at: now - 7200, counts: { profile: 1, chat: 40, receipts: 9 } }] });

const real = window.fetch.bind(window);
window.fetch = async (url, opts = {}) => {
  const u = String(url);
  const json = b => new Response(JSON.stringify(b), { status: 200, headers: { 'Content-Type': 'application/json' } });
  if (u.includes('/legal/status')) return json({ version: '2026-11-13', accepted: false, country: 'DE', stated: null, minAge: 18, sanctioned: CFG.everywhere, features: FEATURES, gates: {} });
  if (u.includes('/chat/session')) return json({ valid: true, token: 'dev', expiresAt: now + 7 * 86400 });
  if (u.includes('/legal/accept')) return json({ ok: true });
  if (u.includes('/legal/export')) return json({ wallet: W, data: { profile: { name: 'dev' }, chat: [], receipts: [] } });
  if (u.includes('/legal/delete')) return json({ ok: true, removed: { profile: 1, follows: 3, notifications: 8, push: 1, dmPrefs: 0, identities: 0, dms: 2, chat: 12, sessions: 2 } });
  return real(url, opts);
};
try { localStorage.setItem(`feeless:chat-session:${W}`, JSON.stringify({ token: 'dev', expiresAt: now + 7 * 86400 })); } catch { /* ignore */ }
const call = async (path, opts) => { if (opts?.method === 'POST') cfg = JSON.parse(opts.body).cfg; return VIEW(); };

export default function LegalHarness() {
  const v = new URLSearchParams(window.location.search).get('view') || 'accept';
  if (v === 'day') document.body.classList.add('theme-day');
  const wallet = { name: 'Dev wallet', chain: 'solana', address: W };
  return <BrowserRouter><WalletContext.Provider value={{ wallet, signMessage: async () => 'sig' }}>
    <main style={{ padding: 16, maxWidth: 1100, margin: '0 auto', display: 'grid', gap: 16 }}>
      {v === 'data' ? <MyDataCard /> : null}
      {v === 'hq' || v === 'day' ? <LegalRegions call={call} /> : null}
      {v === 'accept' ? <><MyDataCard /><LegalConsent /></> : null}
    </main>
  </WalletContext.Provider></BrowserRouter>;
}

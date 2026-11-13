import React from 'react';
import { WarRoom } from '../components/command/WarRoom';

// 🧪 DEV ONLY (`/dev/war`): the SEC-1 War Room on fixtures (no sign-in, no live backend).
const now = Date.now() / 1000;
const FIX = {
  counts: { events: 6, captures: 2, canaries: 5, opens: 2, keyUses: 1, nets: 1, revoked: 1, reports: 2, byKind: {} },
  feed: [
    { seq: 6, at: now - 2, kind: 'harden', ip: '45.155.205.11', net: '45.155.205.0/24', method: '', path: '', action: 'banned a subnet — 3 scanners from one /24' },
    { seq: 5, at: now - 9, kind: 'canary-key', ip: '91.92.1.4', net: '91.92.1.0/24', method: 'GET', path: '/api/reputation/me', action: 'a planted fake key was used against us' },
    { seq: 4, at: now - 20, kind: 'canary', ip: '5.6.7.8', net: '5.6.7.0/24', method: 'GET', path: '/api/reputation/c/ab12…', action: 'canary opened' },
    { seq: 3, at: now - 44, kind: 'decoy', ip: '45.155.205.11', net: '45.155.205.0/24', method: 'POST', path: '/admin/export-keys', action: 'served a decoy + captured' },
    { seq: 2, at: now - 70, kind: 'replay', ip: '2.2.2.2', net: '2.2.2.0/24', method: 'GET', path: '/api/reputation/admin/money', action: 'tarpit + flagged' },
    { seq: 1, at: now - 120, kind: 'probe', ip: '45.155.205.11', net: '45.155.205.0/24', method: 'GET', path: '/.env', action: 'seen' },
  ],
  timeline: Array.from({ length: 24 }, (_, i) => ({ h: Math.floor(now / 3600) * 3600 - (23 - i) * 3600, probe: i % 4, decoy: i % 3, harden: i === 23 ? 2 : 0 })),
  captures: [
    { at: now - 44, ip: '45.155.205.11', net: '45.155.205.0/24', ua: 'python-requests/2.31', method: 'POST', path: '/admin/export-keys', bodyLen: 312 },
    { at: now - 120, ip: '45.155.205.11', net: '45.155.205.0/24', ua: 'python-requests/2.31', method: 'GET', path: '/.env', bodyLen: 0 },
  ],
  canaries: [{ tok: 'ab12', origin: 'keys-decoy', opens: 1, keyUses: 1, at: now - 50 }],
  hits: [{ at: now - 20, tok: 'ab12', origin: 'keys-decoy', ip: '5.6.7.8', net: '5.6.7.0/24', ua: 'Mozilla/5.0 (X11; Linux) Chrome/139', ref: 'http://pastebin-mirror', lang: 'ru-RU' }],
  nets: [{ net: '45.155.205.0/24', at: now - 2, fps: 3, left: 7 * 86400, why: '3 scanners from one subnet probed decoys' }],
  moves: [
    { kind: 'ban-net', net: '45.155.205.0/24', at: now - 2, why: '3 scanners from one subnet probed decoys' },
    { kind: 'revoke-session', at: now - 300, why: 'the session signature appeared from a second device' },
  ],
  reports: [{ at: now - 4000, wallet: 'He11o…9xQp', detail: 'The /api/reputation/observe endpoint echoes the referer unescaped in an error page — reflected XSS PoC attached.' }],
  hardening: {
    total: 10, counts: { done: 6, partial: 3, todo: 1 },
    items: [
      { id: 'social-multisig', attack: 'Drift $285M (Apr 2026)', how: 'In-person social engineering + durable nonces got multisig signers to pre-authorise routine-looking txns.', item: 'Every order shows coins/side/amount and is re-verified signed==quoted; no pre-authorised or resubmitted txns.', state: 'done', source: 'cryptotimes.io' },
      { id: 'addr-poison', attack: 'Address poisoning (65M+ txns)', how: 'A lookalike address seeded into history; the victim copies it and sends to the attacker.', item: 'Full address + verified label before any send; warn on first-seen counterparties.', state: 'todo', source: 'blockaid.io' },
      { id: 'scanner-recon', attack: 'Automated recon / drainer scanning', how: 'Bots probe /.env, /wp-login, key-export paths before an attack.', item: 'Decoys capture + canary the recon; a subnet of scanners is banned; learned UA rules block the tool.', state: 'done', source: 'FEELESS' },
    ],
  },
  encyclopedia: {
    intro: 'How attacks work, so we can defend — threat intel for defenders, not an offensive guide.', total: 10,
    entries: [
      { id: 'recon', name: 'Reconnaissance & scanning', how: 'Bots request known-sensitive paths and fingerprint servers before striking.', defence: 'Decoys, canaries, subnet bans, learned UA rules, no version leakage.' },
      { id: 'drainer', name: 'Wallet drainers & malicious approvals', how: 'A crafted transaction simulates benign then drains or hands over authority on sign.', defence: 'Sign only what is on screen; server re-derives effect vs the signed txn; refuse authority changes.' },
      { id: 'laundering', name: 'Cash-out & laundering', how: 'Stolen funds hop through mixers to an exchange; tracing + freezes recover them.', defence: 'On-chain trace + evidence pack for an exchange / IC3. We report, never counter-hack.' },
    ],
  },
  bounty: {
    intro: 'Found a real security issue? Report it privately, give us time to fix, and get paid.',
    inScope: ['The FEELESS web app + API', 'Fund-safety / signing / quote-integrity bugs', 'Admin / session / privilege-escalation bugs'],
    outOfScope: ['Denial of service / floods', 'Automated scanner noise', "Anything touching other users' funds", 'Social engineering of staff'],
    rules: ['Report privately first, no public disclosure until fixed', 'No data exfiltration beyond PoC', 'One wallet per researcher', 'The owner decides each reward'],
    severity: [],
  },
};
const call = path => Promise.resolve(path.includes('trace') ? { trace: { outCount: 3, counterparties: 2, hops: [{ to: 'Binance14…', amount: 3.5, n: 2 }, { to: 'Tornado…', amount: 0.3, n: 1 }] }, pack: 'FEELESS security evidence pack …' } : FIX);

export default function WarRoomHarness() {
  return <div style={{ minHeight: '100vh', boxSizing: 'border-box', padding: 16, background: 'var(--m-bg, #050806)', color: 'var(--m-text, #dfe)' }}>
    <h2 className="m-label">🧪 DEV PREVIEW · HQ › Safety › War Room (fixtures)</h2><WarRoom call={call} /></div>;
}

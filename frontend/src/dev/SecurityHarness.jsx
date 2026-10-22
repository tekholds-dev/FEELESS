import React from 'react';
import { DefencePanel } from '../components/command/DefencePanel';

// 🧪 DEV ONLY (`/dev/security`): HQ › Security's learned defence + stores map on fixtures (the approvals check needs a wallet — it shows its connect state).
const now = Date.now() / 1000;
const DEF = { blocks: [{ fp: 'a91f02c4e1b3d7aa', n: 2, until: now + 160000, why: 'probed a decoy (/api/reputation/.env)', at: now - 7000, left: 160000 }, { fp: '5c0e99ab12f03d44', n: 1, until: now + 80000, why: 'probed a decoy (/api/wp-login.php)', at: now - 3000, left: 80000 }],
  rules: [{ ua: 'zgrab/0.x', why: 'a scanner seen from 4 IPs', hits: 37, at: now - 9000, last: now - 60 }], tarpit: 2,
  incidents: [{ fp: 'a91f02c4e1b3d7aa', kind: 'honeypot', ip: '45.155.205.11', ua: 'python-requests/2.31', first: now - 7300, last: now - 7000, n: 3, action: 'blocked', report: 'Abuse report — honeypot…' },
    { fp: '77aa', kind: 'scraper', ip: '91.92.1.4', ua: 'curl/8.4', first: now - 600, last: now - 200, n: 260, action: 'tarpit', report: 'Abuse report — scraper…' }],
  honeypots: ['/.env', '/.git/config', '/wp-login.php', '/wp-admin', '/phpmyadmin', '/server-status', '/config.json', '/backup.zip', '/admin.php'], limits: {} };
const ST = { totalMb: 291.4, over: 3, stale: 50, staleMb: 12.6, byClass: { cache: { mb: 228.1, n: 40 }, money: { mb: 14.2, n: 22 }, log: { mb: 9.8, n: 30 }, snapshot: { mb: 12.6, n: 50 }, memory: { mb: 1.9, n: 8 }, other: { mb: 24.8, n: 40 } },
  stores: [{ name: 'logos/', mb: 151, class: 'cache', capMb: 12, pct: 1258, state: 'over' }, { name: 'pump_callers.json', mb: 28.3, class: 'cache', capMb: 12, pct: 235, state: 'over' }, { name: 'uploads/', mb: 25, class: 'cache', capMb: 12, pct: 208, state: 'over' },
    { name: 'realcfg_before_clean1009.json', mb: 0.4, class: 'snapshot', capMb: null, pct: null, ageD: 13.2, state: 'stale' }, { name: 'chat.json', mb: 2.5, class: 'log', capMb: 8, pct: 31, state: 'ok' }, { name: 'candle_ticks.json', mb: 7.3, class: 'cache', capMb: 12, pct: 81, state: 'watch' }] };
const call = path => Promise.resolve(path.includes('/stores') ? ST : DEF);

export default function SecurityHarness() {
  return <div style={{ height: '100vh', overflowY: 'auto', boxSizing: 'border-box', padding: 16, background: '#050806', color: '#dfe' }}>
    <h2 className="m-label">🧪 DEV PREVIEW · HQ › Security (fixtures)</h2><DefencePanel call={call} /></div>;
}

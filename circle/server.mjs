// FEELESS Circle wallets sidecar — localhost only. The reputation backend is the only caller and it
// enforces owner-only access. Keys (CIRCLE_API_KEY, ENTITY_SECRET) are read from backend/.env and
// never returned, logged or stored elsewhere. Circle holds the wallet keys; FEELESS never sees them.
import { fileURLToPath } from 'node:url';
import http from 'node:http';
import fs from 'node:fs';
import crypto from 'node:crypto';
import dotenv from 'dotenv';
import { initiateDeveloperControlledWalletsClient } from '@circle-fin/developer-controlled-wallets';

const ENV = fileURLToPath(new URL('../backend/.env', import.meta.url));
const STATE = fileURLToPath(new URL('../backend/data/circle_state.json', import.meta.url));
const CHAINS = new Set(['SOL-DEVNET', 'ETH-SEPOLIA', 'BASE-SEPOLIA', 'MATIC-AMOY', 'ARB-SEPOLIA', 'SOL', 'ETH', 'BASE', 'MATIC', 'ARB']);
const read = () => { try { return JSON.parse(fs.readFileSync(STATE, 'utf8')); } catch { return {}; } };
const write = s => fs.writeFileSync(STATE, JSON.stringify(s));

function client() {
  dotenv.config({ path: ENV, override: true });
  if (!process.env.CIRCLE_API_KEY) return { error: 'CIRCLE_API_KEY missing' };
  if (!process.env.ENTITY_SECRET) return { error: 'ENTITY_SECRET not registered yet — run: cd circle && npm install && node setup.mjs' };
  return { sdk: initiateDeveloperControlledWalletsClient({ apiKey: process.env.CIRCLE_API_KEY, entitySecret: process.env.ENTITY_SECRET }) };
}

async function walletSet(sdk) {
  const s = read();
  if (s.walletSetId) return s.walletSetId;
  const r = await sdk.createWalletSet({ name: 'FEELESS creator wallets', idempotencyKey: crypto.randomUUID() });
  s.walletSetId = r.data?.walletSet?.id; write(s); return s.walletSetId;
}

const routes = {
  'GET /status': async () => { const c = client(); return { configured: !c.error, reason: c.error || null, testnet: (process.env.CIRCLE_API_KEY || '').startsWith('TEST_') }; },
  'GET /wallets': async () => {
    const { sdk, error } = client(); if (error) return { wallets: [], reason: error };
    const setId = read().walletSetId; if (!setId) return { wallets: [] };
    const r = await sdk.listWallets({ walletSetId: setId, pageSize: 50 });
    const wallets = r.data?.wallets || [];
    const withBal = await Promise.all(wallets.map(async w => {
      try { const b = await sdk.getWalletTokenBalance({ id: w.id }); return { ...w, balances: (b.data?.tokenBalances || []).map(t => ({ symbol: t.token?.symbol, amount: t.amount, tokenId: t.token?.id })) }; }
      catch { return { ...w, balances: [] }; }
    }));
    return { wallets: withBal.map(w => ({ id: w.id, address: w.address, blockchain: w.blockchain, name: w.name, state: w.state, createDate: w.createDate, balances: w.balances })) };
  },
  'POST /wallets': async body => {
    const { sdk, error } = client(); if (error) throw new Error(error);
    const chain = String(body.blockchain || '');
    if (!CHAINS.has(chain)) throw new Error('Unsupported blockchain.');
    const name = String(body.name || 'Creator wallet').slice(0, 40);
    const r = await sdk.createWallets({ walletSetId: await walletSet(sdk), accountType: 'EOA', blockchains: [chain], count: 1, metadata: [{ name }], idempotencyKey: crypto.randomUUID() });
    const w = r.data?.wallets?.[0] || {};
    return { wallet: { id: w.id, address: w.address, blockchain: w.blockchain, name } };
  },
  'POST /wallets/rename': async body => {
    const { sdk, error } = client(); if (error) throw new Error(error);
    const name = String(body.name || '').slice(0, 40);
    if (!body.id || name.length < 2) throw new Error('Wallet id and a name (2+ chars) are required.');
    await sdk.updateWallet({ id: String(body.id), name });
    return { ok: true, id: body.id, name };
  },
  // Send from a Circle wallet. Circle signs with the entity secret; the FEELESS backend checks owner + amount first.
  'POST /transfer': async body => {
    const { sdk, error } = client(); if (error) throw new Error(error);
    const amount = String(body.amount || '');
    if (!body.walletId || !body.tokenId || !body.to || !/^\d+(\.\d+)?$/.test(amount) || Number(amount) <= 0) throw new Error('walletId, tokenId, to and a positive amount are required.');
    const r = await sdk.createTransaction({ walletId: String(body.walletId), tokenId: String(body.tokenId), destinationAddress: String(body.to), amount: [amount],
      fee: { type: 'level', config: { feeLevel: 'MEDIUM' } }, idempotencyKey: String(body.idempotencyKey || crypto.randomUUID()) });
    return { id: r.data?.id, state: r.data?.state };
  },
  // Owner-approved: sign (never send) one Solana transaction for the Fuse wallet keeper. The FEELESS backend builds it from a
  // Jupiter quote, checks the owner's hard limits first, only for the Fuse wallet id, and broadcasts it itself.
  'POST /sign': async body => {
    const { sdk, error } = client(); if (error) throw new Error(error);
    if (!body.walletId || !body.rawTransaction) throw new Error('walletId and rawTransaction are required.');
    const r = await sdk.signTransaction({ walletId: String(body.walletId), rawTransaction: String(body.rawTransaction), memo: String(body.memo || 'FEELESS Fuse card').slice(0, 80) });
    return { signedTransaction: r.data?.signedTransaction, signature: r.data?.signature, txHash: r.data?.txHash };
  },
};

http.createServer(async (req, res) => {
  const key = `${req.method} ${req.url.split('?')[0]}`;
  const fn = routes[key];
  res.setHeader('Content-Type', 'application/json');
  if (!fn) { res.statusCode = 404; return res.end('{"detail":"not found"}'); }
  let raw = ''; for await (const chunk of req) raw += chunk;
  try { res.end(JSON.stringify(await fn(raw ? JSON.parse(raw) : {}))); }
  catch (e) { res.statusCode = 400; res.end(JSON.stringify({ detail: String(e?.response?.data?.message || e.message || 'Circle request failed').slice(0, 200) })); }
}).listen(5111, '127.0.0.1', () => console.log('circle sidecar on 127.0.0.1:5111'));

// One-time Circle setup: creates the entity secret, registers it with Circle and saves it to backend/.env.
// The secret is never printed. Circle writes a recovery file to ~/.circle — back it up (password manager).
//   cd circle && npm install && node setup.mjs
import { fileURLToPath } from 'node:url';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import dotenv from 'dotenv';
import { registerEntitySecretCiphertext } from '@circle-fin/developer-controlled-wallets';

const ENV = fileURLToPath(new URL('../backend/.env', import.meta.url));
dotenv.config({ path: ENV });
const apiKey = process.env.CIRCLE_API_KEY;
if (!apiKey) { console.error('Add CIRCLE_API_KEY=... (from console.circle.com → API & Client Keys) to backend/.env first.'); process.exit(1); }
if (process.env.ENTITY_SECRET) { console.error('ENTITY_SECRET is already set in backend/.env — nothing to do.'); process.exit(1); }

const entitySecret = crypto.randomBytes(32).toString('hex');
const recoveryDir = path.join(os.homedir(), '.circle');
fs.mkdirSync(recoveryDir, { recursive: true, mode: 0o700 });
await registerEntitySecretCiphertext({ apiKey, entitySecret, recoveryFileDownloadPath: recoveryDir });
fs.appendFileSync(ENV, `\nENTITY_SECRET=${entitySecret}\n`, { mode: 0o600 });
console.log(`✓ Entity secret registered with Circle and saved to backend/.env.\n✓ Recovery file saved in ${recoveryDir} — back it up now.\nNext: restart the backend (bash scripts/start-backend.sh) and open Command Center → Circle wallets.`);

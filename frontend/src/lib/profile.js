import { apiUrl } from './api';

const API = apiUrl('/api');

async function readResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.detail || 'Profile request failed.');
    error.status = response.status;
    error.retryAfter = data.retryAfter;
    throw error;
  }
  return data;
}

export async function walletProof(wallet, signMessage) {
  if (!wallet) throw new Error('Connect a wallet before signing.');
  const challengeResponse = await fetch(`${API}/profile/challenge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ address: wallet.address, chain: wallet.chain }),
  });
  const challenge = await readResponse(challengeResponse);
  const signature = await signMessage(challenge.message);
  return { address: wallet.address, chain: wallet.chain, message: challenge.message, signature };
}

export async function fetchPublicProfile(address, chain) {
  const response = await fetch(`${API}/profile/${encodeURIComponent(address)}?chain=${encodeURIComponent(chain)}`);
  return readResponse(response);
}

export async function fetchOwnProfile(wallet, signMessage) {
  const proof = await walletProof(wallet, signMessage);
  const response = await fetch(`${API}/profile/me`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(proof),
  });
  return { profile: await readResponse(response), proof };
}

export function displayAddress(address) {
  const value = String(address || '');
  return value.length > 13 ? `${value.slice(0, 6)}…${value.slice(-4)}` : value;
}

export function profileLabel(profile) {
  return profile?.username || profile?.displayName || displayAddress(profile?.address);
}

export { API as PROFILE_API };
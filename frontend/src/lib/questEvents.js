import { apiUrl } from './api';
import { readChatSession } from './chatSession';

// Tool quests (case files, war room trades): sent only when you're signed in to chat (no extra signature prompts).
// The server verifies what it can (a war room trade must be one of your confirmed FEELESS trades) and caps the rest.
export function reportQuest(address, kind, ref) {
  const session = address ? readChatSession(address) : null;
  if (!session || !ref) return Promise.resolve(null);
  return fetch(apiUrl('/api/reputation/quests/event'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address, session, kind, ref }) })
    .then(r => (r.ok ? r.json() : null)).then(d => { if (d?.counted) window.dispatchEvent(new CustomEvent('feeless:quest-progress', { detail: { kind } })); return d; }).catch(() => null);
}

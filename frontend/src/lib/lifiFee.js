import { apiUrl } from './api';

// FEELESS fee on LI.FI (EVM swaps + bridges). Configured in HQ → Fees; LI.FI pays it to the
// integrator's fee wallet registered at portal.li.fi. Off when not configured.
let cached = null;
export async function lifiFeeConfig() {
  if (cached) return cached;
  cached = fetch(apiUrl('/api/reputation/fees/public')).then(r => r.json()).then(d => d?.lifi || null).catch(() => null);
  return cached;
}

// FEELESS's share of a LI.FI quote, as LI.FI itemises it in estimate.feeCosts.

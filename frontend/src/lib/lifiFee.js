import { apiUrl } from './api';

// FEELESS fee on LI.FI (EVM swaps + bridges). Configured in Command Center → Fees; LI.FI pays it to the
// integrator's fee wallet registered at portal.li.fi. Off when not configured.
let cached = null;
export async function lifiFeeConfig() {
  if (cached) return cached;
  cached = fetch(apiUrl('/api/reputation/fees/public')).then(r => r.json()).then(d => d?.lifi || null).catch(() => null);
  return cached;
}

export const lifiFeeParams = cfg => (cfg?.integrator && cfg.fee > 0
  ? `&integrator=${encodeURIComponent(cfg.integrator)}&fee=${cfg.fee}` : '');

// A mis-set integrator must never block a user's bridge: re-quote without the fee.
export async function lifiQuote(baseUrl) {
  const cfg = await lifiFeeConfig();
  const withFee = lifiFeeParams(cfg);
  const first = await (await fetch(baseUrl + withFee)).json();
  if (withFee && !first?.estimate && /integrator|fee/i.test(String(first?.message || ''))) {
    const plain = await (await fetch(baseUrl)).json();
    return { ...plain, feelessFeeSkipped: true };
  }
  return first;
}

// FEELESS's share of a LI.FI quote, as LI.FI itemises it in estimate.feeCosts.
export const lifiFeelessFee = quote => (quote?.estimate?.feeCosts || []).find(f => /integrator/i.test(`${f.name} ${f.description || ''}`)) || null;

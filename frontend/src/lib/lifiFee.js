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
export const lifiFeelessFee = quote => {
  const bps = Number(quote?.feeless?.feeBps || 0);
  if (!bps) return null;
  const total = (quote?.estimate?.feeCosts || []).reduce((a, f) => a + Number(f.amountUSD || 0), 0);
  const totalPct = (quote?.estimate?.feeCosts || []).reduce((a, f) => a + Number(f.percentage || 0), 0);
  return { percentage: bps / 10000, amountUSD: totalPct ? total * (bps / 10000) / totalPct : 0 };
};

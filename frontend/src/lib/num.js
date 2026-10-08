// 🔢 ONE number style for the whole site (owner: "a coin at .0000004 auto-sets the small number for how many zeros, commas, $").
//   tiny(0.0000004123)  → "0.0₆4123"   (≥ 4 zeros after the point collapse into a subscript count)
//   tiny(0.00123)       → "0.00123"    tiny(1234.5) → "1,234.5"
//   price(v) = "$" + tiny(v) · usd(v) = compact dollars ($4.4M, $12.3K, $812) · pct(v) = +12.3% / 12.4x for huge moves
const SUB = '₀₁₂₃₄₅₆₇₈₉';
const sub = n => String(n).split('').map(d => SUB[+d]).join('');

export function tiny(v, sig = 4) {
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  if (n === 0) return '0';
  const neg = n < 0 ? '-' : ''; const a = Math.abs(n);
  if (a >= 1) return neg + a.toLocaleString('en-US', { maximumFractionDigits: a >= 1000 ? 2 : Math.max(2, sig - 1) });
  const zeros = Math.ceil(-Math.log10(a)) - 1;                    // 0.0004 → 3 zeros after the point · 0.00001 → 4
  const digits = Math.round(a * 10 ** (zeros + sig)).toString().replace(/0+$/, '') || '0';
  if (zeros >= 4) return `${neg}0.0${sub(zeros)}${digits.slice(0, sig)}`;
  return neg + Number(a.toPrecision(sig)).toFixed(Math.min(20, zeros + sig)).replace(/0+$/, '').replace(/\.$/, '');
}

export const price = (v, sig = 4) => (Number(v) > 0 ? `$${tiny(v, sig)}` : '—');

export function usd(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  const a = Math.abs(n); const s = n < 0 ? '-' : '';
  if (a >= 1e9) return `${s}$${(a / 1e9).toFixed(2)}B`;
  if (a >= 1e6) return `${s}$${(a / 1e6).toFixed(2)}M`;
  if (a >= 1e4) return `${s}$${(a / 1e3).toFixed(1)}K`;
  if (a >= 1) return `${s}$${a.toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
  return `${s}$${tiny(a, 3)}`;
}

export function pct(v, digits = 1) {
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  if (n >= 1000) return `${(n / 100 + 1).toLocaleString('en-US', { maximumFractionDigits: 1 })}x`;   // +1,140% reads as 12.4x
  return `${n > 0 ? '+' : ''}${n.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })}%`;
}

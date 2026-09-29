import React, { useEffect, useMemo, useState } from 'react';
import { useMarket } from '../../hooks/useMarket';

// Fun, but honest: the forecast is computed from the live launchpad board (share of green coins,
// average 1h move, how many are dumping). The jokes are jokes; the numbers are real.
export function forecast(pairs = []) {
  const moves = pairs.map(p => Number(p.priceChange?.h1)).filter(Number.isFinite);
  if (moves.length < 4) return null;
  const green = moves.filter(v => v > 0).length / moves.length;
  const sorted = [...moves].sort((a, b) => a - b);
  const avg = sorted[Math.floor(sorted.length / 2)];   // median: one +50,000% fresh listing can't fake the weather
  const dumping = moves.filter(v => v <= -30).length;
  const ripping = moves.filter(v => v >= 100).length;
  let icon, line;
  if (dumping >= Math.max(3, moves.length * 0.25)) { icon = '⛈️'; line = 'Rug storm warning. Seatbelts on, stops tight.'; }
  else if (green >= 0.7 && avg >= 20) { icon = '☀️'; line = 'Scorching. Send it responsibly. Sunscreen = take profits.'; }
  else if (green >= 0.55) { icon = '🌤️'; line = 'Mostly green with light rug showers in the afternoon.'; }
  else if (green >= 0.4) { icon = '⛅'; line = 'Crab weather. Bring a sideways umbrella.'; }
  else { icon = '🌧️'; line = 'Red rain. Paper-hand advisory in effect.'; }
  return { icon, line, green: Math.round(green * 100), avg, dumping, ripping, n: moves.length };
}

const FEECAT_SAYS = [
  'FeeCat has never paid a hidden fee. FeeCat has also never paid rent.',
  'Buying the top is just early for the next cycle. — nobody wise',
  'Your bags are not heavy. You are just strong.',
  'In a FEELESS world, the only fee is emotional damage.',
  'Dev sold? Dev was never your friend. FeeCat is.',
  'Zoom out. No, further. Okay that’s the whole universe, zoom back in.',
  'Rule 1: take profit. Rule 2: see rule 1. Rule 3: FeeCat naps at 3pm.',
  'Diamond hands are just paper hands that forgot the password.',
  'Every rug has a silver lining: it was only paper money. Right? Right?',
  'Liquidity pulled faster than FeeCat off a hot keyboard.',
];

export function DegenWeather({ scope = 'launchpads', compact = false }) {
  const { data } = useMarket(`/feed?kind=trending&chain=solana&page=1&scope=${scope}`, 60000);
  const f = useMemo(() => forecast(data?.pairs || []), [data]);
  const [i, setI] = useState(() => Math.floor(Math.random() * FEECAT_SAYS.length));
  useEffect(() => { const t = setInterval(() => setI(n => (n + 1) % FEECAT_SAYS.length), 9000); return () => clearInterval(t); }, []);
  return <section className={`degen-weather ${compact ? 'is-compact' : ''}`} data-testid="degen-weather">
    <div className="dw-main">
      <span className="dw-icon" aria-hidden="true">{f?.icon || '🌫️'}</span>
      <div><small>DEGEN WEATHER · LIVE</small><b>{f ? f.line : 'Fog. Forecast loading from the trenches…'}</b>
        {f && <em>{f.green}% of {f.n} top coins green · median {f.avg >= 0 ? '+' : ''}{f.avg.toFixed(0)}% 1h · {f.ripping} ripping · {f.dumping} dumping</em>}</div>
    </div>
    <p className="dw-says" key={i}><span>🐱 FeeCat says</span>{FEECAT_SAYS[i]}</p>
  </section>;
}

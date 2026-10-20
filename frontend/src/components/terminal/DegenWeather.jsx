import React, { useEffect, useMemo, useState } from 'react';
import { useMarket } from '../../hooks/useMarket';
import { useCoinRead } from './ChartVitals';
import { useCoinEdge } from '../../lib/coinEdge';
import '../../styles/warSky.css';

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

const num = v => (v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v));
const k$ = v => (v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Math.round(v)}`);

// 🌦 THE WEATHER OVER ONE COIN (owner, 2026-10-19: "degen weather in war room needs to show per viewed coin rep and all vital data"): the coin's
// own read (coin-read: vital grade, rug / heat meters, holders, dev, bundles, snipers, insiders, buyers, organic, creator crew, tape) + its
// live pair → one forecast and a tile per vital, each toned good / watch / bad. Every number is a reading we have; a missing one is "—".
export function coinForecast(read, pair, edge) {
  const r = read?.row || {}; const v = read?.vital || {}; const tv = read?.tv || {};
  const pc = pair?.priceChange || {}; const tx = pair?.txns?.h1 || {};
  const chg5 = num(pc.m5) ?? num(r.chg5m); const chg1 = num(pc.h1) ?? num(r.chg1h);
  const b = num(tx.buys); const sl = num(tx.sells);
  const buys = b != null && sl != null && b + sl > 0 ? (100 * b) / (b + sl) : num(r.buyShare);
  const rug = num(tv.rug); const heat = num(tv.heat); const grade = v.grade || null;
  const sym = pair?.baseToken?.symbol || r.symbol || 'this coin';
  const call = (tv.call || [])[1];
  let icon, line, tone;
  if ((rug != null && rug >= 65) || grade === 'F' || call === 'RUG BAIT') { icon = '⛈️'; tone = 'storm'; line = `Rug storm over $${sym} — the holders read like an exit. Stops tight or stay out.`; }
  else if ((call === 'SEND IT' || (heat != null && heat >= 70)) && (rug == null || rug <= 35)) { icon = '☀️'; tone = 'hot'; line = `Heatwave on $${sym} — buyers stacking, holders arriving. Take profit into the sun.`; }
  else if (buys != null && buys >= 58 && (chg5 ?? 0) >= 0) { icon = '🌤️'; tone = 'warm'; line = `Warm front on $${sym} — ${Math.round(buys)}% of trades are buys.`; }
  else if ((buys != null && buys <= 42) || (chg5 != null && chg5 <= -5)) { icon = '🌧️'; tone = 'rain'; line = `Sell rain on $${sym} — sellers lead${chg5 != null ? `, ${chg5.toFixed(1)}% in 5 min` : ''}.`; }
  else { icon = '⛅'; tone = 'crab'; line = `Crab weather on $${sym} — no side in charge yet.`; }
  const crew = v.crew || null; const rep = edge?.runner?.creatorRep || null;
  const T = (k, label, val, t, tip) => ({ k, label, val, t, tip });
  const top10 = num(r.top10); const dev = num(r.dev); const ins = num(r.insiders); const bun = num(r.bundledN); const snp = num(r.snipersN); const org = num(v.organicPct);
  const tiles = [
    T('grade', 'VITAL', grade ? `${grade} · ${v.score ?? '—'}` : '—', !grade ? '' : 'AB'.includes(grade) ? 'good' : grade === 'C' ? 'watch' : 'bad', v.word || 'FEELESS vital grade'),
    T('rug', '☠ RUG', rug != null ? `${Math.round(rug)}` : '—', rug == null ? '' : rug >= 50 ? 'bad' : rug >= 30 ? 'watch' : 'good', 'Rug meter 0–100 from holders, dev, bundles, snipers, socials, pool'),
    T('heat', '🔥 HEAT', heat != null ? `${Math.round(heat)}` : '—', heat == null ? '' : heat >= 60 ? 'good' : heat >= 35 ? 'watch' : 'bad', 'Heat: 5-min pace, buyers, holders arriving'),
    T('buys', 'BUYS 1H', buys != null ? `${Math.round(buys)}%` : '—', buys == null ? '' : buys >= 55 ? 'good' : buys >= 45 ? 'watch' : 'bad'),
    T('m5', '5 MIN', chg5 != null ? `${chg5 > 0 ? '+' : ''}${chg5.toFixed(1)}%` : '—', chg5 == null ? '' : chg5 >= 0 ? 'good' : chg5 > -5 ? 'watch' : 'bad'),
    T('top10', 'TOP-10', top10 != null ? `${Math.round(top10)}%` : '—', top10 == null ? '' : top10 < 25 ? 'good' : top10 < 40 ? 'watch' : 'bad', 'Share the 10 biggest wallets hold'),
    T('dev', 'DEV', dev != null ? `${dev.toFixed(1)}%` : '—', dev == null ? '' : dev < 5 ? 'good' : dev < 10 ? 'watch' : 'bad'),
    T('ins', 'INSIDERS', ins != null ? `${Math.round(ins)}%` : '—', ins == null ? '' : ins < 8 ? 'good' : ins < 15 ? 'watch' : 'bad'),
    T('bun', 'BUNDLED', bun != null ? String(bun) : '—', bun == null ? '' : bun <= 1 ? 'good' : bun <= 3 ? 'watch' : 'bad'),
    T('snp', 'SNIPERS', snp != null ? String(snp) : '—', snp == null ? '' : snp <= 3 ? 'good' : snp <= 8 ? 'watch' : 'bad'),
    T('org', 'ORGANIC', org != null ? `${Math.round(org)}%` : '—', org == null ? '' : org >= 20 ? 'good' : org >= 5 ? 'watch' : 'bad', 'Share of volume from real wallets (Jupiter)'),
    T('hold', 'HOLDERS', num(r.holders) != null ? Number(r.holders).toLocaleString('en-US') : '—', ''),
    T('liq', 'POOL', num(pair?.liquidity?.usd) ?? num(r.liq) ? k$(num(pair?.liquidity?.usd) ?? num(r.liq)) : '—', ''),
  ];
  const repWord = rep ? (typeof rep === 'string' ? rep : rep.verdict || rep.label || '') : '';
  const repTone = /clean|good/i.test(repWord) ? 'good' : /suspect|high|flag/i.test(repWord) ? 'bad' : repWord ? 'watch' : '';
  return { icon, line, tone, tiles, crew, rep: repWord ? { word: repWord, tone: repTone } : null, flags: (v.flags || []).slice(0, 3), call: tv.call || null };
}

function CoinWeather({ pair, compact }) {
  const mint = pair?.baseToken?.address;
  const read = useCoinRead(mint, pair?.priceUsd);
  const edge = useCoinEdge(mint);
  const f = useMemo(() => coinForecast(read, pair, edge), [read, pair, edge]);
  useEffect(() => { window.dispatchEvent(new CustomEvent('feeless:war-weather', { detail: f.tone })); }, [f.tone]);
  return <section className={`degen-weather dw-coin t-${f.tone} ${compact ? 'is-compact' : ''}`} data-testid="degen-weather" data-tone={f.tone}>
    <div className="dw-main">
      <span className="dw-icon" aria-hidden="true">{f.icon}</span>
      <div><small>COIN WEATHER · ${pair?.baseToken?.symbol || ''} · LIVE{read ? '' : ' · reading…'}</small><b data-testid="dw-coin-line">{f.line}</b>
        <em>{f.crew ? <span className={`dw-crew k-${f.crew.kind}`} data-tip={f.crew.why}>{f.crew.icon} {f.crew.label}</span> : null}
          {f.rep ? <span className={`dw-rep is-${f.rep.tone}`} data-tip="The creator's reputation on FEELESS">🧪 creator {f.rep.word}</span> : null}
          {f.call ? <span className={`dw-call is-${f.call[2] || ''}`}>{f.call[0]} {f.call[1]}</span> : null}</em></div>
    </div>
    <div className="dw-tiles" data-testid="dw-tiles">{f.tiles.map((t, i) => <span key={t.k} className={t.t ? `is-${t.t}` : ''} style={{ '--i': i }} data-tip={t.tip}><i>{t.label}</i><b key={t.val}>{t.val}</b></span>)}</div>
    {f.flags.length ? <p className="dw-flags">{f.flags.map((x, i) => <span key={i} className={`is-${x[2]}`}>{x[0]} {x[1]}</span>)}</p> : null}
  </section>;
}

export function DegenWeather({ scope = 'launchpads', compact = false, pair = null }) {
  if (pair?.baseToken?.address) return <CoinWeather pair={pair} compact={compact} />;
  return <MarketWeather scope={scope} compact={compact} />;
}

function MarketWeather({ scope, compact }) {
  const { data } = useMarket(`/feed?kind=trending&chain=solana&page=1&scope=${scope}`, 60000);
  const f = useMemo(() => forecast(data?.pairs || []), [data]);
  const [i, setI] = useState(() => Math.floor(Math.random() * FEECAT_SAYS.length));
  useEffect(() => { const t = setInterval(() => setI(n => (n + 1) % FEECAT_SAYS.length), 9000); return () => clearInterval(t); }, []);
  const tone = !f ? 'crab' : f.icon === '⛈️' ? 'storm' : f.icon === '☀️' ? 'hot' : f.icon === '🌤️' ? 'warm' : f.icon === '🌧️' ? 'rain' : 'crab';
  useEffect(() => { window.dispatchEvent(new CustomEvent('feeless:war-weather', { detail: tone })); }, [tone]);
  return <section className={`degen-weather ${compact ? 'is-compact' : ''}`} data-testid="degen-weather">
    <div className="dw-main">
      <span className="dw-icon" aria-hidden="true">{f?.icon || '🌫️'}</span>
      <div><small>DEGEN WEATHER · LIVE</small><b>{f ? f.line : 'Fog. Forecast loading from the trenches…'}</b>
        {f && <em>{f.green}% of {f.n} top coins green · median {f.avg >= 0 ? '+' : ''}{f.avg.toFixed(0)}% 1h · {f.ripping} ripping · {f.dumping} dumping</em>}</div>
    </div>
    <p className="dw-says" key={i}><span>🐱 FeeCat says</span>{FEECAT_SAYS[i]}</p>
  </section>;
}

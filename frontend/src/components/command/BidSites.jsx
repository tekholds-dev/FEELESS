import React, { useState } from 'react';

// 🇺🇸 REAL-MONEY SITES (owner 2026-11-04): links only. No bet is placed, no money moves and no login is shared from FEELESS (DECISIONS: no betting house).
// Each status is what we could read on 2026-11-04. Change a status only after reading that site's own terms.
export const BID_SITES = [
  { k: 'kalshi', name: 'Kalshi', url: 'https://kalshi.com', docs: 'https://docs.kalshi.com/welcome', status: 'api', what: 'Sports, news, finance contracts', line: 'Official trading API and a demo exchange, under its Developer Agreement.', where: 'CFTC-regulated. Arizona and Wisconsin have open cases against it.' },
  { k: 'polymarket', name: 'Polymarket US', url: 'https://polymarket.us', docs: 'https://docs.polymarket.us/', status: 'api', what: 'Sports, news, politics contracts', line: 'Official trading API with its own keys. This is the US exchange, not the global site.', where: 'A guide says New York is blocked. Check your state on its site.' },
  { k: 'robinhood', name: 'Robinhood Predictions', url: 'https://robinhood.com/us/en/prediction-markets/', status: 'unread', what: 'Contracts inside the Robinhood app', docs: 'https://cdn.robinhood.com/assets/robinhood/legal/account_scope_agentic_brokerage_agreement.pdf', line: 'Has an official AI-agent account for stocks and crypto, but that agreement never mentions event contracts. Runs on Kalshi’s exchange.', where: 'Availability varies by state.' },
  { k: 'draftkings', name: 'DraftKings Predictions', url: 'https://predictions.draftkings.com', status: 'people', what: 'Sports contracts', line: 'DraftKings bars bots and automated tools. Read from a copy of its terms: its own page blocked our check.', where: 'A report says 38 states at launch.' },
  { k: 'fanduel', name: 'FanDuel Predicts', url: 'https://www.fanduel.com/predicts', terms: 'https://www.fanduel.com/terms', status: 'people', what: 'Sports and event contracts', line: 'FanDuel’s terms ban automated access without its written permission. Predicts may add its own terms.', where: 'A report says 16 states.' },
  { k: 'fanatics', name: 'Fanatics Markets', url: 'https://fanaticsmarkets.com', status: 'unread', what: 'Sports, finance, culture contracts', line: 'Runs through Crypto.com. The page we could read says nothing on automation.', where: 'Availability varies by state.' },
  { k: 'coinbase', name: 'Coinbase', url: 'https://www.coinbase.com/prediction-markets', status: 'unread', what: 'Contracts inside the Coinbase app', line: 'Routes through Kalshi. Its user agreement blocked our check.', where: 'Wisconsin has an open case against it.' },
  { k: 'underdog', name: 'Underdog Predict', url: 'https://underdogfantasy.com/predict', terms: 'https://legal.underdogsports.com/?g=42203', status: 'people', what: 'Sports contracts', line: 'Underdog’s terms ban robots, scrapers and unauthorized scripts. Approved apps and APIs only.', where: 'Availability varies by state.' },
];
const STATUS = { api: ['API OK', 'The site offers its own API for trading. That is not the same as letting an AI browser click its pages'], people: ['PEOPLE ONLY', 'Its terms ban automated tools, so do not point an agent at it'], unread: ['NOT CLEAR', 'We could not find its rule on automation for these contracts. Treat it as people only'] };
const LENS = [['all', 'All'], ['api', 'API OK'], ['people', 'People only']];

export function BidSites() {
  const [lens, setLens] = useState('all');
  const rows = BID_SITES.filter(s => lens === 'all' || (lens === 'api' ? s.status === 'api' : s.status !== 'api'));
  const count = k => BID_SITES.filter(s => s.status === k).length;
  return <section className="bs" data-testid="bid-sites">
    <header className="bs-head m-glass m-live"><span><b>🇺🇸 REAL-MONEY SITES · USA ONLY</b><small>No site says an AI browser may click for you. {count('api')} offer an official API. These are links only: no bet is placed from FEELESS, and your state decides what you can use.</small></span>
      <span className="bs-meter" role="img" aria-label={`${count('api')} with an API, ${count('people')} people only, ${count('unread')} not clear`}>{['api', 'people', 'unread'].map(k => <i key={k} className={`is-${k}`} style={{ flexGrow: count(k) }}><b className="m-num">{count(k)}</b></i>)}</span></header>
    <div className="m-seg bs-seg" role="group" aria-label="Filter sites">{LENS.map(([k, l]) => <button key={k} type="button" className={lens === k ? 'active' : ''} aria-pressed={lens === k} onClick={() => setLens(k)} data-tip={k === 'all' ? 'Every site, most popular first' : k === 'api' ? 'Sites with an official trading API' : 'Banned or not read: a person uses these, not an agent'} data-testid={`bs-lens-${k}`}>{l}</button>)}</div>
    <ul className="bs-list">{rows.map((s, i) => <li key={s.k} className={`m-glass is-${s.status}`} style={{ '--i': i }} data-testid={`bs-${s.k}`}>
      <span className="bs-id"><b>{s.name}</b><small>{s.what}</small></span>
      <em className="bs-status" data-tip={STATUS[s.status][1]}><i aria-hidden="true" />{STATUS[s.status][0]}</em>
      <p>{s.line}</p><small className="bs-where">{s.where}</small>
      <span className="bs-acts"><a className="m-btn m-go" href={s.url} target="_blank" rel="noopener noreferrer" data-tip={`Opens ${s.name} in a new tab. You sign up and bet on their site`}>Open ↗</a>
        {s.docs ? <a className="m-btn" href={s.docs} target="_blank" rel="noopener noreferrer" data-tip={s.status === 'api' ? 'Its official API documents' : 'Its AI-agent account agreement'}>{s.status === 'api' ? 'API docs ↗' : 'Agent terms ↗'}</a> : null}{s.terms ? <a className="m-btn" href={s.terms} target="_blank" rel="noopener noreferrer" data-tip="The terms we read">Terms ↗</a> : null}</span></li>)}</ul>
    <p className="bs-foot">Read on 2026-11-04. Rules change, so check the site’s own terms before you rely on this. Not legal advice.</p>
  </section>;
}

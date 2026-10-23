import React from 'react';
import { HousePricing, CrewsPricing } from '../components/command/FuseAdminSettings';

// 🧪 DEV ONLY (`/dev/fees`): HQ › Core's house-fee block (+ La Familia pricing beside it) on a fake `call` — nothing reaches the server.
const call = (path, opts) => Promise.resolve(opts?.body ? { ...JSON.parse(opts.body), house: JSON.parse(opts.body), feecatSynced: true, crews: JSON.parse(opts.body) } : {});
export default function FeesHarness() {
  return <div className="cc-panel cc-fees" style={{ minHeight: '100vh', padding: 16, background: '#050806', boxSizing: 'border-box' }}>
    <div className="cc-studio-grid"><HousePricing call={call} initial={{ fuseCreatorMaxBps: 5000, feecatFeePct: 1, redeemMp: 1000000, redeemFeecat: 10000 }} /><CrewsPricing call={call} initial={{ createUsd: 25, packUsd: 5, badgeUsd: 2 }} /></div>
  </div>;
}

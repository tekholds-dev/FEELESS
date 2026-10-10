// HQ jump list: every place a search should find, in the owner's words. `tab` = HQ tab, `panel` = a Fuse deck panel,
// `view` = a Money view. Tabs themselves are added by the caller (their labels live in HqDeck).
export const HQ_JUMPS = [
  { label: '🤖 Agents', words: 'agents agent desk tally sherlock trigger devil learn trade trench 5 min ai bots', tab: 'agents' },
  { label: '🪪 Wallet profiles', words: 'circle wallet profile name picture pfp bio edit search wallets', tab: 'fuse', panel: 'profiles' },
  { label: '👛 Fuse wallet', words: 'fuse wallet real money arm kill limits top up dry run audit deposit keeper', tab: 'fuse', panel: 'wallet' },
  { label: '🔑 RPC keys', words: 'rpc key lane quota helius quicknode alchemy endpoint', tab: 'fuse', panel: 'wallet' },
  { label: '🏃 Runners', words: 'runners rounds lanes board gates', tab: 'fuse', panel: 'runners' },
  { label: '⚔ Arena · tier cards', words: 'arena prime tier cards battles bell season paper cards', tab: 'fuse', panel: 'arena' },
  { label: '🧬 Breed & fuse', words: 'lab breed build card publish', tab: 'fuse', panel: 'lab' },
  { label: '🧪 Engine playground', words: 'playground sim brain scenarios battles', tab: 'fuse', panel: 'pub' },
  { label: '💰 Fuse P&L', words: 'fuse pnl profit positions', tab: 'fuse', panel: 'hq' },
  { label: '💲 Fuse fees', words: 'fuse fees bundle swap per coin', tab: 'fuse', panel: 'fees' },
  { label: '💸 Fuse payouts', words: 'payouts fee-back weekly pay creators', tab: 'fuse', panel: 'payouts' },
  { label: '🃏 Card rules', words: 'card rules auto profit levels copy cut auto-collect', tab: 'fuse', panel: 'rules' },
  { label: '⚡ Engine · gates', words: 'engine funnel gates dial runner settings top-10 buy share', tab: 'fuse', panel: 'engine' },
  { label: '⛓ Contract', words: 'contract program go live checklist devnet audit', tab: 'fuse', panel: 'contract' },
  { label: '🏦 Vault', words: 'vault designer shares', tab: 'fuse', panel: 'vault' },
  { label: '🏛 Treasury', words: 'treasury balances wallets money', tab: 'money', view: 'treasury' },
  { label: '⭕ Circle', words: 'circle wallets move send pay', tab: 'money', view: 'circle' },
  { label: '🏦 Fee Reserve pool', words: 'reserve pool rfee', tab: 'money', view: 'reserve' },
];

const norm = s => String(s || '').toLowerCase().replace(/[^a-z0-9$ ]+/g, ' ').trim();

// Every typed word must appear in the label or its words; label hits rank first. Empty query = nothing.
export function jumpSearch(q, rows = HQ_JUMPS, max = 7) {
  const parts = norm(q).split(/\s+/).filter(Boolean);
  if (!parts.length) return [];
  return rows.map((r, i) => { const l = norm(r.label), w = `${l} ${norm(r.words)}`;
    if (!parts.every(p => w.includes(p))) return null;
    return [r, (parts.every(p => l.includes(p)) ? 0 : 100) + (l.startsWith(parts[0]) || l.includes(` ${parts[0]}`) ? 0 : 10) + i / 100]; })
    .filter(Boolean).sort((a, b) => a[1] - b[1]).slice(0, max).map(x => x[0]);
}

export const LAUNCHPADS = [
  { id: 'feeless-launch', name: 'Launch on FEELESS', symbol: 'F', chainId: 'solana', color: '#14F195', lat: -18, lng: 132, url: '/terminal/launch', description: 'Bring a verified launch to the FEELESS network.', tag: 'FEELESS NATIVE', dexIds: [], isFeelessLaunch: true },
  { id: 'pump', name: 'Pump.fun', symbol: 'P', chainId: 'solana', color: '#34efad', lat: 25, lng: -78, url: process.env.REACT_APP_PUMP_URL, description: 'The home of Solana memecoins.', tag: 'MEME CULTURE', dexIds: ['pump', 'pumpswap', 'pump-fun', 'pump_fun'] },
  { id: 'bonk', name: 'LetsBONK', symbol: 'B', chainId: 'solana', color: '#f5b747', lat: -6, lng: -46, url: 'https://letsbonk.fun/', description: 'Community-first launches on Solana.', tag: 'COMMUNITY', dexIds: [] },
  { id: 'raydium', name: 'LaunchLab', symbol: 'R', chainId: 'solana', color: '#84a5ff', lat: 46, lng: 25, url: 'https://raydium.io/launchpad/', description: 'Token launches from the Raydium ecosystem.', tag: 'RAYDIUM', dexIds: ['raydium-launchlab'] },
  { id: 'meteora', name: 'Meteora', symbol: 'M', chainId: 'solana', color: '#ed8a60', lat: -30, lng: 22, url: 'https://launch.meteora.ag/', description: 'Launch infrastructure and dynamic liquidity.', tag: 'LIQUIDITY', dexIds: ['meteora', 'meteora-dlmm', 'meteora-dbc', 'meteora-damm-v2'] },
  { id: 'moonit', name: 'Moonit', symbol: '☾', chainId: 'solana', color: '#e6ef9f', lat: 4, lng: 152, url: 'https://moon.it/', description: 'Community tokens, from idea to orbit.', tag: 'FAIR LAUNCH', dexIds: ['moonit'] },
  { id: 'four', name: 'Four.meme', symbol: '4', chainId: 'bsc', color: '#efce5c', lat: 48, lng: 93, url: 'https://four.meme/en', description: 'Memecoin discovery on BNB Chain.', tag: 'BNB CHAIN', dexIds: ['four-meme', 'four_meme'] },
];

export const launchpadEcosystem = pad => ({ ...pad, isLaunchpad: true, website: pad.url,
  platforms: [{ name: pad.name, url: pad.url, type: 'launch' },
    { name: 'Discover pools', url: `/terminal/discover?chain=${pad.chainId}`, type: 'analytics' }] });

export function matchesPad(pair, id) {
  const pad = LAUNCHPADS.find(p => p.id === id);
  if (!pad) return true;
  return pair.chainId === pad.chainId && pad.dexIds.includes(pair.dexId?.toLowerCase());
}
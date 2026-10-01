// Ecosystem chain configuration
export const ECOSYSTEMS = [
  {
    id: 'solana',
    name: 'Solana',
    symbol: 'SOL',
    chainId: 'solana',
    lat: 34.0522,
    lng: -118.2437,
    color: '#14F195',
    accent: '#9945FF',
    logo: 'https://cryptologos.cc/logos/solana-sol-logo.png',
    explorer: 'https://solscan.io',
    dex: 'https://raydium.io',
    website: 'https://solana.com',
    platforms: [
      { name: 'Jupiter', url: 'https://jup.ag', type: 'aggregator', logo: 'https://jup.ag/svg/jupiter-logo.svg' },
      { name: 'Raydium', url: 'https://raydium.io', type: 'dex', logo: 'https://raydium.io/logo.png' },
      { name: 'Pump.fun', url: 'https://pump.fun', type: 'launch', logo: 'https://pump.fun/logo.png' },
      { name: 'Orca', url: 'https://www.orca.so', type: 'dex', logo: 'https://www.orca.so/orca-logo.svg' },
      { name: 'Solscan', url: 'https://solscan.io', type: 'explorer', logo: '' },
      { name: 'Birdeye', url: 'https://birdeye.so', type: 'analytics', logo: '' }
    ]
  },
  {
    id: 'ethereum',
    name: 'Ethereum',
    symbol: 'ETH',
    chainId: 'ethereum',
    lat: 51.5074,
    lng: -0.1278,
    color: '#627EEA',
    accent: '#8A92B2',
    logo: 'https://cryptologos.cc/logos/ethereum-eth-logo.png',
    explorer: 'https://etherscan.io',
    dex: 'https://app.uniswap.org',
    website: 'https://ethereum.org',
    platforms: [
      { name: 'Uniswap', url: 'https://app.uniswap.org', type: 'dex', logo: '' },
      { name: 'Etherscan', url: 'https://etherscan.io', type: 'explorer', logo: '' },
      { name: '1inch', url: 'https://1inch.io', type: 'aggregator', logo: '' },
      { name: 'DexScreener', url: 'https://dexscreener.com/ethereum', type: 'analytics', logo: '' }
    ]
  },
  {
    id: 'base',
    name: 'Base',
    symbol: 'BASE',
    chainId: 'base',
    lat: 37.7749,
    lng: -122.4194,
    color: '#0052FF',
    accent: '#4C7BF4',
    logo: 'https://dd.dexscreener.com/ds-data/chains/base.png',
    explorer: 'https://basescan.org',
    dex: 'https://app.uniswap.org',
    website: 'https://base.org',
    platforms: [
      { name: 'Aerodrome', url: 'https://aerodrome.finance', type: 'dex', logo: '' },
      { name: 'Uniswap', url: 'https://app.uniswap.org', type: 'dex', logo: '' },
      { name: 'BaseScan', url: 'https://basescan.org', type: 'explorer', logo: '' },
      { name: 'Virtuals', url: 'https://virtuals.io', type: 'launch', logo: '' }
    ]
  },
  {
    id: 'bnb',
    name: 'BNB Chain',
    symbol: 'BNB',
    chainId: 'bsc',
    lat: 22.3193,
    lng: 114.1694,
    color: '#F3BA2F',
    accent: '#FCD535',
    logo: 'https://cryptologos.cc/logos/bnb-bnb-logo.png',
    explorer: 'https://bscscan.com',
    dex: 'https://pancakeswap.finance',
    website: 'https://bnbchain.org',
    platforms: [
      { name: 'PancakeSwap', url: 'https://pancakeswap.finance', type: 'dex', logo: '' },
      { name: 'BSCScan', url: 'https://bscscan.com', type: 'explorer', logo: '' },
      { name: 'Four.meme', url: 'https://four.meme', type: 'launch', logo: '' }
    ]
  },
  {
    id: 'arbitrum',
    name: 'Arbitrum',
    symbol: 'ARB',
    chainId: 'arbitrum',
    lat: 40.7128,
    lng: -74.0060,
    color: '#28A0F0',
    accent: '#96BEDC',
    logo: 'https://cryptologos.cc/logos/arbitrum-arb-logo.png',
    explorer: 'https://arbiscan.io',
    dex: 'https://app.uniswap.org',
    website: 'https://arbitrum.io',
    platforms: [
      { name: 'GMX', url: 'https://gmx.io', type: 'perps', logo: '' },
      { name: 'Camelot', url: 'https://app.camelot.exchange', type: 'dex', logo: '' },
      { name: 'Arbiscan', url: 'https://arbiscan.io', type: 'explorer', logo: '' }
    ]
  },
  {
    id: 'avalanche',
    name: 'Avalanche',
    symbol: 'AVAX',
    chainId: 'avalanche',
    lat: -33.8688,
    lng: 151.2093,
    color: '#E84142',
    accent: '#FF6B6C',
    logo: 'https://cryptologos.cc/logos/avalanche-avax-logo.png',
    explorer: 'https://snowtrace.io',
    dex: 'https://traderjoexyz.com',
    website: 'https://avax.network',
    platforms: [
      { name: 'Trader Joe', url: 'https://traderjoexyz.com', type: 'dex', logo: '' },
      { name: 'SnowTrace', url: 'https://snowtrace.io', type: 'explorer', logo: '' }
    ]
  },
  {
    id: 'polygon',
    name: 'Polygon',
    symbol: 'MATIC',
    chainId: 'polygon',
    lat: 19.0760,
    lng: 72.8777,
    color: '#8247E5',
    accent: '#A379E8',
    logo: 'https://cryptologos.cc/logos/polygon-matic-logo.png',
    explorer: 'https://polygonscan.com',
    dex: 'https://quickswap.exchange',
    website: 'https://polygon.technology',
    platforms: [
      { name: 'QuickSwap', url: 'https://quickswap.exchange', type: 'dex', logo: '' },
      { name: 'PolygonScan', url: 'https://polygonscan.com', type: 'explorer', logo: '' }
    ]
  },
  {
    id: 'optimism',
    name: 'Optimism',
    symbol: 'OP',
    chainId: 'optimism',
    lat: 35.6762,
    lng: 139.6503,
    color: '#FF0420',
    accent: '#FF6B6C',
    logo: 'https://dd.dexscreener.com/ds-data/chains/optimism.png',
    explorer: 'https://optimistic.etherscan.io',
    dex: 'https://app.uniswap.org',
    website: 'https://optimism.io',
    platforms: [
      { name: 'Velodrome', url: 'https://velodrome.finance', type: 'dex', logo: '' },
      { name: 'Uniswap', url: 'https://app.uniswap.org', type: 'dex', logo: '' },
      { name: 'Optimistic Etherscan', url: 'https://optimistic.etherscan.io', type: 'explorer', logo: '' }
    ]
  },
  {
    id: 'zksync',
    name: 'zkSync Era',
    symbol: 'ZK',
    chainId: 'zksync',
    lat: 48.8566,
    lng: 2.3522,
    color: '#8C8DFC',
    accent: '#B4B5FE',
    logo: 'https://dd.dexscreener.com/ds-data/chains/zksync.png',
    explorer: 'https://explorer.zksync.io',
    dex: 'https://app.uniswap.org',
    website: 'https://zksync.io',
    platforms: [
      { name: 'SyncSwap', url: 'https://syncswap.xyz', type: 'dex', logo: '' },
      { name: 'zkSync Explorer', url: 'https://explorer.zksync.io', type: 'explorer', logo: '' }
    ]
  },
  {
    id: 'zora',
    name: 'Zora',
    symbol: 'ZORA',
    chainId: 'zora',
    lat: 34.0195,
    lng: -118.4912,
    color: '#000000',
    accent: '#8ADFFF',
    logo: 'https://dd.dexscreener.com/ds-data/chains/zora.png',
    explorer: 'https://explorer.zora.energy',
    dex: 'https://zora.co',
    website: 'https://zora.co',
    platforms: [
      { name: 'Zora', url: 'https://zora.co', type: 'launch', logo: '' },
      { name: 'Zora Explorer', url: 'https://explorer.zora.energy', type: 'explorer', logo: '' }
    ]
  },
  {
    id: 'cronos',
    name: 'Cronos',
    symbol: 'CRO',
    chainId: 'cronos',
    lat: 22.3964,
    lng: 114.1095,
    color: '#002D74',
    accent: '#3B5FA0',
    logo: 'https://dd.dexscreener.com/ds-data/chains/cronos.png',
    explorer: 'https://cronoscan.com',
    dex: 'https://vvs.finance',
    website: 'https://cronos.org',
    platforms: [
      { name: 'VVS Finance', url: 'https://vvs.finance', type: 'dex', logo: '' },
      { name: 'CronoScan', url: 'https://cronoscan.com', type: 'explorer', logo: '' }
    ]
  },
  {
    id: 'unichain',
    name: 'Unichain',
    symbol: 'UNI',
    chainId: 'unichain',
    lat: 47.6062,
    lng: -122.3321,
    color: '#FF37C7',
    accent: '#FF8AE0',
    logo: 'https://dd.dexscreener.com/ds-data/chains/unichain.png',
    explorer: 'https://uniscan.xyz',
    dex: 'https://app.uniswap.org',
    website: 'https://unichain.org',
    platforms: [
      { name: 'Uniswap', url: 'https://app.uniswap.org', type: 'dex', logo: '' },
      { name: 'Uniscan', url: 'https://uniscan.xyz', type: 'explorer', logo: '' }
    ]
  },
  {
    id: 'worldchain',
    name: 'World Chain',
    symbol: 'WLD',
    chainId: 'worldchain',
    lat: 25.2048,
    lng: 55.2708,
    color: '#000000',
    accent: '#9BA1A6',
    logo: 'https://dd.dexscreener.com/ds-data/chains/worldchain.png',
    explorer: 'https://worldscan.org',
    dex: 'https://app.uniswap.org',
    website: 'https://world.org',
    platforms: [
      { name: 'Uniswap', url: 'https://app.uniswap.org', type: 'dex', logo: '' },
      { name: 'Worldscan', url: 'https://worldscan.org', type: 'explorer', logo: '' }
    ]
  },
  {
    id: 'sui',
    name: 'Sui',
    symbol: 'SUI',
    chainId: 'sui',
    lat: 1.3521,
    lng: 103.8198,
    color: '#4DA2FF',
    accent: '#6FBFFF',
    logo: 'https://dd.dexscreener.com/ds-data/chains/sui.png',
    explorer: 'https://suivision.xyz',
    dex: 'https://cetus.zone',
    website: 'https://sui.io',
    platforms: [
      { name: 'Cetus', url: 'https://cetus.zone', type: 'dex', logo: '' },
      { name: 'SuiVision', url: 'https://suivision.xyz', type: 'explorer', logo: '' }
    ]
  },
  {
    id: 'feeless',
    name: 'FEELESS',
    symbol: 'FEE',
    chainId: 'solana',
    lat: 0,
    lng: 0,
    color: '#14F195',
    accent: '#00FFA3',
    logo: '',
    explorer: 'https://solscan.io',
    dex: 'https://raydium.io',
    website: '/terminal',
    isFeeless: true,
    platforms: [
      { name: 'FEELESS Terminal', url: '/terminal', type: 'terminal', logo: '' }
    ]
  }
];

export function getEcosystem(id) {
  return ECOSYSTEMS.find(e => e.id === id);
}

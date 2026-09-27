// Vetted venues for creating coins and liquidity pools. Every action happens on the venue's own
// site and is signed by the creator's wallet — FEELESS never holds funds.
export const DEXES = [
  { id: 'raydium', name: 'Raydium CPMM', url: 'https://raydium.io/liquidity/create-pool/', note: 'Standard constant-product pool. Cheapest to create; works everywhere.' },
  { id: 'meteora', name: 'Meteora DAMM v2', url: 'https://app.meteora.ag/', note: 'Dynamic fees — earns more in volatile markets; supports fee scheduling.' },
  { id: 'orca', name: 'Orca Whirlpool', url: 'https://www.orca.so/pools', note: 'Concentrated liquidity — best depth per dollar if you manage ranges.' },
  { id: 'uniswap-base', name: 'Uniswap (Base)', url: 'https://app.uniswap.org/positions/create', note: 'Base: the deepest EVM venue. Pick Base network, pair with WETH or USDC.' },
  { id: 'aerodrome', name: 'Aerodrome (Base)', url: 'https://aerodrome.finance/deposit', note: 'Base-native DEX with emissions — good for incentivised liquidity.' },
];
// Vetted coin makers: each creates a real token (and its first pool/curve) signed by your wallet.
export const COIN_MAKERS = [
  { chain: 'Solana', name: 'pump.fun', url: 'https://pump.fun/create', note: 'Bonding curve → auto-migrates to PumpSwap at completion. Fastest meme launch.' },
  { chain: 'Solana', name: 'LetsBonk', url: 'https://letsbonk.fun', note: 'Bonk-ecosystem launchpad on Raydium LaunchLab rails.' },
  { chain: 'Solana', name: 'Raydium LaunchLab', url: 'https://raydium.io/launchpad/create/', note: 'Custom curve + graduation straight into a Raydium pool.' },
  { chain: 'Base', name: 'Clanker', url: 'https://www.clanker.world/deploy', note: 'One-step ERC-20 + Uniswap v4 pool with locked liquidity.' },
  { chain: 'Base', name: 'Zora', url: 'https://zora.co/create', note: 'Creator coins on Base with built-in liquidity.' },
];
export const LAUNCH_STEPS = ['Make the coin (coin maker below) — your wallet signs; FEELESS never touches funds.', 'Add liquidity on a DEX (or let the curve graduate) and copy the pool address.', 'Verify the pool here so FEELESS indexes it and charts go live.', 'Shield it on the launch page — public promises buyers can check on-chain.'];

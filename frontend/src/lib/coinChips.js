// ↩ / 🔥 which actions a Fuse-wallet coin chip offers: sell when worth something, burn (+ close for the rent) only under 5¢, nothing for SOL
export const chipActs = b => (!b.mint ? [] : b.usd == null ? ['sell', 'burn'] : b.usd < 0.05 ? ['burn', 'sell'] : ['sell']);

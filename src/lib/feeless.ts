export const FEE_MINT = "49MmWE8sgNjuw342Eu7tB9thsVFtvTfKigUw9KSppump";
export const FEECAT_MINT = "AsX2abSJ2HqPqRxUbeYXE5R5ksrmUDz6BMGpg9mDpump";
export type PairData = { baseToken?: { symbol?: string; name?: string }; priceUsd?: string; priceChange?: { h24?: number }; marketCap?: number; volume?: { h24?: number }; liquidity?: { usd?: number }; pairCreatedAt?: number; };
export const money = (value?: number) => value == null ? "—" : `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

import { Link } from "@tanstack/react-router";
import { BarChart3, Bell, CandlestickChart, ExternalLink, MessageCircle, Rocket, Search, Sparkles, WalletCards } from "lucide-react";
import { Button } from "@/components/ui/button";
import feelessAsset from "@/assets/feeless.png.asset.json";
import feecatAsset from "@/assets/feecat.png.asset.json";
import { EmptyState, Panel } from "@/components/feeless-shell";
import { usePairData } from "@/components/market-data";
import { FEE_MINT, FEECAT_MINT, money, type PairData } from "@/lib/feeless";

const price = (data?: PairData) => data?.priceUsd ? `$${data.priceUsd}` : "—";

function Stat({ label, value, positive }: { label: string; value: string; positive?: boolean }) {
  return <div className="min-w-0 border-r border-border px-3 last:border-0"><div className="truncate text-[9px] text-muted-foreground">{label}</div><strong className={`mt-1 block truncate text-xs ${positive ? "text-primary" : ""}`}>{value}</strong></div>;
}

function BrandBanner() {
  return <section className="relative flex min-h-40 overflow-hidden rounded-md border border-border bg-banner px-5 py-5 sm:px-7">
    <div className="relative z-10 max-w-xl self-center"><span className="text-[9px] font-bold uppercase tracking-[0.22em] text-primary">The Solana-first terminal</span><h1 className="mt-2 font-display text-2xl font-black leading-[1.05] sm:text-3xl">SAME TRANSACTIONS.<br/><span className="text-primary">ZERO FEES.</span> MORE FOR YOU.</h1><p className="mt-2 text-xs text-muted-foreground">Trade. Discover. Launch. Earn. A FEELESS future.</p></div>
    <img src={feelessAsset.url} alt="FEELESS token" className="absolute -right-8 -top-16 h-72 w-72 rounded-full object-cover opacity-80 sm:right-3" />
  </section>;
}

function MarketCard({ data, status }: { data: PairData | undefined; status: string }) {
  const change = data?.priceChange?.h24;
  return <Panel title="$FEE / USD" tag={status}>
    <div className="flex items-center gap-3 border-b border-border p-3"><img src={feelessAsset.url} alt="$FEE" className="h-10 w-10 rounded-full object-cover shadow-glow" /><div><h2 className="text-lg font-bold">$FEE</h2><span className="text-[9px] uppercase text-muted-foreground">A FEELESS future</span></div><span className="ml-auto rounded border border-border px-2 py-1 text-[9px] text-primary">Solana</span></div>
    <div className="grid grid-cols-3 border-b border-border py-3 sm:grid-cols-6"><Stat label="Price" value={price(data)} /><Stat label="24h Change" value={change == null ? "—" : `${change > 0 ? "+" : ""}${change}%`} positive={change != null && change >= 0}/><Stat label="Market Cap" value={money(data?.marketCap)} /><Stat label="24h Volume" value={money(data?.volume?.h24)} /><Stat label="Liquidity" value={money(data?.liquidity?.usd)} /><Stat label="Holders" value="—" /></div>
    <div className="flex h-9 items-center gap-1 border-b border-border px-3 text-[9px] text-muted-foreground"><button className="rounded bg-accent px-2 py-1 text-primary">1D</button><button className="px-2">1W</button><button className="px-2">1M</button><span className="ml-auto">Market chart</span></div>
    <div className="market-grid flex h-44 items-center justify-center text-center"><div><div className="text-2xl font-bold">{price(data)}</div><p className="mt-2 max-w-xs text-[10px] text-muted-foreground">{data ? "Live pair metrics loaded. Candle history is not fabricated." : "Live market data is currently unavailable."}</p></div></div>
    <div className="grid gap-2 border-t border-border p-2.5 sm:grid-cols-3">
      <Button asChild><a href={`https://pump.fun/coin/${FEE_MINT}`} target="_blank" rel="noreferrer"><Rocket />View on Pump<ExternalLink /></a></Button>
      <Button variant="outline" asChild><a href={`https://dexscreener.com/solana/${FEE_MINT}`} target="_blank" rel="noreferrer"><CandlestickChart />View on DEX<ExternalLink /></a></Button>
      <Button variant="outline" asChild><a href={`https://jup.ag/swap/SOL-${FEE_MINT}`} target="_blank" rel="noreferrer"><BarChart3 />View on Jupiter<ExternalLink /></a></Button>
    </div>
  </Panel>;
}

function Movers({ fee, cat }: { fee: PairData | undefined; cat: PairData | undefined }) {
  const rows = [{ name: "$FEE", full: "FEELESS", image: feelessAsset.url, data: fee, mint: FEE_MINT }, { name: "FeeCat", full: "FeeCat", image: feecatAsset.url, data: cat, mint: FEECAT_MINT }];
  return <Panel title="Top Movers" tag="Real pairs"><div className="flex gap-1 border-b border-border p-2"><Button size="sm">Trending</Button><Button size="sm" variant="ghost">New</Button><Button size="sm" variant="ghost">Top volume</Button></div><div className="overflow-x-auto"><table className="w-full min-w-[580px] text-left text-[10px]"><thead className="text-muted-foreground"><tr><th className="p-3">#</th><th>Token</th><th>Price</th><th>24h</th><th>Volume</th><th>Market Cap</th><th></th></tr></thead><tbody>{rows.map((row, index) => <tr key={row.mint} className="border-t border-border"><td className="p-3 text-muted-foreground">{index + 1}</td><td><div className="flex items-center gap-2"><img src={row.image} alt="" className="h-6 w-6 rounded-full object-cover"/><div><b>{row.name}</b><small className="block text-muted-foreground">{row.full}</small></div></div></td><td>{price(row.data)}</td><td className={row.data?.priceChange?.h24 != null && row.data.priceChange.h24 >= 0 ? "text-primary" : ""}>{row.data?.priceChange?.h24 == null ? "—" : `${row.data.priceChange.h24}%`}</td><td>{money(row.data?.volume?.h24)}</td><td>{money(row.data?.marketCap)}</td><td><Link to="/token/$mint" params={{ mint: row.mint }} className="text-primary">View</Link></td></tr>)}</tbody></table></div></Panel>;
}

function RightRail() { return <aside className="space-y-2.5">
  <Panel title="FEELESS Chat" tag="Offline"><div className="flex gap-1 border-b border-border p-2 text-[9px]"><span className="rounded bg-accent px-2 py-1 text-primary">General</span><span className="px-2 py-1">Alpha</span><span className="px-2 py-1">Launches</span></div><EmptyState><div><MessageCircle className="mx-auto mb-2 h-5 w-5 text-primary"/>Community chat is waiting for its persistent, rate-limited service. No sample messages shown.</div></EmptyState><div className="border-t border-border p-2"><Button asChild variant="outline" className="w-full"><a href="/chat">Open Chat</a></Button></div></Panel>
  <Panel title="Live Feed" tag="Unavailable"><EmptyState>Confirmed launches, swaps and liquidity events will appear from a configured stream.</EmptyState></Panel>
  <Panel title="Quick Actions"><div className="grid grid-cols-3 gap-px bg-border"><Link to="/pump" className="bg-panel p-3 text-center text-[9px] hover:bg-surface"><Rocket className="mx-auto mb-1 h-4 w-4 text-primary"/>Pump</Link><Link to="/dex" className="bg-panel p-3 text-center text-[9px] hover:bg-surface"><CandlestickChart className="mx-auto mb-1 h-4 w-4 text-primary"/>DEX</Link><Link to="/discover" className="bg-panel p-3 text-center text-[9px] hover:bg-surface"><Search className="mx-auto mb-1 h-4 w-4 text-primary"/>Discover</Link><a href="/launch" className="bg-panel p-3 text-center text-[9px] hover:bg-surface"><Sparkles className="mx-auto mb-1 h-4 w-4 text-primary"/>Launch</a><a href="/portfolio" className="bg-panel p-3 text-center text-[9px] hover:bg-surface"><WalletCards className="mx-auto mb-1 h-4 w-4 text-primary"/>Portfolio</a><a href="/alerts" className="bg-panel p-3 text-center text-[9px] hover:bg-surface"><Bell className="mx-auto mb-1 h-4 w-4 text-primary"/>Alerts</a></div></Panel>
  <Panel title="Market Overview" tag="Live on Solana"><div className="grid grid-cols-2 gap-px bg-border text-[9px]"><div className="bg-panel p-3 text-muted-foreground">Total Market Cap<strong className="mt-1 block text-foreground">—</strong></div><div className="bg-panel p-3 text-muted-foreground">24h Volume<strong className="mt-1 block text-foreground">—</strong></div><div className="bg-panel p-3 text-muted-foreground">Total Tokens<strong className="mt-1 block text-foreground">—</strong></div><div className="bg-panel p-3 text-muted-foreground">Active Traders<strong className="mt-1 block text-foreground">—</strong></div></div></Panel>
  </aside>; }

export function Dashboard() {
  const fee = usePairData(FEE_MINT); const cat = usePairData(FEECAT_MINT);
  return <div className="grid gap-2.5 p-2.5 xl:grid-cols-[minmax(0,1fr)_300px]"><div className="min-w-0 space-y-2.5"><BrandBanner/><MarketCard data={fee.data} status={fee.status}/><Movers fee={fee.data} cat={cat.data}/></div><RightRail/></div>;
}
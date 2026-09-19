import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Home, TrendingUp, Rocket, BarChart3, Compass, Sparkles, Briefcase, Coins,
  Ticket, Cat, MessageCircle, Trophy, Bell, GraduationCap, Map, FileText,
  Settings, Search, Menu, ExternalLink, Star, Zap, Send, ChevronDown,
  Droplet, Activity, Flame, Waves, CircleDollarSign, PenLine
} from 'lucide-react';
import { FeelessMark, FeelessWordmark } from '../components/FeelessLogo';
import WalletModal from '../components/WalletModal';
import EcosystemChat from '../components/EcosystemChat';
import { searchTokens, formatUSD } from '../lib/dexscreener';
import { getEcosystem } from '../lib/ecosystems';
import {
  ResponsiveContainer, ComposedChart, Bar, XAxis, YAxis, Tooltip, Cell,
  Line
} from 'recharts';

const SIDE_ITEMS = [
  { id: 'home', label: 'Home', Icon: Home, active: true },
  { id: 'trade', label: 'Trade', Icon: TrendingUp },
  { id: 'pump', label: 'Pump', Icon: Rocket },
  { id: 'dex', label: 'DEX', Icon: BarChart3 },
  { id: 'discover', label: 'Discover', Icon: Compass },
  { id: 'launch', label: 'Launch', Icon: Sparkles },
  { id: 'portfolio', label: 'Portfolio', Icon: Briefcase },
  { id: 'feeback', label: 'Fee-Back', Icon: Coins },
  { id: 'feetoken', label: 'FEE Token', Icon: Ticket },
  { id: 'feecat', label: 'FeeCat', Icon: Cat },
  { id: 'chat', label: 'Chat', Icon: MessageCircle },
  { id: 'leaderboard', label: 'Leaderboard', Icon: Trophy },
  { id: 'alerts', label: 'Alerts', Icon: Bell },
  { id: 'learn', label: 'Learn', Icon: GraduationCap },
  { id: 'roadmap', label: 'Roadmap', Icon: Map },
  { id: 'whitepaper', label: 'Whitepaper', Icon: FileText },
  { id: 'settings', label: 'Settings', Icon: Settings },
];

function generateCandles(n = 60) {
  const arr = [];
  let base = 0.00012;
  for (let i = 0; i < n; i++) {
    const o = base;
    const change = (Math.random() - 0.48) * 0.00002;
    const c = Math.max(0.00001, o + change);
    const h = Math.max(o, c) + Math.random() * 0.00001;
    const l = Math.min(o, c) - Math.random() * 0.00001;
    const v = 200 + Math.random() * 800;
    const positive = c >= o;
    arr.push({ i, o, h, l, c, v, positive, wickTop: h - Math.max(o,c), body: Math.abs(c-o), bodyBase: Math.min(o,c), wickBot: Math.min(o,c) - l });
    base = c;
  }
  return arr;
}

export default function Terminal() {
  const [walletOpen, setWalletOpen] = useState(false);
  const [connectedWallet, setConnectedWallet] = useState(null);
  const [candles] = useState(() => generateCandles(70));
  const [movers, setMovers] = useState([]);
  const [moversTab, setMoversTab] = useState('Trending');
  const nav = useNavigate();

  useEffect(() => {
    (async () => {
      const r = await searchTokens('sol');
      const filtered = r.filter(p => p.chainId === 'solana').slice(0, 5);
      setMovers(filtered);
    })();
  }, [moversTab]);

  const feelessEco = getEcosystem('feeless');

  return (
    <div className="min-h-screen bg-[#03080a] text-white">
      {/* Top bar */}
      <header className="flex items-center gap-4 px-5 py-3 border-b border-[#14F195]/10 bg-black/50">
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => nav('/')}>
          <FeelessWordmark size={20} />
        </div>
        <div className="flex-1 max-w-2xl mx-auto flex items-center gap-2 bg-black/60 border border-[#14F195]/15 rounded-full px-4 py-2">
          <Search size={14} className="text-white/40"/>
          <input placeholder="Search tokens, wallets, or contract…" className="flex-1 bg-transparent outline-none text-sm placeholder:text-white/30"/>
        </div>
        <button className="relative w-10 h-10 rounded-full bg-black/50 border border-[#14F195]/15 flex items-center justify-center">
          <Bell size={15} className="text-white/70"/>
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-[#14F195] text-black text-[9px] font-bold rounded-full flex items-center justify-center">1</span>
        </button>
        <button onClick={() => setWalletOpen(true)}
          className="px-5 py-2.5 rounded-full bg-[#14F195] hover:bg-[#00FFA3] text-black font-bold text-sm shadow-[0_0_25px_-5px_rgba(20,241,149,0.6)] flex items-center gap-2">
          <Zap size={14}/>{connectedWallet ? connectedWallet.name : 'Connect Wallet'}
        </button>
        <button className="w-10 h-10 rounded-full bg-black/50 border border-[#14F195]/15 flex items-center justify-center"><Menu size={16} className="text-white/70"/></button>
      </header>

      {/* Ticker */}
      <div className="flex items-center gap-6 flex-wrap text-xs px-5 py-2.5 border-b border-[#14F195]/10 bg-black/30">
        <div className="flex items-center gap-2"><div className="w-5 h-5 rounded-full bg-[#14F195]/20 border border-[#14F195]/40 flex items-center justify-center text-[9px] font-bold text-[#14F195]">S</div><span className="text-white/40">SOL</span><span className="text-white font-mono">$142.37</span><span className="text-[#14F195]">+2.4%</span></div>
        <div className="flex items-center gap-2"><span className="text-white/40">24h Volume</span><span className="text-white font-mono">$2.14B</span></div>
        <div className="flex items-center gap-2"><span className="text-white/40">New Launches</span><span className="text-white font-mono">1,247</span></div>
        <div className="flex items-center gap-2"><span className="text-white/40">Trending</span><span className="text-white font-mono">87</span></div>
        <div className="flex items-center gap-2"><span className="text-white/40">Market Cap</span><span className="text-white font-mono">$58.3B</span></div>
        <div className="flex items-center gap-2"><span className="text-white/40">Liquidity</span><span className="text-white font-mono">$4.1B</span></div>
        <div className="ml-auto text-[#14F195] tracking-[0.28em] font-semibold">TRADE . DISCOVER . LAUNCH . EARN</div>
      </div>

      <div className="flex">
        {/* Sidebar */}
        <aside className="w-56 flex-shrink-0 border-r border-[#14F195]/10 bg-black/30 py-3 min-h-[calc(100vh-96px)] flex flex-col">
          <nav className="flex-1 px-2 space-y-0.5">
            {SIDE_ITEMS.map(it => (
              <button key={it.id} className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${it.active ? 'bg-[#14F195]/12 text-[#14F195] border border-[#14F195]/30' : 'text-white/60 hover:text-white hover:bg-white/5'}`}>
                <it.Icon size={15}/>{it.label}
              </button>
            ))}
          </nav>
          <div className="m-3 rounded-2xl bg-gradient-to-br from-[#0a1a13] to-[#050908] border border-[#14F195]/25 p-4 text-center">
            <FeelessMark size={44}/>
            <div className="mt-2 font-black tracking-[0.15em] text-white text-sm">FEELESS</div>
            <div className="text-[8px] tracking-[0.2em] text-[#14F195]/80">SAME TX. ZERO FEES.<br/>MORE FOR YOU.</div>
            <button onClick={() => setWalletOpen(true)} className="mt-3 w-full px-3 py-1.5 rounded-full bg-[#14F195] hover:bg-[#00FFA3] text-black text-[11px] font-bold">Join the Movement</button>
            <div className="mt-3 flex justify-center gap-2 text-white/40">
              <a href="#" className="hover:text-[#14F195]">X</a>
              <a href="#" className="hover:text-[#14F195]">DC</a>
              <a href="#" className="hover:text-[#14F195]">TG</a>
            </div>
            <div className="text-[8px] text-white/40 tracking-[0.2em] mt-2">BUILDING A FEELESS FUTURE.<br/>TOGETHER.</div>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 p-5 grid grid-cols-12 gap-5">
          {/* Hero */}
          <div className="col-span-12 xl:col-span-8 rounded-2xl bg-gradient-to-br from-[#08201a] to-[#031007] border border-[#14F195]/25 p-6 relative overflow-hidden">
            <div className="absolute inset-0 opacity-40 pointer-events-none" style={{ background: 'radial-gradient(circle at 85% 50%, rgba(20,241,149,0.2), transparent 55%)' }}/>
            <div className="relative flex items-center gap-6">
              <div className="flex-1">
                <div className="text-[10px] tracking-[0.3em] text-[#14F195]">THE SOLANA-FIRST TERMINAL</div>
                <h2 className="mt-2 text-4xl font-black leading-tight">SAME TRANSACTIONS.<br/><span className="text-[#14F195] drop-shadow-[0_0_20px_rgba(20,241,149,0.5)]">ZERO FEES.</span> MORE FOR YOU.</h2>
                <p className="mt-3 text-sm text-white/60">Trade. <span className="text-[#14F195]">Discover</span>. Launch. Earn. A FeeLess Future.</p>
                <div className="mt-5 flex gap-3">
                  <button onClick={() => setWalletOpen(true)} className="px-5 py-2.5 rounded-lg bg-[#14F195] hover:bg-[#00FFA3] text-black font-bold text-sm flex items-center gap-2"><Zap size={13}/>Connect Wallet</button>
                  <button className="px-5 py-2.5 rounded-lg bg-black/50 border border-[#14F195]/40 hover:border-[#14F195] text-white font-bold text-sm flex items-center gap-2">Explore <ExternalLink size={13}/></button>
                </div>
              </div>
              <div className="hidden md:block relative">
                <div className="absolute inset-0 rounded-full" style={{ background: 'radial-gradient(circle, rgba(20,241,149,0.4), transparent 60%)', filter: 'blur(28px)' }}/>
                <FeelessMark size={180}/>
                <div className="absolute bottom-4 right-0 text-[#14F195] italic text-sm" style={{fontFamily:'cursive'}}>More for You.</div>
              </div>
            </div>
          </div>

          {/* Chat */}
          <div className="col-span-12 xl:col-span-4 row-span-2 rounded-2xl bg-[#050908] border border-[#14F195]/20 overflow-hidden flex flex-col min-h-[600px]">
            <div className="flex items-center justify-between px-4 py-3 border-b border-[#14F195]/10">
              <div className="flex items-center gap-2"><MessageCircle size={15} className="text-[#14F195]"/><div className="font-bold">FEELESS Chat</div><span className="w-1.5 h-1.5 rounded-full bg-[#14F195] animate-pulse"/></div>
              <div className="text-[10px] text-white/40">1,284 online</div>
            </div>
            <div className="px-4 pt-3 flex gap-1">
              {['General','Alpha','Launches','Trading'].map((t,i) => (
                <button key={t} className={`px-3 py-1 rounded-md text-xs ${i===0?'bg-[#14F195]/15 text-[#14F195] border border-[#14F195]/30':'text-white/50 hover:text-white'}`}>{t}</button>
              ))}
            </div>
            <div className="flex-1 overflow-hidden">
              <EcosystemChat ecosystem={feelessEco} />
            </div>
          </div>

          {/* $FEE token block */}
          <div className="col-span-12 xl:col-span-8 rounded-2xl bg-[#050908] border border-[#14F195]/20 p-5">
            <div className="flex items-center gap-4 flex-wrap">
              <div className="w-14 h-14 rounded-full bg-[#14F195]/12 border border-[#14F195]/40 flex items-center justify-center"><FeelessMark size={30}/></div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-black">$FEE</span>
                  <span className="px-2 py-0.5 rounded bg-[#14F195]/15 text-[#14F195] text-[10px] font-bold flex items-center gap-1"><FeelessMark size={10}/>FEELESS</span>
                </div>
                <div className="text-[11px] text-white/50">A FEELESS FUTURE</div>
              </div>
              <div className="ml-auto flex items-center gap-2 flex-wrap">
                <span className="px-2.5 py-1 rounded-md bg-[#14F195]/10 text-[#14F195] text-[10px] font-bold flex items-center gap-1"><CircleDollarSign size={11}/>Solana</span>
                <span className="px-2.5 py-1 rounded-md bg-emerald-400/10 text-emerald-300 text-[10px] font-bold flex items-center gap-1">✓ Verified</span>
                <span className="px-2.5 py-1 rounded-md bg-white/5 text-white/70 text-[10px] font-bold flex items-center gap-1">👥 Community</span>
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-5 pt-5 border-t border-[#14F195]/10">
              {[['Price','$0.0000',''],['24h Change','+0.00%','#14F195'],['Market Cap','—',''],['24h Volume','—',''],['Liquidity','—','']].map(([k,v,c],i) => (
                <div key={i}><div className="text-[10px] uppercase tracking-wider text-white/40">{k}</div><div className="mt-1 font-mono text-sm" style={{color: c || 'white'}}>{v}</div></div>
              ))}
            </div>
            {/* Timeframe */}
            <div className="mt-5 flex items-center gap-2 flex-wrap">
              {['1m','5m','15m','1h','4h','1D'].map((t,i) => (
                <button key={t} className={`px-3 py-1 rounded-md text-xs font-medium ${t==='1D'?'bg-[#14F195]/15 text-[#14F195] border border-[#14F195]/30':'text-white/50 hover:text-white border border-transparent'}`}>{t}</button>
              ))}
              <div className="ml-auto flex items-center gap-3 text-xs text-white/50">
                <span className="flex items-center gap-1"><Activity size={12}/>Indicators</span>
                <span className="flex items-center gap-1"><PenLine size={12}/>Draw</span>
              </div>
            </div>
            {/* Chart */}
            <div className="mt-3 h-[280px] bg-black/50 rounded-xl border border-white/5 p-2">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={candles} margin={{ top: 10, right: 40, bottom: 10, left: 0 }}>
                  <XAxis dataKey="i" tick={{ fill: '#ffffff40', fontSize: 10 }} axisLine={{ stroke: '#ffffff10' }} tickLine={false} />
                  <YAxis orientation="right" tick={{ fill: '#ffffff40', fontSize: 10 }} axisLine={{ stroke: '#ffffff10' }} tickLine={false} tickFormatter={v => v.toFixed(5)} />
                  <Tooltip contentStyle={{ background: '#0a0f0d', border: '1px solid #14F19540', borderRadius: 8, fontSize: 11 }} />
                  <Bar dataKey="body" stackId="a" fill="transparent" />
                  <Bar dataKey="c" fillOpacity={0}>
                    {candles.map((c, i) => (
                      <Cell key={i} fill={c.positive ? '#14F195' : '#EF4444'} />
                    ))}
                  </Bar>
                  <Line type="monotone" dataKey="c" stroke="#14F195" strokeWidth={1.5} dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
              <div className="text-[9px] text-white/30 mt-1 flex justify-between"><span>TradingView-style</span><span>Jul · Aug · Sep · Oct</span></div>
            </div>
            {/* CTA row */}
            <div className="grid grid-cols-3 gap-3 mt-4">
              <a href="https://pump.fun" target="_blank" rel="noreferrer" className="flex items-center justify-between px-4 py-3 rounded-xl bg-[#14F195] hover:bg-[#00FFA3] text-black transition-colors">
                <div className="flex items-center gap-2"><Rocket size={16}/><div><div className="font-bold text-sm">View on PUMP</div><div className="text-[10px] opacity-70">See on Pump.fun</div></div></div>
                <ExternalLink size={13}/>
              </a>
              <a href="https://dexscreener.com" target="_blank" rel="noreferrer" className="flex items-center justify-between px-4 py-3 rounded-xl bg-black/50 border border-[#14F195]/25 hover:border-[#14F195] text-white transition-colors">
                <div className="flex items-center gap-2"><BarChart3 size={16} className="text-[#14F195]"/><div><div className="font-bold text-sm">View on DEX</div><div className="text-[10px] text-white/50">See on Dexscreener</div></div></div>
                <ExternalLink size={13} className="text-[#14F195]"/>
              </a>
              <a href="https://jup.ag" target="_blank" rel="noreferrer" className="flex items-center justify-between px-4 py-3 rounded-xl bg-black/50 border border-[#14F195]/25 hover:border-[#14F195] text-white transition-colors">
                <div className="flex items-center gap-2"><CircleDollarSign size={16} className="text-[#14F195]"/><div><div className="font-bold text-sm">View on Jupiter</div><div className="text-[10px] text-white/50">Trade on Jupiter</div></div></div>
                <ExternalLink size={13} className="text-[#14F195]"/>
              </a>
            </div>
          </div>

          {/* Top Movers */}
          <div className="col-span-12 xl:col-span-8 rounded-2xl bg-[#050908] border border-[#14F195]/20 p-5">
            <div className="flex items-center gap-3 flex-wrap">
              <div className="flex items-center gap-2"><BarChart3 size={16} className="text-[#14F195]"/><span className="font-bold text-lg">Top Movers</span></div>
              <div className="flex gap-1 ml-2">
                {['Trending','New','Top Gainers','Top Volume'].map(t => (
                  <button key={t} onClick={() => setMoversTab(t)} className={`px-3 py-1 rounded-md text-xs ${moversTab===t?'bg-[#14F195]/15 text-[#14F195] border border-[#14F195]/30':'text-white/50 hover:text-white border border-transparent'}`}>{t}</button>
                ))}
              </div>
              <a href="#" className="ml-auto text-xs text-[#14F195] hover:underline flex items-center gap-1">View All <ExternalLink size={11}/></a>
            </div>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[10px] uppercase tracking-wider text-white/40 border-b border-white/5">
                    <th className="text-left py-2 font-medium">#</th>
                    <th className="text-left font-medium">Token</th>
                    <th className="text-right font-medium">Price</th>
                    <th className="text-right font-medium">1h</th>
                    <th className="text-right font-medium">24h</th>
                    <th className="text-right font-medium">Volume</th>
                    <th className="text-right font-medium">Market Cap</th>
                    <th className="text-right font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {movers.length === 0 && (
                    <tr><td colSpan={8} className="py-6 text-center text-white/40 text-xs">Loading market data…</td></tr>
                  )}
                  {movers.map((p, i) => (
                    <tr key={p.pairAddress || i} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                      <td className="py-3 text-white/50">{i+1}</td>
                      <td className="py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-[#14F195]/10 border border-[#14F195]/30 flex items-center justify-center text-[10px] font-bold text-[#14F195]">{(p.baseToken?.symbol||'?').slice(0,3)}</div>
                          <div>
                            <div className="font-bold">{p.baseToken?.symbol}</div>
                            <div className="text-[10px] text-white/40">{p.baseToken?.name}</div>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 text-right font-mono">{formatUSD(p.priceUsd)}</td>
                      <td className={`py-3 text-right ${(p.priceChange?.h1||0)>=0?'text-[#14F195]':'text-rose-400'}`}>{(p.priceChange?.h1||0).toFixed(2)}%</td>
                      <td className={`py-3 text-right ${(p.priceChange?.h24||0)>=0?'text-[#14F195]':'text-rose-400'}`}>{(p.priceChange?.h24||0).toFixed(2)}%</td>
                      <td className="py-3 text-right font-mono text-white/80">{formatUSD(p.volume?.h24)}</td>
                      <td className="py-3 text-right font-mono text-white/80">{formatUSD(p.marketCap||p.fdv)}</td>
                      <td className="py-3">
                        <div className="flex items-center justify-end gap-2">
                          <a href={p.url} target="_blank" rel="noreferrer" className="text-[#14F195] hover:text-[#00FFA3]"><Rocket size={13}/></a>
                          <a href={p.url} target="_blank" rel="noreferrer" className="text-[#14F195] hover:text-[#00FFA3]"><BarChart3 size={13}/></a>
                          <button className="text-white/40 hover:text-[#14F195]"><Star size={13}/></button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Live Feed */}
          <div className="col-span-12 xl:col-span-4 rounded-2xl bg-[#050908] border border-[#14F195]/20 p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2"><Activity size={15} className="text-[#14F195]"/><span className="font-bold">Live Feed</span></div>
              <button className="text-xs text-white/50 flex items-center gap-1">All <ChevronDown size={12}/></button>
            </div>
            <div className="mt-3 space-y-2.5">
              {[
                {Icon:Rocket, color:'#14F195', title:'New Token Launched', sub:'$WAVE on Pump.fun', time:'2m'},
                {Icon:Bell, color:'#F59E0B', title:'Big Buy', sub:'$MOON 12.5 SOL', time:'4m'},
                {Icon:Waves, color:'#22C55E', title:'Migration Alert', sub:'$SHIP migrating to Raydium', time:'6m'},
                {Icon:Flame, color:'#EF4444', title:'Trending', sub:'$FEE +42%', time:'8m'},
                {Icon:Droplet, color:'#3B82F6', title:'New Liquidity', sub:'$CAT 85 SOL', time:'10m'},
              ].map((it, i) => (
                <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-white/[0.03] transition-colors">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0" style={{ background: `${it.color}22`, border: `1px solid ${it.color}55` }}>
                    <it.Icon size={14} style={{ color: it.color }}/>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-semibold">{it.title}</div>
                    <div className="text-[11px] text-white/50 truncate">{it.sub}</div>
                  </div>
                  <div className="text-[10px] text-white/40">{it.time}</div>
                </div>
              ))}
            </div>
            <a href="#" className="mt-3 block text-center text-xs text-[#14F195] hover:underline">View All →</a>
          </div>

          {/* Quick Actions */}
          <div className="col-span-12 xl:col-span-8 rounded-2xl bg-[#050908] border border-[#14F195]/20 p-5">
            <div className="flex items-center gap-2 mb-3"><Zap size={15} className="text-[#14F195]"/><span className="font-bold">Quick Actions</span></div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {[
                {Icon:Rocket, title:'Pump', sub:'New Launches'},
                {Icon:BarChart3, title:'DEX', sub:'Charts & Pairs'},
                {Icon:Compass, title:'Discover', sub:'Find Gems'},
                {Icon:Sparkles, title:'Launch', sub:'Create Token'},
                {Icon:Briefcase, title:'Portfolio', sub:'Track Assets'},
                {Icon:Coins, title:'Fee-Back', sub:'Earn While You Trade'},
              ].map((a, i) => (
                <button key={i} className="flex items-center gap-3 p-3 rounded-xl bg-gradient-to-br from-[#0a1a13] to-[#050908] border border-[#14F195]/15 hover:border-[#14F195]/45 transition-all">
                  <div className="w-9 h-9 rounded-lg bg-[#14F195]/12 border border-[#14F195]/30 flex items-center justify-center"><a.Icon size={16} className="text-[#14F195]"/></div>
                  <div className="text-left">
                    <div className="font-bold text-sm">{a.title}</div>
                    <div className="text-[10px] text-white/50">{a.sub}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Market Overview */}
          <div className="col-span-12 xl:col-span-4 rounded-2xl bg-[#050908] border border-[#14F195]/20 p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2"><BarChart3 size={15} className="text-[#14F195]"/><span className="font-bold">Market Overview</span></div>
              <div className="text-[10px] text-white/50 flex items-center gap-1">Live on Solana <span className="w-1.5 h-1.5 rounded-full bg-[#14F195] animate-pulse"/></div>
            </div>
            <div className="grid grid-cols-2 gap-4 mt-4">
              {[['Total Market Cap','$58.3B','+2.4%'],['24h Volume','$2.14B','+12.6%'],['Total Tokens','1.2M','+1.8%'],['Active Traders','245K','+6.1%']].map(([k,v,c],i)=>(
                <div key={i} className="p-3 rounded-xl bg-black/40 border border-white/5">
                  <div className="text-[10px] uppercase tracking-wider text-white/40">{k}</div>
                  <div className="mt-1 font-bold text-lg">{v}</div>
                  <div className="text-[10px] text-[#14F195]">{c}</div>
                </div>
              ))}
            </div>
          </div>
        </main>
      </div>

      <footer className="px-5 py-4 border-t border-[#14F195]/10 flex items-center justify-between text-xs text-white/50">
        <div>© 2026 FEELESS. All rights reserved.</div>
        <div>Same Transactions. <span className="text-[#14F195]">Zero Fees.</span> More For You.</div>
        <div className="flex gap-4"><a href="#" className="hover:text-white">Terms</a><a href="#" className="hover:text-white">Privacy</a><a href="#" className="hover:text-white">Support</a><a href="#" className="hover:text-white">Docs</a></div>
      </footer>

      <WalletModal open={walletOpen} onClose={() => setWalletOpen(false)} onConnect={setConnectedWallet}/>
    </div>
  );
}

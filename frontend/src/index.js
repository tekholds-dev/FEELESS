import React from "react";

import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@/index.css";
import App from "@/App";
import { cleanBrowserStorage } from "@/lib/storageHygiene";
import { installImageFallback } from "@/lib/imageFallback";
import { installTipLayer } from "@/lib/tipLayer";
import { installDeadClick } from "@/lib/deadClick";
import { installClipboard, installNoFocusZoom } from "@/lib/clipboard";
import { installDuo } from "@/lib/duo";
import { installPhoneShell } from "@/lib/phoneShell";
import "@/styles/phoneShell.css";
import { initTelegram } from "@/lib/telegram";
import "@/styles/duo.css";

cleanBrowserStorage();
initTelegram();   // 📲 only acts when Telegram opened FEELESS as a Mini App
installImageFallback();
installTipLayer();
installDeadClick();
installClipboard();
installNoFocusZoom();
installDuo();
installPhoneShell();

// Any link that leaves FEELESS opens in a new tab, even if a component forgot target=_blank.
document.addEventListener('click', event => {
  const a = event.target.closest?.('a[href]');
  if (a && a.origin && a.origin !== window.location.origin && !a.hasAttribute('download')) {
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
  }
}, true);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
    },
  },
});

const root = ReactDOM.createRoot(document.getElementById("root"));
import('./lib/openrouterConnect').then(m => m.finishOpenRouterConnect()).catch(() => {});   // 🔑 back from OpenRouter's approval page: seal the key, clear the one-time code
if (process.env.NODE_ENV === 'development' && window.location.pathname.startsWith('/dev/') && window.location.search.includes('look')) import('./lib/looks').then(m => m.applyLook(m.DEFAULT_LOOK));   // 🧪 any harness under the owner's look (?look)
if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/colony') {   // 🧪 the Colony on fixtures
  import('./dev/ColonyHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/rewards') {   // 🧪 the rewards dash on fixtures, signed in (src/dev/RewardsHarness.jsx)
  import('./dev/RewardsHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/hq') {   // 🧪 HQ on fixtures, no sign-in (src/dev/HqHarness.jsx)
  import('./dev/HqHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/gas') {   // 🧪 the fuel station gauges on fixtures
  import('./dev/GasHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/bridge') {   // 🧪 the bridge desk + its states on a fixture quote
  import('./dev/BridgeHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/chats') {   // 🧪 the shared chat box + the kit picker
  import('./dev/ChatsHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/themes') {   // 🧪 every chat theme + the picker
  import('./dev/ThemesHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/security') {   // 🧪 HQ › Security defence + stores + approvals on fixtures
  import('./dev/SecurityHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/war') {   // 🧪 the SEC-1 War Room on fixtures (src/dev/WarRoomHarness.jsx)
  import('./dev/WarRoomHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/block') {   // 🧪 a family's block + the Family Deck from the live backend (src/dev/BlockHarness.jsx)
  import('./dev/BlockHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/city') {   // 🧪 Fee City on a captured world + injected turf / raid (src/dev/CityHarness.jsx)
  import('./dev/CityHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/familia') {   // 🧪 Familia Wars / Board / Live on fixtures (src/dev/FamiliaHarness.jsx)
  import('./dev/FamiliaHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/pools') {   // 🧪 Pool Hub + deposit-here on fixtures (src/dev/PoolsHarness.jsx)
  import('./dev/PoolsHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/brain') {   // 🧪 the Brain + LM Studio rig on fixtures (src/dev/BrainHarness.jsx)
  import('./dev/BrainHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/cats') {   // 🧪 one agent's desk + REAL MODE proposals on a fixture cat (src/dev/CatHarness.jsx)
  import('./dev/CatHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/legal') {   // 🧪 LEGAL-1: accept window, Your data, HQ Legal & regions on fixtures (src/dev/LegalHarness.jsx)
  import('./dev/LegalHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/stash') {   // 🧪 COL-20 P3: the Stash + missions per dollar + record check, live backend (src/dev/StashHarness.jsx)
  import('./dev/StashHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/features') {   // 🧪 an agent's Features folder on fixtures (src/dev/FeaturesHarness.jsx)
  import('./dev/FeaturesHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/perps') {   // 🧪 the Perps money read + paper desk on fixtures (src/dev/PerpsHarness.jsx)
  import('./dev/PerpsHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/towers') {   // 🧪 Trench Towers on the live intake · ?cdc = the Crypto.com key door (src/dev/TowersHarness.jsx)
  import('./dev/TowersHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/broker') {   // 🧪 the Brokerage (Alpaca keys / linked accounts) on fixtures (src/dev/BrokerHarness.jsx)
  import('./dev/BrokerHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/money') {   // 🧪 the YOUR MONEY room on fixtures (src/dev/MoneyHarness.jsx)
  import('./dev/MoneyHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/fees') {   // 🧪 HQ › Core house fees on a fake call (src/dev/FeesHarness.jsx)
  import('./dev/FeesHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/launch') {   // 🧪 the launch wizard pre-filled, nothing signs (src/dev/LaunchHarness.jsx)
  import('./dev/LaunchHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/street') {   // 🧪 THE STREETS on a fixture read (src/dev/StreetHarness.jsx)
  import('./dev/StreetHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/crest') {   // 🧪 crest forge + family cards on fixtures (src/dev/CrestHarness.jsx)
  import('./dev/CrestHarness').then(m => root.render(<m.default />));
} else root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);

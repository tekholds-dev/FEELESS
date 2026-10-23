import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@/index.css";
import App from "@/App";
import { cleanBrowserStorage } from "@/lib/storageHygiene";
import { installImageFallback } from "@/lib/imageFallback";
import { installTipLayer } from "@/lib/tipLayer";
import { installDeadClick } from "@/lib/deadClick";

cleanBrowserStorage();
installImageFallback();
installTipLayer();
installDeadClick();

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
if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/hq') {   // 🧪 HQ on fixtures, no sign-in (src/dev/HqHarness.jsx)
  import('./dev/HqHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/gas') {   // 🧪 the fuel station gauges on fixtures
  import('./dev/GasHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/themes') {   // 🧪 every chat theme + the picker
  import('./dev/ThemesHarness').then(m => root.render(<m.default />));
} else if (process.env.NODE_ENV === 'development' && window.location.pathname === '/dev/security') {   // 🧪 HQ › Security defence + stores + approvals on fixtures
  import('./dev/SecurityHarness').then(m => root.render(<m.default />));
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

import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@/index.css";
import App from "@/App";
import { cleanBrowserStorage } from "@/lib/storageHygiene";

cleanBrowserStorage();

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
root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);

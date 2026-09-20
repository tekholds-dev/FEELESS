import React, { lazy, Suspense } from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { WalletProvider } from './hooks/useWallet';
import { WorkspaceProvider } from './hooks/useWorkspace';
import { Toaster } from './components/ui/sonner';
import './styles/terminal.css';
import './styles/command.css';
const Landing = lazy(() => import('./pages/Landing'));
const Terminal = lazy(() => import('./pages/Terminal'));

function App() {
  return (
    <div className="App">
      <WalletProvider><WorkspaceProvider><BrowserRouter>
        <Suspense fallback={<div className="app-loading" data-testid="app-loading"><span className="loader" />Opening FEELESS…</div>}><Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/terminal/*" element={<Terminal />} />
          <Route path="/whitepaper" element={<Navigate to="/terminal/whitepaper" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes></Suspense>
      </BrowserRouter><Toaster theme="dark" position="bottom-right" /></WorkspaceProvider></WalletProvider>
    </div>
  );
}

export default App;

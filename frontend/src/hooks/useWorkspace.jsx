import React, { createContext, useContext, useState } from 'react';
import { ECOSYSTEMS } from '../lib/ecosystems';
import { LAUNCHPADS, launchpadEcosystem } from '../lib/launchpads';
import { useWatchlist } from './useMarket';
const Context = createContext(null);
export const CONTEXTS = [...ECOSYSTEMS.filter(e => !e.isFeeless), ...LAUNCHPADS.map(launchpadEcosystem)];
export const WorkspaceProvider = ({ children }) => {
  const [id, update] = useState(() => {
    const saved = localStorage.getItem('feeless-ecosystem') || localStorage.getItem('feeless-default-ecosystem');
    return CONTEXTS.some(e => e.id === saved) ? saved : 'solana';
  });
  const [selectedPair, selectPair] = useState(null);
  const [alertPair, setAlertPair] = useState(null);
  const watch = useWatchlist();
  const ecosystem = CONTEXTS.find(e => e.id === id) || CONTEXTS[0];
  const setEcosystem = next => {
    if (!CONTEXTS.some(e => e.id === next)) return;
    update(next); localStorage.setItem('feeless-ecosystem', next);
  };
  return <Context.Provider value={{ ecosystem, setEcosystem, selectedPair, selectPair, alertPair, setAlertPair, ...watch }}>{children}</Context.Provider>;
};
export const useWorkspace = () => useContext(Context);
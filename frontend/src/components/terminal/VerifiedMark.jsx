import React from 'react';

// Blue check for FEELESS-verified identities (HQ, official accounts, and wallets HQ verifies).
export function VerifiedMark({ size = 18 }) {
  return <svg className="verified-mark" width={size} height={size} viewBox="0 0 24 24" aria-label="Verified by FEELESS" role="img"><title>Verified by FEELESS</title>
    <path fill="#1d9bf0" d="M22.5 12.5c0-1.58-.88-2.95-2.18-3.65.47-1.4.2-3.02-.9-4.12-1.1-1.1-2.72-1.37-4.12-.9C14.6 2.53 13.23 1.65 11.65 1.65s-2.95.88-3.65 2.18c-1.4-.47-3.02-.2-4.12.9-1.1 1.1-1.37 2.72-.9 4.12C1.68 9.55.8 10.92.8 12.5s.88 2.95 2.18 3.65c-.47 1.4-.2 3.02.9 4.12 1.1 1.1 2.72 1.37 4.12.9.7 1.3 2.07 2.18 3.65 2.18s2.95-.88 3.65-2.18c1.4.47 3.02.2 4.12-.9 1.1-1.1 1.37-2.72.9-4.12 1.3-.7 2.18-2.07 2.18-3.65z" />
    <path fill="#fff" d="M10.2 16.6 6.6 13l1.4-1.4 2.2 2.2 5.8-5.8 1.4 1.4z" /></svg>;
}

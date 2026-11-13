import React from 'react';
import { StashWeb } from '../components/command/StashWeb';

// 🧪 DEV ONLY (`/dev/stash`, never in a production build): the public Stash web with COL-20 P3 (verified missions per dollar + the daily
// record check), read from the live backend. ?day = the day theme.
export default function StashHarness() {
  if (new URLSearchParams(window.location.search).has('day')) document.body.classList.add('theme-day');
  return <main style={{ padding: 16, maxWidth: 900, margin: '0 auto' }}><StashWeb /></main>;
}

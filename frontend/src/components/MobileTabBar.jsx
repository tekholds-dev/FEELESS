import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Home, Flame, Repeat, ShieldCheck } from 'lucide-react';
import { FeeCatMark } from './FeeCatMark';

// Phone-only bottom tab bar: the five places people live, one thumb-tap away (hidden ≥ 761px).
const TABS = [['/', 'Home', Home, true], ['/terminal/chat', 'Trenches', Flame], ['/terminal/trade', 'Trade', Repeat], ['/terminal/reputation', 'Rep', ShieldCheck], ['/terminal/feecat', 'Fee', null]];

export function MobileTabBar() {
  if (useLocation().pathname.startsWith('/familia')) return null;   // 🌹 La Familia is its own app with its own dock
  return <nav className="mobile-tabbar" aria-label="Main">
    {TABS.map(([to, label, Icon, end]) => <NavLink key={to} to={to} end={end} className={({ isActive }) => (isActive ? 'active' : '')}>
      {Icon ? <Icon size={20} /> : <FeeCatMark size={22} animate={false} />}<span>{label}</span>
    </NavLink>)}
  </nav>;
}

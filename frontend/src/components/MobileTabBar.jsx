import React from 'react';
import { NavLink } from 'react-router-dom';
import { Home, Flame, Repeat, ShieldCheck } from 'lucide-react';
import { FeeCatMark } from './FeeCatMark';

// Phone-only bottom tab bar: the five places people live, one thumb-tap away (hidden ≥ 761px).
const TABS = [['/', 'Home', Home, true], ['/terminal/chat', 'Trenches', Flame], ['/terminal/trade', 'Trade', Repeat], ['/terminal/reputation', 'Rep', ShieldCheck], ['/terminal/feecat', 'Fee', null]];

export function MobileTabBar() {
  return <nav className="mobile-tabbar" aria-label="Main">
    {TABS.map(([to, label, Icon, end]) => <NavLink key={to} to={to} end={end} className={({ isActive }) => (isActive ? 'active' : '')}>
      {Icon ? <Icon size={20} /> : <FeeCatMark size={22} animate={false} />}<span>{label}</span>
    </NavLink>)}
  </nav>;
}

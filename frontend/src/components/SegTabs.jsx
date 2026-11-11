import React from 'react';
import { Tabs } from '@heroui/react';
import { Ic3Text } from '../lib/icon3d';

// 🗂 SITE-3: the one tab row (HeroUI Tabs: arrow keys, sliding indicator, tab roles). items = [[key, label, tip?, count?]];
// testid(key) names each tab; className adds the page's own layout (sticky, wrap). The page accent comes from --accent.
export default function SegTabs({ items, value, onChange, label, className = '', testid, style, rootTestid }) {
  return <Tabs selectedKey={value} onSelectionChange={k => onChange(String(k))} className={`seg-tabs ${className}`} aria-label={label} style={style} data-testid={rootTestid}>
    <Tabs.ListContainer><Tabs.List aria-label={label}>{items.map(([k, l, tip, n], i) => <Tabs.Tab key={k} id={k} style={{ '--i': i }} data-tip={tip || undefined} data-testid={testid ? testid(k) : undefined}>
      <Ic3Text text={l} />{n ? <em>{n}</em> : null}<Tabs.Indicator /></Tabs.Tab>)}</Tabs.List></Tabs.ListContainer></Tabs>;
}

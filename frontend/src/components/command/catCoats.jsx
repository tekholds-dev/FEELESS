import React from 'react';
import { FeeCatMark } from '../FeeCatMark';

// 🎨 THE COATS (FeeCat redo, 2026-10-23): 25 real coats — fur + accent + the pattern drawn on the head (stripes / spots / patch). The old list
// padded itself to 50 with "<name> Spots" copies of the same 25 colours; a cat saved under one of those names still resolves (`catByName`).
export const CAT_VARIATIONS = [
  ['Mint Mackerel', '#b9f4d7', '#087a58', 'stripes'], ['Midnight Patch', '#1c2930', '#f7d36b', 'patch'], ['Solaris', '#ffbf69', '#d94e41', 'spots'],
  ['Cloud Nine', '#f5f0e8', '#a9b9c8', 'patch'], ['Berry Socks', '#e78aa8', '#5b2b55', 'spots'], ['Lime Sprout', '#c9ee68', '#3e8e52', 'stripes'],
  ['Copper Tabby', '#c87842', '#713d27', 'stripes'], ['Bluebell', '#99b8ef', '#4b54a8', 'spots'], ['Tux Bloom', '#f4f4ec', '#171c25', 'patch'],
  ['Peach Fizz', '#ffc7a4', '#e55c72', 'spots'], ['Mossy', '#849c75', '#314a36', 'patch'], ['Lavender Loop', '#cbb8ed', '#6b54a5', 'stripes'],
  ['Neon Paws', '#66f2d0', '#734cf2', 'spots'], ['Caramel Dot', '#d99d59', '#8a4b35', 'patch'], ['Moonstone', '#c7d2d9', '#54616e', 'stripes'],
  ['Rosewater', '#f4b4be', '#9c3d65', 'spots'], ['Golden Hour', '#f1d36b', '#b36a2e', 'patch'], ['Inkblot', '#41485a', '#10141c', 'spots'],
  ['Cactus Cat', '#a4d58c', '#2a6a5b', 'stripes'], ['Creamsicle', '#ffe0a3', '#f08042', 'patch'], ['Orchid', '#df9ce8', '#763e9a', 'spots'],
  ['Raincoat', '#89c6d8', '#284f72', 'stripes'], ['Pistachio', '#d7e8a4', '#718e47', 'patch'], ['Firefly', '#e9ed72', '#574278', 'spots'],
  ['Paper Tiger', '#eee5d0', '#b87952', 'stripes'],
];

// Every FeeCat is Fee's animated rig in its own coat: same silhouette, blink and tail, different fur.
export const CatAvatar = ({ cat, large = false, gear = null, eyes = null, full = false, size = null, gesture = null }) => {
  const [name, fur, accent, pattern] = cat;
  return <span className={`feeless-cat-art ${large ? 'large' : ''}`}><FeeCatMark size={size || (large ? 120 : 56)} colors={[fur, accent]} pattern={pattern} gear={gear} eyes={eyes} full={full} gesture={gesture} label={`${name} Feeless Cat`} /></span>;
};


// pure: a saved cat's avatar name → its coat (a legacy "<name> Spots" → that coat with spots); unknown → the first coat
export function catByName(name) {
  const n = String(name || ''); const hit = CAT_VARIATIONS.find(c => c[0] === n); if (hit) return hit;
  const base = n.endsWith(' Spots') ? CAT_VARIATIONS.find(c => c[0] === n.slice(0, -6)) : null;
  return base ? [base[0], base[1], base[2], 'spots'] : CAT_VARIATIONS[0];
}

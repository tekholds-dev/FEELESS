import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { markOf, WalletMark } from './WalletPfp';

test('the same wallet always gets the same mark; two wallets differ; never blank', () => {
  const a = markOf('7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU'); const b = markOf('9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM');
  expect(markOf('7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU')).toEqual(a);
  expect(a.h1 === b.h1 && JSON.stringify(a.cells) === JSON.stringify(b.cells)).toBe(false);
  expect(renderToStaticMarkup(<WalletMark address="" />)).toContain('<svg');
});

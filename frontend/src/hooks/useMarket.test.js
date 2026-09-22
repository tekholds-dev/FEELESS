import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import useSWR from 'swr';
import { marketRequest } from '../lib/dexscreener';
import {
  FEED_CACHE_PREFIX,
  FEED_CACHE_TTL,
  readFeedCache,
  useMarket,
  writeFeedCache,
} from './useMarket';

jest.mock('../lib/dexscreener', () => ({
  marketRequest: jest.fn(),
  tokenKey: pair => `${pair.chainId}-${pair.baseToken?.address}`,
}));

jest.mock('swr', () => jest.fn());

const swrMock = useSWR;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function mountHook(path) {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  let value;
  act(() => root.render(<Probe path={path} onValue={next => { value = next; }} />));
  return { root, value: () => value };
}

function Probe({ path, onValue }) {
  onValue(useMarket(path, 0));
  return null;
}

beforeEach(() => {
  localStorage.clear();
  swrMock.mockReset();
  marketRequest.mockReset();
});

afterEach(() => {
  document.body.innerHTML = '';
});

test('removes feed cache entries older than fourteen days while retaining fresh entries', () => {
  const now = 1_700_000_000_000;
  localStorage.setItem(`${FEED_CACHE_PREFIX}/feed?kind=trending`, JSON.stringify({
    savedAt: now - FEED_CACHE_TTL - 1,
    data: { pairs: [{ pairAddress: 'old' }] },
  }));
  writeFeedCache('/feed?kind=new', { pairs: [{ pairAddress: 'fresh' }] }, now);

  expect(readFeedCache('/feed?kind=new', now).data.pairs[0].pairAddress).toBe('fresh');
  expect(localStorage.getItem(`${FEED_CACHE_PREFIX}/feed?kind=trending`)).toBeNull();
});

test('keeps visible rows during a live feed refresh and writes the refreshed response', async () => {
  const path = '/feed?kind=trending&chain=solana&page=1';
  const visibleRows = { pairs: [{ pairAddress: 'visible-row' }] };
  const refreshedRows = { pairs: [{ pairAddress: 'refreshed-row' }] };
  let fetcher;
  swrMock.mockImplementation((key, request, options) => {
    fetcher = request;
    expect(key).toBe(path);
    expect(options.keepPreviousData).toBe(true);
    return { data: visibleRows, error: null, isLoading: false, isValidating: true, mutate: jest.fn() };
  });
  marketRequest.mockResolvedValue(refreshedRows);

  const mounted = mountHook(path);
  expect(mounted.value().data).toEqual(visibleRows);
  expect(mounted.value().refreshing).toBe(true);

  await act(async () => {
    expect(await fetcher(path)).toEqual(refreshedRows);
  });
  expect(JSON.parse(localStorage.getItem(`${FEED_CACHE_PREFIX}${path}`)).data).toEqual(refreshedRows);
});

test('keeps the last usable feed snapshot when a later provider response is empty', async () => {
  const path = '/feed?kind=trending&chain=solana&page=1';
  const usableRows = { provider: 'DexScreener', pairs: [{ pairAddress: 'last-usable-pool' }] };
  const emptyRows = { provider: 'GeckoTerminal', pairs: [] };
  writeFeedCache(path, usableRows);
  let fetcher;
  swrMock.mockImplementation((key, request, options) => {
    fetcher = request;
    expect(key).toBe(path);
    expect(options.fallbackData).toEqual(usableRows);
    return { data: options.fallbackData, error: null, isLoading: false, isValidating: false, mutate: jest.fn() };
  });
  marketRequest.mockResolvedValue(emptyRows);

  const mounted = mountHook(path);
  await act(async () => {
    expect(await fetcher(path)).toEqual(emptyRows);
  });

  expect(mounted.value().data).toEqual(usableRows);
  expect(JSON.parse(localStorage.getItem(`${FEED_CACHE_PREFIX}${path}`)).data).toEqual(usableRows);
});
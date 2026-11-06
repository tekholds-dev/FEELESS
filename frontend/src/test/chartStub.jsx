import React from 'react';
// Jest has no canvas or layout. The road map and charts are checked in a real browser; here they render as an empty box with their test id.
export const Handle = () => null;
export const Position = { Top: 'top', Bottom: 'bottom', Left: 'left', Right: 'right' };
export const ReactFlow = () => <div data-testid="flow-stub" />;
const chart = { setOption() {}, resize() {}, dispose() {}, getZr: () => ({ on() {} }), containPixel: () => false, convertFromPixel: () => 0 };
export const init = () => chart; export const use = () => {};
export const LineChart = {}; export const GridComponent = {}; export const MarkLineComponent = {}; export const MarkPointComponent = {}; export const TooltipComponent = {}; export const CanvasRenderer = {};

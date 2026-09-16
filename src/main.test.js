import {describe,it,expect} from 'vitest';
describe('route configuration',()=>{it('does not provide a token default',()=>expect(import.meta.env.VITE_FEE_MINT || '').toBe('') )});

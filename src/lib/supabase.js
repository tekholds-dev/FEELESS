import { createClient } from '@supabase/supabase-js';

const url = import.meta.env.VITE_SUPABASE_URL;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const supabase = createClient(url, anonKey, {
  auth: { persistSession: true, autoRefreshToken: true },
  realtime: { params: { eventsPerSecond: 10 } },
});

export const FEE_MINT = '49MmWE8sgNjuw342Eu7tB9thsVFtvTfKigUw9KSppump';
export const FEECAT_MINT = 'AsX2abSJ2HqPqRxUbeYXE5R5ksrmUDz6BMGpg9mDpump';

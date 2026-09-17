import { createClient } from '@supabase/supabase-js';
import type { Database } from './types';
import { brokeredPreviewStorage } from './previewAuthStorage';
function createSupabaseClient(){const url=import.meta.env['VITE_SUPABASE_URL']||process.env['SUPABASE_URL'];const key=import.meta.env['VITE_SUPABASE_PUBLISHABLE_KEY']||process.env['SUPABASE_PUBLISHABLE_KEY'];if(!url||!key)throw new Error('Missing Supabase environment variables');return createClient<Database>(url,key,{auth:{storage:brokeredPreviewStorage(),persistSession:true,autoRefreshToken:true}})}
let _supabase:ReturnType<typeof createSupabaseClient>|undefined;
export const supabase=new Proxy({} as ReturnType<typeof createSupabaseClient>,{get(_,prop,receiver){if(!_supabase)_supabase=createSupabaseClient();return Reflect.get(_supabase,prop,receiver)}});

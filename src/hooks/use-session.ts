import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
export function useSession(){const [session,setSession]=useState<Session|null>(null);const [ready,setReady]=useState(false);useEffect(()=>{const {data}=supabase.auth.onAuthStateChange((_event,next)=>setSession(next));void supabase.auth.getSession().then(({data:current})=>{setSession(current.session);setReady(true)});return()=>data.subscription.unsubscribe()},[]);return{session,user:session?.user??null,ready}}
export type Profile={id:string;handle:string;display_name:string|null;bio:string|null;avatar_url:string|null;created_at:string};
export function useMyProfile(userId?:string){return useQuery({queryKey:["profile",userId],enabled:!!userId,queryFn:async()=>{const{data,error}=await supabase.from("profiles").select("*").eq("id",userId!).maybeSingle();if(error)throw error;return data as Profile|null}})}
export function useProfileByHandle(handle:string){return useQuery({queryKey:["profile-handle",handle],enabled:!!handle,queryFn:async()=>{const{data,error}=await supabase.from("profiles").select("*").eq("handle",handle).maybeSingle();if(error)throw error;return data as Profile|null}})}

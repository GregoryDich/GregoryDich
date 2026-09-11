import "server-only";

import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { supabaseConfigured, supabaseEnv } from "./env";

/** Cookie-backed Supabase client for server components, route handlers and server actions. */
export async function createClient() {
  const { url, anonKey } = supabaseEnv();
  const cookieStore = await cookies();
  return createServerClient(url, anonKey, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet) {
        try {
          for (const { name, value, options } of cookiesToSet) {
            cookieStore.set(name, value, options);
          }
        } catch {
          // Server components cannot write cookies; the middleware refreshes the session.
        }
      },
    },
  });
}

/**
 * Returns the signed-in user and the access token the API expects as Bearer token, or
 * null when there is no valid session. `getUser()` verifies the JWT with Supabase;
 * the token itself is then read from the session cookie.
 */
export async function getSessionUser() {
  // Without Supabase settings (a preview deployment before the project exists) every
  // page renders signed-out instead of failing to build.
  if (!supabaseConfigured()) return null;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return null;
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session?.access_token) return null;
  return { supabase, user, accessToken: session.access_token };
}

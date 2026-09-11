"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

type State = "unknown" | "anonymous" | "signed-in";

/** Header links that depend on the session; kept client-side so public pages stay static. */
export function AuthNav() {
  const [state, setState] = useState<State>("unknown");

  useEffect(() => {
    const supabase = createClient();
    let active = true;
    supabase.auth.getSession().then(({ data }) => {
      if (active) setState(data.session ? "signed-in" : "anonymous");
    });
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setState(session ? "signed-in" : "anonymous");
    });
    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, []);

  if (state === "signed-in") {
    return (
      <Link href="/account" className="btn btn-secondary">
        Account
      </Link>
    );
  }

  return (
    <div className={`flex items-center gap-2 ${state === "unknown" ? "opacity-0" : "opacity-100"} transition-opacity`}>
      <Link href="/login" className="btn btn-ghost hidden sm:inline-flex">
        Log in
      </Link>
      <Link href="/signup" className="btn btn-primary">
        Get started
      </Link>
    </div>
  );
}

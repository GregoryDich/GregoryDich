import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { AuthCard } from "@/components/AuthCard";
import { authErrorMessage } from "@/lib/auth-messages";
import { safeNext } from "@/lib/redirect";
import { getSessionUser } from "@/lib/supabase/server";
import { LoginForm } from "./LoginForm";

export const metadata: Metadata = {
  title: "Log in",
  robots: { index: false },
};

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ next?: string; error?: string }> }) {
  const { next, error } = await searchParams;
  const target = safeNext(next);
  if (await getSessionUser()) redirect(target);
  return (
    <AuthCard title="Log in" intro="Use the email and password you signed up with.">
      <LoginForm next={target} initialError={authErrorMessage(error)} />
    </AuthCard>
  );
}

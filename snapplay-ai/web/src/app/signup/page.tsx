import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { AuthCard } from "@/components/AuthCard";
import { brand } from "@/lib/brand";
import { safeNext } from "@/lib/redirect";
import { getSessionUser } from "@/lib/supabase/server";
import { SignupForm } from "./SignupForm";

export const metadata: Metadata = {
  title: "Create account",
  description: `Create a free ${brand.productName} account and get 3 credits. No card required.`,
  robots: { index: false },
};

export default async function SignupPage({ searchParams }: { searchParams: Promise<{ next?: string }> }) {
  const { next } = await searchParams;
  const target = safeNext(next);
  if (await getSessionUser()) redirect(target);
  const loginHref = target === "/account" ? "/login" : `/login?next=${encodeURIComponent(target)}`;
  return (
    <AuthCard title="Create your account" intro="3 free credits. No card. Sign in inside the plugin once it is installed.">
      <SignupForm loginHref={loginHref} />
    </AuthCard>
  );
}

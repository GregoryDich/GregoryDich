import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { AuthCard } from "@/components/AuthCard";
import { NewPasswordForm } from "./NewPasswordForm";

export const metadata: Metadata = {
  title: "Choose a new password",
  robots: { index: false },
};

/**
 * Recovery links that still carry a code or token hash are exchanged by the confirm
 * route handler (the only place that can write the session cookie) and come back here clean.
 */
export default async function NewPasswordPage({ searchParams }: { searchParams: Promise<{ code?: string; token_hash?: string }> }) {
  const { code, token_hash: tokenHash } = await searchParams;
  if (code) redirect(`/auth/confirm?code=${encodeURIComponent(code)}&type=recovery`);
  if (tokenHash) redirect(`/auth/confirm?token_hash=${encodeURIComponent(tokenHash)}&type=recovery`);
  return (
    <AuthCard title="Choose a new password" intro="Pick something long; a phrase works better than a word.">
      <NewPasswordForm />
    </AuthCard>
  );
}

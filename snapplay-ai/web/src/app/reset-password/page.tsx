import type { Metadata } from "next";
import Link from "next/link";
import { AuthCard } from "@/components/AuthCard";
import { authErrorMessage } from "@/lib/auth-messages";
import { ResetRequestForm } from "./ResetRequestForm";

export const metadata: Metadata = {
  title: "Reset password",
  robots: { index: false },
};

export default async function ResetPasswordPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const { error } = await searchParams;
  const message = authErrorMessage(error);
  return (
    <AuthCard
      title="Reset your password"
      intro={
        <>
          Enter your email and we will send a link to choose a new password. Remembered it?{" "}
          <Link href="/login" className="text-ink underline underline-offset-4">
            Log in
          </Link>
          .
        </>
      }
    >
      {message && (
        <p role="alert" className="alert alert-error mb-5">
          {message}
        </p>
      )}
      <ResetRequestForm />
    </AuthCard>
  );
}

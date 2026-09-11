import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { brand } from "@/lib/brand";
import { getSessionUser } from "@/lib/supabase/server";
import { NpsForm } from "./NpsForm";

export const metadata: Metadata = {
  title: "Your feedback",
  robots: { index: false, follow: false },
};

/** `?score=` comes prefilled from the email link; anything outside 0–10 is ignored. */
function parseScore(value: string | undefined): number | null {
  if (value === undefined || !/^\d{1,2}$/.test(value)) return null;
  const score = Number(value);
  return score >= 0 && score <= 10 ? score : null;
}

export default async function NpsPage({ searchParams }: { searchParams: Promise<{ score?: string }> }) {
  const { score } = await searchParams;
  const initialScore = parseScore(score);
  const session = await getSessionUser();
  if (!session) {
    const back = initialScore === null ? "/nps" : `/nps?score=${initialScore}`;
    redirect(`/login?next=${encodeURIComponent(back)}`);
  }
  return (
    <div className="mx-auto w-full max-w-xl px-5 py-16 sm:px-8 sm:py-24">
      <p className="eyebrow">Feedback</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight">One question, ten seconds.</h1>
      <p className="mt-2 text-sm text-ink-muted">
        One answer per person every 30 days. Nothing here is shared outside {brand.companyLegalName}.
      </p>
      <div className="card mt-8">
        <NpsForm initialScore={initialScore} />
      </div>
    </div>
  );
}

import type { Metadata } from "next";
import Link from "next/link";
import { releases } from "@/content/releases";
import { brand } from "@/lib/brand";
import { formatDate } from "@/lib/format";

export const metadata: Metadata = {
  title: "Changelog",
  description: `Every ${brand.productName} release, newest first.`,
};

export default function ChangelogPage() {
  return (
    <div className="container-prose py-16 sm:py-24">
      <p className="eyebrow">Changelog</p>
      <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">Releases</h1>
      <p className="mt-4 text-ink-muted">
        The plugin updates itself from these builds. The latest version is always on the{" "}
        <Link href="/download" className="text-ink underline underline-offset-4">
          download page
        </Link>
        .
      </p>
      <ol className="mt-12 space-y-12">
        {releases.map((release) => (
          <li key={release.version} id={`v${release.version}`}>
            <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
              <h2 className="font-mono text-2xl font-semibold">{release.version}</h2>
              <span className="text-sm text-ink-dim">{formatDate(release.date)}</span>
              <span className="text-sm text-ink-muted">{release.title}</span>
            </div>
            <ul className="mt-4 list-disc space-y-1.5 pl-5 text-ink-muted">
              {release.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </li>
        ))}
      </ol>
    </div>
  );
}

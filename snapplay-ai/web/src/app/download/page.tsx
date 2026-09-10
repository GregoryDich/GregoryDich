import type { Metadata } from "next";
import Link from "next/link";
import { latestRelease, releaseAssetUrl, releases } from "@/content/releases";
import { brand } from "@/lib/brand";
import { formatDate } from "@/lib/format";

export const metadata: Metadata = {
  title: "Download",
  description: `Download ${brand.productName} for macOS (VST3 and AU, Apple silicon and Intel) and Windows (VST3).`,
};

const REQUIREMENTS = [
  { platform: "macOS", items: ["macOS 12 Monterey or later", "Apple silicon or Intel (universal build)", "A 64-bit VST3 or AU host"] },
  { platform: "Windows", items: ["Windows 10 or 11, 64-bit", "A 64-bit VST3 host"] },
  { platform: "Both", items: ["An internet connection while processing clips", "About 200 MB of disk space", `A ${brand.productName} account (free)`] },
];

export default function DownloadPage() {
  const release = latestRelease;
  return (
    <div className="container-page py-16 sm:py-24">
      <div className="max-w-2xl">
        <p className="eyebrow">Download</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">{brand.productName} {release.version}</h1>
        <p className="mt-4 text-lg text-ink-muted">
          Released {formatDate(release.date)}. One installer per platform, every plugin format included.
        </p>
      </div>

      <div className="mt-12 grid gap-4 md:grid-cols-2">
        <DownloadCard
          platform="macOS"
          formats="VST3 + AU · Apple silicon and Intel"
          fileLabel=".pkg installer"
          href={releaseAssetUrl(release, "macos")}
        />
        <DownloadCard platform="Windows" formats="VST3 · 64-bit" fileLabel=".exe installer" href={releaseAssetUrl(release, "windows")} />
      </div>

      <div className="alert alert-info mt-6">
        After installing, open the plugin in your DAW and sign in with the account you created here. Your credits — including
        the three free ones — are attached to the account, not the machine.{" "}
        <Link href="/signup" className="text-ink underline underline-offset-4">
          Create an account
        </Link>
        .
      </div>

      <section className="mt-16 grid gap-10 md:grid-cols-2" aria-labelledby="requirements">
        <div>
          <h2 id="requirements" className="text-2xl font-semibold tracking-tight">
            System requirements
          </h2>
          <dl className="mt-6 space-y-5">
            {REQUIREMENTS.map((group) => (
              <div key={group.platform}>
                <dt className="text-sm font-semibold text-ink">{group.platform}</dt>
                <dd>
                  <ul className="mt-1.5 space-y-1 text-sm text-ink-muted">
                    {group.items.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </dd>
              </div>
            ))}
          </dl>
        </div>
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Install locations</h2>
          <p className="mt-2 text-sm text-ink-muted">The installers use the standard folders your DAW already scans.</p>
          <dl className="mt-6 space-y-4 text-sm">
            <div>
              <dt className="font-semibold">macOS VST3</dt>
              <dd className="mt-1">
                <code className="kbd">/Library/Audio/Plug-Ins/VST3/</code>
              </dd>
            </div>
            <div>
              <dt className="font-semibold">macOS AU</dt>
              <dd className="mt-1">
                <code className="kbd">/Library/Audio/Plug-Ins/Components/</code>
              </dd>
            </div>
            <div>
              <dt className="font-semibold">Windows VST3</dt>
              <dd className="mt-1">
                <code className="kbd">C:\Program Files\Common Files\VST3\</code>
              </dd>
            </div>
          </dl>
          <p className="mt-4 text-sm text-ink-dim">
            If your DAW does not list the plugin after installing, rescan plugins; on macOS, Logic and GarageBand may need a
            restart to register the AU.
          </p>
        </div>
      </section>

      <section className="mt-16" aria-labelledby="changelog">
        <div className="flex items-end justify-between gap-4">
          <h2 id="changelog" className="text-2xl font-semibold tracking-tight">
            What&apos;s new
          </h2>
          <Link href="/changelog" className="btn btn-ghost">
            Full changelog →
          </Link>
        </div>
        <ul className="mt-6 space-y-6">
          {releases.slice(0, 3).map((entry) => (
            <li key={entry.version} className="border-t border-line pt-5">
              <p className="text-sm text-ink-dim">
                <span className="font-mono text-ink">{entry.version}</span> · {formatDate(entry.date)} · {entry.title}
              </p>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink-muted">
                {entry.notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function DownloadCard({ platform, formats, fileLabel, href }: { platform: string; formats: string; fileLabel: string; href: string }) {
  return (
    <div className="card flex flex-col">
      <h2 className="text-2xl font-semibold tracking-tight">{platform}</h2>
      <p className="mt-1 text-sm text-ink-muted">{formats}</p>
      <div className="mt-8 flex-1" />
      <a href={href} className="btn btn-primary btn-lg w-full" download>
        Download for {platform}
      </a>
      <p className="mt-3 text-center text-xs text-ink-dim">
        {fileLabel} · version {latestRelease.version}
      </p>
    </div>
  );
}

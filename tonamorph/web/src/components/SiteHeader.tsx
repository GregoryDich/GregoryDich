import Link from "next/link";
import { AuthNav } from "./AuthNav";
import { Wordmark } from "./Logo";

const NAV = [
  { href: "/pricing", label: "Pricing" },
  { href: "/download", label: "Download" },
  { href: "/changelog", label: "Changelog" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-line/80 bg-bg/80 backdrop-blur">
      <div className="container-page flex h-16 items-center justify-between gap-6">
        <Wordmark />
        <nav aria-label="Main" className="hidden items-center gap-7 text-sm text-ink-muted md:flex">
          {NAV.map((item) => (
            <Link key={item.href} href={item.href} className="transition-colors hover:text-ink">
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          <nav aria-label="Main (compact)" className="flex items-center gap-4 text-sm text-ink-muted md:hidden">
            <Link href="/pricing" className="hover:text-ink">
              Pricing
            </Link>
            <Link href="/download" className="hover:text-ink">
              Download
            </Link>
          </nav>
          <AuthNav />
        </div>
      </div>
    </header>
  );
}

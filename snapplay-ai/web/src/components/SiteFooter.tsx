import Link from "next/link";
import { brand } from "@/lib/brand";
import { LEGAL_DOCUMENTS, LEGAL_SLUGS } from "@/lib/legal";
import { LogoMark } from "./Logo";

const PRODUCT_LINKS = [
  { href: "/pricing", label: "Pricing" },
  { href: "/download", label: "Download" },
  { href: "/changelog", label: "Changelog" },
  { href: "/#faq", label: "FAQ" },
];

const ACCOUNT_LINKS = [
  { href: "/signup", label: "Create account" },
  { href: "/login", label: "Log in" },
  { href: "/account", label: "Account" },
];

export function SiteFooter() {
  const year = new Date().getUTCFullYear();
  return (
    <footer className="mt-24 border-t border-line">
      <div className="container-page grid gap-10 py-14 md:grid-cols-[1.5fr_1fr_1fr_1fr]">
        <div className="space-y-4">
          <div className="flex items-center gap-2.5">
            <LogoMark />
            <span className="font-semibold">{brand.productName}</span>
          </div>
          <p className="max-w-xs text-sm text-ink-muted">{brand.tagline}</p>
          <p className="text-sm text-ink-dim">
            <a href={`mailto:${brand.supportEmail}`} className="hover:text-ink">
              {brand.supportEmail}
            </a>
          </p>
        </div>
        <FooterColumn title="Product" links={PRODUCT_LINKS} />
        <FooterColumn title="Account" links={ACCOUNT_LINKS} />
        <FooterColumn
          title="Legal"
          links={LEGAL_SLUGS.map((slug) => ({ href: `/legal/${slug}`, label: LEGAL_DOCUMENTS[slug].title }))}
        />
      </div>
      <div className="border-t border-line">
        <div className="container-page flex flex-col gap-2 py-6 text-xs text-ink-dim sm:flex-row sm:items-center sm:justify-between">
          <p>
            © {year} {brand.companyLegalName}. All rights reserved.
          </p>
          <p>Purchases are processed by {brand.merchantOfRecord} as merchant of record.</p>
        </div>
      </div>
    </footer>
  );
}

function FooterColumn({ title, links }: { title: string; links: { href: string; label: string }[] }) {
  return (
    <nav aria-label={title}>
      <h2 className="mb-4 text-xs font-semibold tracking-[0.18em] text-ink-dim uppercase">{title}</h2>
      <ul className="space-y-2.5 text-sm">
        {links.map((link) => (
          <li key={link.href}>
            <Link href={link.href} className="text-ink-muted transition-colors hover:text-ink">
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

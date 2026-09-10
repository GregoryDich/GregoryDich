import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { AnchorHTMLAttributes } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { brand } from "@/lib/brand";
import { LEGAL_DOCUMENTS, LEGAL_SLUGS, availableLegalSlugs, isLegalSlug, loadLegalDocument } from "@/lib/legal";

export const dynamicParams = false;
export const dynamic = "force-static";

export function generateStaticParams(): { slug: string }[] {
  const available = availableLegalSlugs();
  const missing = LEGAL_SLUGS.filter((slug) => !available.includes(slug));
  if (missing.length > 0) {
    console.warn(`[legal] source files missing for: ${missing.join(", ")} — those pages are not built.`);
  }
  return available.map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  if (!isLegalSlug(slug)) return {};
  return {
    title: LEGAL_DOCUMENTS[slug].title,
    description: `${LEGAL_DOCUMENTS[slug].title} for ${brand.productName}.`,
  };
}

function MarkdownLink({ href = "", children, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement>) {
  const external = /^[a-z]+:/i.test(href) && !href.startsWith("mailto:");
  return (
    <a href={href} {...rest} {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}>
      {children}
    </a>
  );
}

export default async function LegalPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  if (!isLegalSlug(slug)) notFound();
  const document = loadLegalDocument(slug);
  if (!document) notFound();

  return (
    <div className="container-prose py-12 sm:py-16">
      <nav aria-label="Legal documents" className="mb-10 flex flex-wrap gap-x-5 gap-y-2 text-sm">
        {LEGAL_SLUGS.map((item) => (
          <Link
            key={item}
            href={`/legal/${item}`}
            aria-current={item === slug ? "page" : undefined}
            className={item === slug ? "text-ink underline underline-offset-4" : "text-ink-muted hover:text-ink"}
          >
            {LEGAL_DOCUMENTS[item].title}
          </Link>
        ))}
      </nav>
      <article className="legal-prose">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ a: MarkdownLink }}>
          {document.markdown}
        </ReactMarkdown>
      </article>
    </div>
  );
}

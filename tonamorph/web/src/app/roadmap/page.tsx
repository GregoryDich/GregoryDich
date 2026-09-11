import type { Metadata } from "next";
import Link from "next/link";
import { roadmap } from "@/content/roadmap";
import { brand } from "@/lib/brand";

export const metadata: Metadata = {
  title: "Roadmap",
  description: `What is being built for ${brand.productName} now, next and later.`,
};

export default function RoadmapPage() {
  return (
    <div className="container-page py-16 sm:py-24">
      <div className="max-w-2xl">
        <p className="eyebrow">Roadmap</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">Now, next, later.</h1>
        <p className="mt-4 text-lg text-ink-muted">
          What is being built, in the order it is coming. Dates arrive when the work does; the{" "}
          <Link href="/changelog" className="text-ink underline underline-offset-4">
            changelog
          </Link>{" "}
          records what shipped. Have a request? Write to{" "}
          <a href={`mailto:${brand.supportEmail}`} className="text-ink underline underline-offset-4">
            {brand.supportEmail}
          </a>
          .
        </p>
      </div>
      <div className="mt-12 grid gap-6 md:grid-cols-3">
        {roadmap.map((column) => (
          <section key={column.id} className="card" aria-labelledby={`roadmap-${column.id}`}>
            <h2 id={`roadmap-${column.id}`} className="text-xl font-semibold">
              {column.title}
            </h2>
            <p className="mt-1 text-sm text-ink-dim">{column.intro}</p>
            <ul className="mt-5 space-y-4">
              {column.items.map((item) => (
                <li key={item.title} className="border-t border-line pt-4">
                  <h3 className="font-medium">{item.title}</h3>
                  <p className="mt-1 text-sm text-ink-muted">{item.body}</p>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}

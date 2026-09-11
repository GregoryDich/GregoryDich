"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { attributionQuery } from "@/lib/attribution";

/** A link that carries the page's `ref` / `utm_*` parameters along, so attribution needs no storage. */
export function AttributedLink({ href, className, children }: { href: string; className?: string; children: ReactNode }) {
  const [target, setTarget] = useState(href);

  useEffect(() => {
    const query = attributionQuery(window.location.search);
    if (!query) return;
    const [path, hash] = href.split("#");
    const separator = path?.includes("?") ? "&" : "?";
    setTarget(`${path}${separator}${query}${hash ? `#${hash}` : ""}`);
  }, [href]);

  return (
    <Link href={target} className={className}>
      {children}
    </Link>
  );
}

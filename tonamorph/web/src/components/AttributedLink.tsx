"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { attributionQuery } from "@/lib/attribution";
import { track, type CtaLocation } from "@/lib/track";

/**
 * A link that carries the page's `ref` / `utm_*` parameters along, so attribution needs
 * no storage. With `cta` and `location` set, a click also reports `cta_clicked`.
 */
export function AttributedLink({
  href,
  className,
  children,
  cta,
  location,
}: {
  href: string;
  className?: string;
  children: ReactNode;
  cta?: string;
  location?: CtaLocation;
}) {
  const [target, setTarget] = useState(href);

  useEffect(() => {
    const query = attributionQuery(window.location.search);
    if (!query) return;
    const [path, hash] = href.split("#");
    const separator = path?.includes("?") ? "&" : "?";
    setTarget(`${path}${separator}${query}${hash ? `#${hash}` : ""}`);
  }, [href]);

  return (
    <Link href={target} className={className} onClick={cta && location ? () => track("cta_clicked", { cta, location }) : undefined}>
      {children}
    </Link>
  );
}

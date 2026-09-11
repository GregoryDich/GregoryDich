"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { track, type CtaLocation } from "@/lib/track";

/** A link that reports `cta_clicked` (no attribution parameters; see AttributedLink for those). */
export function TrackedLink({
  href,
  cta,
  location,
  className,
  children,
  external = false,
}: {
  href: string;
  cta: string;
  location: CtaLocation;
  className?: string;
  children: ReactNode;
  /** Plain anchor (checkout URLs built by the API, mailto) instead of a Next link. */
  external?: boolean;
}) {
  const onClick = () => track("cta_clicked", { cta, location });
  if (external) {
    return (
      <a href={href} className={className} rel="noopener" onClick={onClick}>
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className={className} onClick={onClick}>
      {children}
    </Link>
  );
}

import Link from "next/link";
import { brand } from "@/lib/brand";

export function LogoMark({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" className={className} fill="none">
      <rect x="1" y="1" width="30" height="30" rx="8" className="fill-accent" />
      <path
        d="M8 21V11l5 5 3-3 4 4 4-6v10"
        stroke="#14100a"
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Wordmark({ href = "/" }: { href?: string }) {
  return (
    <Link href={href} className="inline-flex items-center gap-2.5 text-ink" aria-label={`${brand.productName} home`}>
      <LogoMark />
      <span className="text-[15px] font-semibold tracking-tight">{brand.productName}</span>
    </Link>
  );
}

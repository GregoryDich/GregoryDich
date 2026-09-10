import type { ReactNode } from "react";

export function AuthCard({ title, intro, children }: { title: string; intro?: ReactNode; children: ReactNode }) {
  return (
    <div className="container-narrow py-16 sm:py-24">
      <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
      {intro && <div className="mt-2 text-sm text-ink-muted">{intro}</div>}
      <div className="card mt-8">{children}</div>
    </div>
  );
}

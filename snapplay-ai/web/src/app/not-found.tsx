import Link from "next/link";

export default function NotFound() {
  return (
    <div className="container-narrow py-24 text-center">
      <p className="eyebrow">404</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight">That page is not here.</h1>
      <p className="mt-3 text-ink-muted">The link may be old, or the page may have moved.</p>
      <div className="mt-8 flex justify-center gap-3">
        <Link href="/" className="btn btn-primary">
          Back to the start
        </Link>
        <Link href="/download" className="btn btn-secondary">
          Download
        </Link>
      </div>
    </div>
  );
}

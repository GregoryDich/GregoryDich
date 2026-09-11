import { HOW_IT_WORKS } from "@/content/landing";

/** The "Drop. Play. Drag." trio, rendered identically on the landing and referral pages. */
export function HowItWorksSteps() {
  return (
    <ol className="mt-10 grid gap-6 md:grid-cols-3">
      {HOW_IT_WORKS.map((step) => (
        <li key={step.n} className="card">
          <span className="font-mono text-sm text-accent">{step.n}</span>
          <h3 className="mt-3 text-xl font-semibold">{step.title}</h3>
          <p className="mt-2 text-sm leading-relaxed text-ink-muted">{step.body}</p>
        </li>
      ))}
    </ol>
  );
}

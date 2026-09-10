import Link from "next/link";
import { DemoVideo } from "@/components/DemoVideo";
import { staticPlans, planCopy } from "@/content/pricing";
import { brand } from "@/lib/brand";
import { formatUsd } from "@/lib/format";

const STEPS = [
  {
    n: "01",
    title: "Drop a clip",
    body: "Drag any audio file — a loop, a sample, a phone recording, a full mix — onto the plugin. Up to 60 seconds, FLAC, WAV, MP3, OGG or AIFF.",
  },
  {
    n: "02",
    title: "The AI splits it",
    body: `${brand.productName} separates bass, drums, synth and vocals in the cloud, transcribes them to MIDI and detects key, tempo and downbeats. About two seconds.`,
  },
  {
    n: "03",
    title: "Play it",
    body: "Each stem lands in a sampler under your fingers, transposed to your root note. Drag the .mid — or .fsc for FL Studio — straight onto your DAW timeline.",
  },
];

const FEATURES = [
  {
    title: "Four stems, one drop",
    body: "Bass, drums, synth and vocals separated with a state-of-the-art model, each with its own level, envelope and root note.",
  },
  {
    title: "MIDI you can edit",
    body: "Every melodic stem comes back as a MIDI track with real note starts, lengths and velocities. Change the notes, keep the sound.",
  },
  {
    title: "Key and BPM detected",
    body: "Root, mode, tempo and beat grid are read from the clip so what you play lands in tune and on the grid.",
  },
  {
    title: "Scale-Lock",
    body: "Snap incoming notes to the detected scale, or force major, minor or pentatonic. Wrong notes stop being possible.",
  },
  {
    title: "Drum kit mode",
    body: "Drum hits are sliced on transients and laid out from C1 upwards. Finger-drum the original groove or write a new one.",
  },
  {
    title: "FL Studio and Ableton ready",
    body: "VST3 on macOS and Windows, AU on macOS. Drag-and-drop exports to the timeline, including FL Studio score files.",
  },
];

const FAQ = [
  {
    q: "Does it work offline?",
    a: "No. The separation and transcription run on cloud GPUs — that is how a 30-second clip comes back in about two seconds. Once a clip has been processed, playing it in the plugin needs no connection.",
  },
  {
    q: "Which audio formats can I drop?",
    a: "FLAC, WAV, MP3, OGG and AIFF, up to 10 MB and 60 seconds per clip. Longer files are trimmed to the first 60 seconds.",
  },
  {
    q: "Do you keep my audio?",
    a: "Your upload and the generated stems and MIDI are deleted from our servers 24 hours after processing. We never train models on your audio.",
  },
  {
    q: "Who owns the output?",
    a: "You do. Everything the service generates from your clip is yours, in the same way your clip was yours. Only upload audio you have the rights to.",
  },
  {
    q: "What is a credit?",
    a: "One credit is one processed clip. Every account starts with three free credits; a 50-credit pack is $9 and never expires; the monthly plan gives you 60 credits per month for $7.99.",
  },
  {
    q: "Which DAWs are supported?",
    a: "Any host that loads VST3 plugins on Windows or macOS, or AU on macOS — Ableton Live, FL Studio, Logic Pro, Cubase, Studio One, Bitwig, Reaper and more.",
  },
];

export default function HomePage() {
  const plans = staticPlans;
  return (
    <>
      <section className="container-page pt-16 pb-12 sm:pt-24 sm:pb-16">
        <div className="max-w-3xl">
          <p className="eyebrow">VST3 · AU · macOS · Windows</p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight text-balance sm:text-6xl">
            Turn any track into a playable instrument in 2 seconds.
          </h1>
          <p className="mt-6 max-w-2xl text-lg text-ink-muted">
            Drop a clip. {brand.productName} splits it into stems and MIDI in the cloud and hands you a sampler you can play from
            your keyboard — in key, on tempo, inside your DAW.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link href="/signup" className="btn btn-primary btn-lg">
              Start free — 3 credits, no card
            </Link>
            <Link href="/download" className="btn btn-secondary btn-lg">
              Download the plugin
            </Link>
          </div>
        </div>
        <div className="mt-14">
          <DemoVideo />
        </div>
      </section>

      <section className="container-page py-16 sm:py-24" aria-labelledby="how">
        <p className="eyebrow">How it works</p>
        <h2 id="how" className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
          Three steps. No sampling chores.
        </h2>
        <ol className="mt-10 grid gap-6 md:grid-cols-3">
          {STEPS.map((step) => (
            <li key={step.n} className="card">
              <span className="font-mono text-sm text-accent">{step.n}</span>
              <h3 className="mt-3 text-xl font-semibold">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-muted">{step.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="border-y border-line bg-surface/40 py-16 sm:py-24" aria-labelledby="features">
        <div className="container-page">
          <p className="eyebrow">What you get</p>
          <h2 id="features" className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
            Built for the moment an idea hits.
          </h2>
          <ul className="mt-10 grid gap-x-10 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((feature) => (
              <li key={feature.title} className="border-t border-line pt-5">
                <h3 className="font-semibold">{feature.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-muted">{feature.body}</p>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="container-page py-16 sm:py-24" aria-labelledby="pricing">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="eyebrow">Pricing</p>
            <h2 id="pricing" className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
              One credit, one clip.
            </h2>
          </div>
          <Link href="/pricing" className="btn btn-ghost">
            Full pricing →
          </Link>
        </div>
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {plans.map((plan) => {
            const copy = planCopy[plan.id];
            return (
              <Link
                key={plan.id}
                href="/pricing"
                className={`card block transition-colors hover:border-line-strong ${copy?.highlight ? "border-accent/60" : ""}`}
              >
                <p className="text-sm text-ink-muted">{plan.name}</p>
                <p className="mt-2 text-3xl font-semibold tracking-tight">
                  {formatUsd(plan.price_usd)}
                  {plan.interval && <span className="text-base font-normal text-ink-dim"> / {plan.interval}</span>}
                </p>
                <p className="mt-1 text-sm text-ink-muted">
                  {plan.credits} credits{plan.interval ? ` every ${plan.interval}` : plan.id === "free" ? " at signup" : ", never expire"}
                </p>
              </Link>
            );
          })}
        </div>
      </section>

      <section id="faq" className="container-page py-16 sm:py-24" aria-labelledby="faq-title">
        <p className="eyebrow">FAQ</p>
        <h2 id="faq-title" className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
          Questions, answered.
        </h2>
        <div className="mt-10 divide-y divide-line border-y border-line">
          {FAQ.map((item) => (
            <details key={item.q} className="group py-5">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-medium">
                {item.q}
                <span aria-hidden="true" className="text-ink-dim transition-transform group-open:rotate-45">
                  +
                </span>
              </summary>
              <p className="mt-3 max-w-3xl text-sm leading-relaxed text-ink-muted">{item.a}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="container-page pb-8">
        <div className="card flex flex-col items-start gap-6 border-accent/40 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">Three clips on us.</h2>
            <p className="mt-1 text-ink-muted">Create an account, install the plugin, sign in inside it. No card required.</p>
          </div>
          <Link href="/signup" className="btn btn-primary btn-lg">
            Create free account
          </Link>
        </div>
      </section>
    </>
  );
}

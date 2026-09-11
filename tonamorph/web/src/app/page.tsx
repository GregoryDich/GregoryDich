import Link from "next/link";
import { AttributedLink } from "@/components/AttributedLink";
import { DemoVideo } from "@/components/DemoVideo";
import { WatchDemoButton } from "@/components/WatchDemoButton";
import { SPEED_CLAIM } from "@/content/performance";
import { PRICING_HEADLINE } from "@/content/pricing";
import { proofQuotes } from "@/content/proof";
import { brand } from "@/lib/brand";

const OLD_WAY = ["Upload", "Wait", "Download", "Re-import", "Slice", "Re-pitch"];
const NEW_WAY = ["Drop", "Play", "Drag"];

const STEPS = [
  { n: "1", title: "Drop", body: "Drop any clip up to 60 s." },
  { n: "2", title: "Play", body: "Bass, drums, synth and vocals arrive mapped across your keyboard, locked to the detected key." },
  { n: "3", title: "Drag", body: "Drag the .mid or .fsc into your piano roll." },
];

const COMPATIBILITY = ["FL Studio 21.2+", "Ableton Live 12", "Logic Pro 11 (AU)", "Windows", "macOS"];

const FAQ = [
  {
    q: "Which audio can I morph?",
    a: "Only audio you hold the rights to: your own recordings, loops you licensed, samples you are cleared to use. Your upload and the stems and MIDI made from it are deleted from our servers within 24 hours, and we never train models on your audio.",
  },
  {
    q: "Does it work offline?",
    a: "Morphing needs a connection: separation and transcription run on cloud GPUs. Once a clip is morphed, playing it from your keyboard and dragging the MIDI out need no connection.",
  },
  {
    q: "What if a morph fails or is unusable?",
    a: `A failed morph is never charged; it comes back to your balance automatically. If a morph finishes but is unusable, that morph is refunded: write to ${brand.supportEmail} with roughly when it ran and what went wrong. Money refunds follow the refund policy, including a full refund of an unused pack within 14 days.`,
  },
  {
    q: "What is a morph?",
    a: "One morph is one clip up to 60 s turned into stems, MIDI, key and BPM. Every account starts with three. 50 more are $9, once, and never expire; the monthly plan gives you 60 a month for $7.99 and they reset monthly.",
  },
  {
    q: "Which formats can I drop?",
    a: "FLAC, WAV, MP3, OGG and AIFF, up to 10 MB and 60 seconds per clip. Longer files are trimmed to the first 60 seconds.",
  },
  {
    q: "Which DAWs are supported?",
    a: "FL Studio 21.2 and later, Ableton Live 12 and Logic Pro 11 are the hosts we test on. Any host that loads VST3 on Windows or macOS, or AU on macOS, should work too: Cubase, Studio One, Bitwig, Reaper and more.",
  },
];

export default function HomePage() {
  return (
    <>
      <section className="container-page pt-16 pb-12 sm:pt-24 sm:pb-16" aria-labelledby="hero">
        <div className="max-w-3xl">
          <p className="eyebrow">VST3 · AU · macOS · Windows</p>
          <h1 id="hero" className="mt-4 text-4xl font-semibold tracking-tight text-balance sm:text-6xl">
            {brand.tagline}
          </h1>
          <p className="mt-6 max-w-2xl text-lg text-ink-muted">
            {brand.productName} turns any audio into a playable instrument inside FL Studio and Ableton: stems, MIDI and key in
            seconds. Drop a clip, play it on your keys, drag the MIDI out.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <AttributedLink href="/signup" className="btn btn-primary btn-lg" cta="get_free_morphs" location="hero">
              Get 3 free morphs
            </AttributedLink>
            <WatchDemoButton className="btn btn-secondary btn-lg" />
          </div>
          <p className="mt-3 text-sm text-ink-dim">No card.</p>
        </div>
        <div id="demo" className="mt-14 scroll-mt-24">
          <DemoVideo />
        </div>
      </section>

      <section className="container-page py-16 sm:py-24" aria-labelledby="problem">
        <p className="eyebrow">The problem</p>
        <h2 id="problem" className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
          The slow part is not sampling. It&apos;s leaving the DAW.
        </h2>
        <p className="mt-4 max-w-2xl text-lg text-ink-muted">Upload, wait, download, re-import, slice, re-pitch. Four apps for one melody.</p>
        <div className="mt-10 space-y-4" aria-label="Timeline: the old way against morphing">
          <Timeline label="Web tools and splitters" steps={OLD_WAY} muted />
          <Timeline label={brand.productName} steps={NEW_WAY} />
        </div>
      </section>

      <section className="border-y border-line bg-surface/40 py-16 sm:py-24" aria-labelledby="how">
        <div className="container-page">
          <p className="eyebrow">How it works</p>
          <h2 id="how" className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
            Drop. Play. Drag.
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
        </div>
      </section>

      <section className="container-page py-16 sm:py-24" aria-labelledby="speed">
        <div className="grid gap-10 md:grid-cols-[1.2fr_1fr] md:items-start">
          <div>
            <p className="eyebrow">Speed</p>
            <h2 id="speed" className="mt-3 text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
              {SPEED_CLAIM.headline}
            </h2>
            {SPEED_CLAIM.measurement && <p className="mt-3 text-sm text-ink-dim">{SPEED_CLAIM.measurement}</p>}
            <p className="mt-4 max-w-2xl text-lg text-ink-muted">
              About two seconds of processing on our GPU tier (pipeline budget 1.8 s on an A10G). Drop to playable is usually
              5–15 s warm; the first morph after a long idle takes longer.
            </p>
            <Link href="/status" className="mt-6 inline-block text-sm text-ink underline underline-offset-4">
              Live numbers from the last 24 hours →
            </Link>
          </div>
          <dl className="card grid grid-cols-2 gap-6 text-sm">
            <div>
              <dt className="text-ink-dim">GPU processing</dt>
              <dd className="mt-1 text-2xl font-semibold tracking-tight">≈ 2 s</dd>
            </div>
            <div>
              <dt className="text-ink-dim">Drop to playable, warm</dt>
              <dd className="mt-1 text-2xl font-semibold tracking-tight">5–15 s</dd>
            </div>
            <div className="col-span-2 text-ink-dim">Includes upload, queue and download on a typical connection. Cold starts are slower.</div>
          </dl>
        </div>
      </section>

      <section className="border-y border-line bg-surface/40 py-16 sm:py-24" aria-labelledby="not-a-splitter">
        <div className="container-page">
          <p className="eyebrow">Not a splitter</p>
          <h2 id="not-a-splitter" className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
            FL Studio and Logic already split stems. {brand.productName} is what happens next.
          </h2>
          <p className="mt-4 max-w-2xl text-lg text-ink-muted">
            Keep their splitter. {brand.productName} gives you each stem as a chromatic instrument, drum slices from C1, auto
            ADSR and the MIDI, without leaving the plugin.
          </p>
          <ul className="mt-10 flex flex-wrap gap-2" aria-label="Compatibility">
            {COMPATIBILITY.map((item) => (
              <li key={item} className="rounded-full border border-line bg-surface px-4 py-1.5 text-sm text-ink-muted">
                {item}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {proofQuotes.length > 0 && (
        <section className="container-page py-16 sm:py-24" aria-labelledby="proof">
          <p className="eyebrow">Proof</p>
          <h2 id="proof" className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
            Made with morphs.
          </h2>
          <ul className="mt-10 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {proofQuotes.map((item) => (
              <li key={item.handle} className="card flex flex-col">
                <blockquote className="flex-1 text-sm leading-relaxed text-ink-muted">“{item.quote}”</blockquote>
                <p className="mt-4 text-sm">
                  {item.url ? (
                    <a href={item.url} className="text-ink underline underline-offset-4" rel="noopener nofollow">
                      {item.handle}
                    </a>
                  ) : (
                    <span className="text-ink">{item.handle}</span>
                  )}
                  <span className="text-ink-dim">
                    {" "}
                    · {item.daw} · {item.genre}
                  </span>
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="container-page py-16 sm:py-24" aria-labelledby="free">
        <div className="card grid gap-8 border-accent/40 md:grid-cols-[1.3fr_1fr] md:items-center">
          <div>
            <p className="eyebrow">Free</p>
            <h2 id="free" className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
              3 free morphs. No card.
            </h2>
            <p className="mt-3 text-lg text-ink-muted">Create an account, sign in inside the plugin, drop your own loop.</p>
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <AttributedLink href="/signup" className="btn btn-primary btn-lg" cta="create_account" location="free">
                Create free account
              </AttributedLink>
              <AttributedLink href="/download" className="btn btn-secondary btn-lg" cta="download_plugin" location="free">
                Download the plugin
              </AttributedLink>
            </div>
            <p className="mt-6 text-sm text-ink-muted">
              {PRICING_HEADLINE}{" "}
              <AttributedLink href="/pricing" className="text-ink underline underline-offset-4" cta="see_pricing" location="free">
                Full pricing →
              </AttributedLink>
            </p>
          </div>
          <div className="rounded-xl border border-line bg-bg p-5" aria-hidden="true">
            <div className="flex items-center justify-between text-xs text-ink-dim">
              <span className="font-mono">{brand.productName.toLowerCase()} · account</span>
              <span className="rounded-full border border-success/40 bg-success/10 px-2 py-0.5 text-success">signed in</span>
            </div>
            <p className="mt-6 text-6xl font-semibold tracking-tight">3</p>
            <p className="mt-1 text-sm text-ink-muted">morphs available</p>
            <div className="mt-6 rounded-md border border-dashed border-line-strong px-4 py-6 text-center text-sm text-ink-dim">
              Drop a clip here · up to 60 s
            </div>
          </div>
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
        <p className="mt-6 text-sm text-ink-dim">
          The details live in the{" "}
          <Link href="/legal/privacy" className="text-ink-muted underline underline-offset-4 hover:text-ink">
            Privacy Policy
          </Link>
          , the{" "}
          <Link href="/legal/terms" className="text-ink-muted underline underline-offset-4 hover:text-ink">
            Terms of Service
          </Link>{" "}
          and the{" "}
          <Link href="/legal/refunds" className="text-ink-muted underline underline-offset-4 hover:text-ink">
            refund policy
          </Link>
          .
        </p>
      </section>
    </>
  );
}

function Timeline({ label, steps, muted = false }: { label: string; steps: string[]; muted?: boolean }) {
  return (
    <div className="grid gap-3 sm:grid-cols-[10rem_1fr] sm:items-center">
      <p className={`text-sm font-medium ${muted ? "text-ink-dim" : "text-ink"}`}>{label}</p>
      <ol className="flex flex-wrap items-center gap-2">
        {steps.map((step, index) => (
          <li key={step} className="flex items-center gap-2">
            <span
              className={`rounded-md border px-3 py-1.5 text-sm ${
                muted ? "border-line bg-surface text-ink-muted" : "border-accent/50 bg-accent/10 text-ink"
              }`}
            >
              {step}
            </span>
            {index < steps.length - 1 && (
              <span aria-hidden="true" className="text-ink-dim">
                →
              </span>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

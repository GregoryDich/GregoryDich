import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { AttributedLink } from "@/components/AttributedLink";
import { brand } from "@/lib/brand";

/**
 * Published only with NEXT_PUBLIC_SAMPLAB_PAGE=1, after the founder has read samplab.com
 * and confirmed the wind-down date. This is the one page that may mention it.
 */
export const metadata: Metadata = brand.samplabPageEnabled
  ? {
      title: "Moving from Samplab? What carries over, what doesn't",
      description: `Samplab stops accepting uploads after September 17, 2026. ${brand.productName} splits a sample into stems and MIDI inside FL Studio, Ableton and Logic, and maps each stem on your keyboard. Three morphs free, no card.`,
    }
  : { title: "Not found", robots: { index: false, follow: false } };

const CARRIES_OVER = [
  "Splitting a sample into stems: bass, drums, synth and vocals.",
  "Audio to MIDI: the transcription comes back as a .mid, plus .fsc for FL Studio.",
  "Key detection, with BPM and the beat grid alongside it.",
  "Working inside FL Studio, Ableton Live and Logic Pro as a VST3 or AU plugin.",
];

const DOES_NOT = [
  "Samplab's timbre-preserving note editing (Resynthesizer). Edit the MIDI instead; the stem keeps playing as it was recorded.",
  "A standalone desktop app. The plugin needs a host.",
  "Offline processing. Morphs run on cloud GPUs; playing a finished morph needs no connection.",
];

const ADDED = [
  "Each stem mapped chromatically across your keyboard, root note on C3.",
  "Drum slices laid out from C1.",
  "Scale-Snap to the detected key, so wrong notes stop being possible.",
  "Auto ADSR per stem, taken from the clip's own envelope.",
];

export default function SamplabPage() {
  if (!brand.samplabPageEnabled) notFound();
  return (
    <div className="container-page py-16 sm:py-24">
      <div className="max-w-3xl">
        <p className="eyebrow">Switching tools</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
          Moving from Samplab? What carries over, what doesn&apos;t.
        </h1>
        <p className="mt-6 text-lg text-ink-muted">
          Samplab has announced it will stop accepting uploads after September 17, 2026. If you used it to split a sample and
          get MIDI, {brand.productName} does that inside FL Studio, Ableton and Logic, and adds what Samplab never had: each
          stem mapped on your keyboard. What it does not do: Samplab&apos;s timbre-preserving note editing (Resynthesizer).
          Existing owners keep an offline version. Three morphs free, no card.
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-3">
          <AttributedLink href="/signup" className="btn btn-primary btn-lg" cta="get_free_morphs" location="samplab">
            Get 3 free morphs
          </AttributedLink>
          <AttributedLink href="/download" className="btn btn-secondary btn-lg" cta="download_plugin" location="samplab">
            Download the plugin
          </AttributedLink>
        </div>
      </div>

      <div className="mt-16 grid gap-6 md:grid-cols-3">
        <Column title="Carries over" items={CARRIES_OVER} />
        <Column title="Not in the plugin" items={DOES_NOT} />
        <Column title="Added" items={ADDED} />
      </div>

      <p className="mt-12 max-w-3xl text-sm text-ink-dim">
        Samplab is a trademark of its owner. {brand.productName} is not affiliated with it; project files do not transfer,
        and the clips you re-morph must be ones you hold the rights to.
      </p>
    </div>
  );
}

function Column({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="card" aria-label={title}>
      <h2 className="text-lg font-semibold">{title}</h2>
      <ul className="mt-4 space-y-3 text-sm text-ink-muted">
        {items.map((item) => (
          <li key={item} className="border-t border-line pt-3">
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}

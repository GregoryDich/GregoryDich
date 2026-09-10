"use client";

import { useState } from "react";

/**
 * Demo placeholder: the illustration always renders; the <video> overlays it only once a
 * source at /media/demo.{webm,mp4} can play, and disappears if none is deployed.
 */
export function DemoVideo() {
  const [state, setState] = useState<"loading" | "ready" | "missing">("loading");

  return (
    <div className="relative aspect-video overflow-hidden rounded-2xl border border-line bg-surface">
      <DemoIllustration />
      {state !== "missing" && (
        <video
          className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-500 ${state === "ready" ? "opacity-100" : "opacity-0"}`}
          poster="/media/demo-poster.jpg"
          autoPlay
          muted
          loop
          playsInline
          preload="metadata"
          aria-label="Product demo: a clip is dropped on the plugin and played from a keyboard"
          onCanPlay={() => setState("ready")}
        >
          <source src="/media/demo.webm" type="video/webm" />
          <source src="/media/demo.mp4" type="video/mp4" onError={() => setState("missing")} />
        </video>
      )}
    </div>
  );
}

function DemoIllustration() {
  const bars = [14, 32, 22, 48, 36, 58, 30, 44, 20, 52, 26, 40, 16, 34, 24, 46, 28, 38, 18, 30];
  return (
    <div className="absolute inset-0 flex flex-col justify-between p-6 sm:p-10" aria-hidden="true">
      <div className="flex items-center justify-between text-xs text-ink-dim">
        <span className="font-mono">clip.flac · 30.0 s</span>
        <span className="font-mono">F minor · 124 BPM</span>
      </div>
      <div className="flex h-24 items-end gap-1 sm:h-40 sm:gap-1.5">
        {bars.map((height, index) => (
          <div
            key={index}
            className={`flex-1 rounded-sm ${index % 5 === 0 ? "bg-accent" : "bg-line-strong"}`}
            style={{ height: `${height}%` }}
          />
        ))}
      </div>
      <div className="grid grid-cols-4 gap-2 text-center text-[11px] font-medium tracking-wide text-ink-muted uppercase sm:text-xs">
        {["Bass", "Drums", "Synth", "Vocals"].map((stem) => (
          <div key={stem} className="rounded-md border border-line bg-surface-2 py-2">
            {stem}
          </div>
        ))}
      </div>
    </div>
  );
}

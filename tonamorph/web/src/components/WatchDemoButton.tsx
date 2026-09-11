"use client";

import { track } from "@/lib/track";

/** Hero CTA: reports `demo_play`, restarts the demo with sound when a video is deployed, and scrolls to it. */
export function WatchDemoButton({ className }: { className?: string }) {
  function play() {
    track("demo_play");
    const section = document.getElementById("demo");
    const video = section?.querySelector("video");
    if (video) {
      video.muted = false;
      video.currentTime = 0;
      video.play().catch(() => {
        // Autoplay with sound refused: the muted loop keeps running.
      });
    }
    section?.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  return (
    <button type="button" className={className} onClick={play}>
      Watch the 60 s demo
    </button>
  );
}

"use client";

import { track } from "@/lib/track";

/** Installer link that reports `plugin_downloaded` with the platform only. */
export function DownloadButton({ href, os, label }: { href: string; os: "macos" | "windows"; label: string }) {
  return (
    <a href={href} className="btn btn-primary btn-lg w-full" download onClick={() => track("plugin_downloaded", { os })}>
      {label}
    </a>
  );
}

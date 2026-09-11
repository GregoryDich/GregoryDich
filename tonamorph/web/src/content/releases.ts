import { brand } from "@/lib/brand";

export interface Release {
  version: string;
  /** ISO date (YYYY-MM-DD). */
  date: string;
  title: string;
  notes: string[];
}

/** Newest first. The first entry drives /download. */
export const releases: readonly [Release, ...Release[]] = [
  {
    version: "0.1.0",
    date: "2026-09-09",
    title: "Early access",
    notes: [
      "Drop any clip (FLAC, WAV, MP3, OGG, AIFF, up to 60 s) and play it from your keyboard within seconds.",
      "Four stems — bass, drums, synth, vocals — separated in the cloud and transcribed to MIDI.",
      "Key and BPM detection with Scale-Lock modes: detected, major, minor, pentatonic major, pentatonic minor, off.",
      "Drum kit mode: drum hits sliced and mapped from C1 upwards.",
      "Auto-ADSR per stem from the detected envelope.",
      "Drag .mid (and .fsc for FL Studio) straight into the DAW timeline.",
      "VST3 on macOS and Windows; AU on macOS. Universal build for Apple silicon and Intel.",
      "Sign in inside the plugin; 3 free credits on every new account.",
    ],
  },
];

export const latestRelease: Release = releases[0];

export type Platform = "macos" | "windows";

const ASSET_SUFFIX: Record<Platform, string> = {
  macos: "macos-universal.pkg",
  windows: "windows-x64.exe",
};

export function releaseAssetUrl(release: Release, platform: Platform): string {
  return `${brand.downloadBaseUrl}/${release.version}/${brand.slug}-${release.version}-${ASSET_SUFFIX[platform]}`;
}

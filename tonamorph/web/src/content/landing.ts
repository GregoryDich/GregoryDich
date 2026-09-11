import { brand } from "@/lib/brand";

/**
 * Copy shared by the landing page and the referral landing (`/m/<code>`): the one-sentence
 * product promise and the "how it works" trio. Changing a word here changes both pages.
 */
export const PRODUCT_PROMISE = `${brand.productName} turns any audio into a playable instrument inside FL Studio and Ableton: stems, MIDI and key in seconds.`;

export interface HowItWorksStep {
  n: string;
  title: string;
  body: string;
}

export const HOW_IT_WORKS: readonly HowItWorksStep[] = [
  { n: "1", title: "Drop", body: "Drop any clip up to 60 s." },
  { n: "2", title: "Play", body: "Bass, drums, synth and vocals arrive mapped across your keyboard, locked to the detected key." },
  { n: "3", title: "Drag", body: "Drag the .mid or .fsc into your piano roll." },
];

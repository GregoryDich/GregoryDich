/**
 * Public roadmap: what is being worked on now, what comes next and what is planned
 * later. Customer-facing wording only; internal tickets stay in the repository.
 */
export interface RoadmapItem {
  title: string;
  body: string;
}

export interface RoadmapColumn {
  id: "now" | "next" | "later";
  title: string;
  intro: string;
  items: readonly RoadmapItem[];
}

export const roadmap: readonly RoadmapColumn[] = [
  {
    id: "now",
    title: "Now",
    intro: "In progress for the launch build.",
    items: [
      {
        title: "Measured speed numbers",
        body: "A benchmark set of 20 clips gives a real p95 from drop to playable; the number replaces the qualified wording on the site.",
      },
      {
        title: "Live status page",
        body: "Component health and the last 24 hours of morph success and latency, refreshed every minute.",
      },
      {
        title: "Demo morph before sign-in",
        body: "The plugin opens with a morphed clip you can play before creating an account.",
      },
      {
        title: "Rate a morph, get it refunded",
        body: "Thumbs down on an unusable result returns that morph to your balance automatically.",
      },
      {
        title: "Crash reports you can opt in to",
        body: "An optional, anonymised crash reporter in the plugin so rare host-specific crashes get fixed faster.",
      },
    ],
  },
  {
    id: "next",
    title: "Next",
    intro: "Queued after launch.",
    items: [
      {
        title: "Update notices in the plugin",
        body: "A banner when a newer version is available, with the changelog one click away.",
      },
      {
        title: "Send a morph to a friend",
        body: "Referral links that give both of you extra morphs after the first successful one.",
      },
      {
        title: "Drop-to-ready timer",
        body: "The plugin measures the full round trip on your connection so the published numbers reflect real sessions.",
      },
      {
        title: "Warm engine during peak hours",
        body: "A GPU kept ready through the evening so the first morph of a session is as fast as the rest.",
      },
    ],
  },
  {
    id: "later",
    title: "Later",
    intro: "Planned, not scheduled.",
    items: [
      {
        title: "Priority lane for paid morphs",
        body: "Pack and subscription morphs skip ahead of free ones when the queue is busy.",
      },
      {
        title: "Sign-in stored in the system keychain",
        body: "Plugin credentials kept in the macOS Keychain and Windows credential store.",
      },
      {
        title: "More stems and longer clips",
        body: "Guitar and piano as separate instruments, and clips beyond 60 seconds.",
      },
    ],
  },
];

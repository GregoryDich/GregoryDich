/**
 * Copy for the referral landing (`/m/<code>`), "send a morph to a friend" (GTM plan §2.4):
 * the friend gets the 3 welcome morphs plus 2 for arriving through the link; the sender
 * earns 3 once the friend's first morph succeeds. Brand-neutral on purpose — the product
 * name comes from `brand` where a page needs it.
 */
export const REFERRAL_COPY = {
  eyebrow: "An invitation",
  /** Browser tab and link preview; the page headline below is the full sentence. */
  title: "5 free morphs from a friend",
  headline: "A friend sent you 5 free morphs.",
  cta: "Claim 5 free morphs",
  terms: "No card. 3 to start, plus 2 from your friend. They get 3 once your first morph succeeds.",
} as const;

/**
 * "Made with morphs": quotes from beta testers who opted in (beta form Q16), with their
 * DAW and genre. The section renders nothing while this list is empty — never add a
 * quote that was not written by the person named.
 */
export interface ProofQuote {
  /** Public handle or first name, exactly as the tester asked to be credited. */
  handle: string;
  daw: string;
  genre: string;
  quote: string;
  /** Optional public profile (YouTube, SoundCloud, …). */
  url?: string;
}

export const proofQuotes: readonly ProofQuote[] = [];

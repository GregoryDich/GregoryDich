/**
 * Speed claim on the landing page. Until the beta benchmark yields a measured p95 the
 * copy stays qualified ("seconds, not minutes"); set the constant once the number exists
 * and the headline switches to the measured figure everywhere it is used.
 */
export const MEASURED_P95_SECONDS: number | null = null;

export interface SpeedClaim {
  headline: string;
  /** Qualifier shown under the headline; null while the claim is unmeasured. */
  measurement: string | null;
}

export function speedClaim(p95Seconds: number | null): SpeedClaim {
  if (p95Seconds === null || !Number.isFinite(p95Seconds) || p95Seconds <= 0) {
    return { headline: "Playable in seconds, not minutes.", measurement: null };
  }
  const seconds = p95Seconds.toFixed(1).replace(/\.0$/, "");
  return {
    headline: `Playable in ${seconds} seconds.`,
    measurement: `p95 from drop to playable, measured across beta morphs on a warm GPU.`,
  };
}

export const SPEED_CLAIM: SpeedClaim = speedClaim(MEASURED_P95_SECONDS);

"use server";

import { api, ApiError } from "@/lib/api";
import { getSessionUser } from "@/lib/supabase/server";
import { NPS_COMMENT_MAX_LENGTH } from "./constants";

export type NpsResult = { ok: true } | { ok: false; reason: "already_answered" | "error"; message: string };

/** Sends one NPS answer for the signed-in user; the API allows one per 30 days (409 otherwise). */
export async function submitNpsAction(score: number, comment: string): Promise<NpsResult> {
  const session = await getSessionUser();
  if (!session) return { ok: false, reason: "error", message: "Your session has expired. Log in again." };
  if (!Number.isInteger(score) || score < 0 || score > 10) {
    return { ok: false, reason: "error", message: "Pick a score between 0 and 10." };
  }
  const trimmed = comment.trim().slice(0, NPS_COMMENT_MAX_LENGTH);
  try {
    await api.submitNps(session.accessToken, trimmed ? { score, comment: trimmed } : { score });
    return { ok: true };
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.status === 409) return { ok: false, reason: "already_answered", message: "Thanks, you already answered recently." };
      if (error.code === "api_not_configured" || error.status === 404) {
        return { ok: false, reason: "error", message: "Feedback is not switched on yet. Reply to the email instead." };
      }
      if (error.code === "network_error") return { ok: false, reason: "error", message: "The API is unreachable. Try again in a minute." };
      return { ok: false, reason: "error", message: error.message };
    }
    return { ok: false, reason: "error", message: "Something went wrong. Try again." };
  }
}

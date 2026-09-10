"use server";

import { revalidatePath } from "next/cache";
import { api, ApiError, type ApiKeyCreated } from "@/lib/api";
import { getSessionUser } from "@/lib/supabase/server";

export type CreateKeyResult = { ok: true; key: ApiKeyCreated } | { ok: false; error: string };
export type RevokeKeyResult = { ok: true } | { ok: false; error: string };

function describe(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "api_not_configured") return "The API is not configured for this site.";
    if (error.status === 404) return "API keys are not available yet.";
    return error.message;
  }
  return "Something went wrong. Try again.";
}

export async function createApiKeyAction(name: string): Promise<CreateKeyResult> {
  const session = await getSessionUser();
  if (!session) return { ok: false, error: "Your session has expired. Log in again." };
  const trimmed = name.trim().slice(0, 64) || "default";
  try {
    const key = await api.createApiKey(session.accessToken, trimmed);
    revalidatePath("/account");
    return { ok: true, key };
  } catch (error) {
    return { ok: false, error: describe(error) };
  }
}

export async function revokeApiKeyAction(id: string): Promise<RevokeKeyResult> {
  const session = await getSessionUser();
  if (!session) return { ok: false, error: "Your session has expired. Log in again." };
  try {
    await api.revokeApiKey(session.accessToken, id);
    revalidatePath("/account");
    return { ok: true };
  } catch (error) {
    return { ok: false, error: describe(error) };
  }
}

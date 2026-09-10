"use client";

import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState, useTransition } from "react";
import { CopyButton } from "@/components/CopyButton";
import type { ApiKey, ApiKeyCreated } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { createApiKeyAction, revokeApiKeyAction } from "./actions";

interface Props {
  keys: ApiKey[];
  /** Null when the list loaded; otherwise the message to show instead of the table. */
  listError: string | null;
}

export function ApiKeysPanel({ keys, listError }: Props) {
  const router = useRouter();
  const nameId = useId();
  const [name, setName] = useState("");
  const [created, setCreated] = useState<ApiKeyCreated | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const [revokingId, setRevokingId] = useState<string | null>(null);

  function create(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    startTransition(async () => {
      const result = await createApiKeyAction(name);
      if (result.ok) {
        setCreated(result.key);
        setName("");
      } else {
        setError(result.error);
      }
    });
  }

  function revoke(key: ApiKey) {
    if (!window.confirm(`Revoke the key "${key.name}" (${key.prefix}…)? Anything using it stops working immediately.`)) return;
    setError(null);
    setRevokingId(key.id);
    startTransition(async () => {
      const result = await revokeApiKeyAction(key.id);
      setRevokingId(null);
      if (!result.ok) setError(result.error);
      router.refresh();
    });
  }

  const active = keys.filter((key) => !key.revoked_at);

  return (
    <div className="space-y-6">
      {error && (
        <p role="alert" className="alert alert-error">
          {error}
        </p>
      )}

      {listError ? (
        <p className="alert alert-info">{listError}</p>
      ) : active.length === 0 ? (
        <p className="text-sm text-ink-muted">No API keys yet. Keys let scripts and CI submit clips with your credits.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-ink-dim uppercase">
              <tr>
                <th className="py-2 pr-4 font-medium">Name</th>
                <th className="py-2 pr-4 font-medium">Prefix</th>
                <th className="py-2 pr-4 font-medium">Created</th>
                <th className="py-2 pr-4 font-medium">Last used</th>
                <th className="py-2 font-medium">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {active.map((key) => (
                <tr key={key.id}>
                  <td className="py-3 pr-4">{key.name}</td>
                  <td className="py-3 pr-4 font-mono text-ink-muted">{key.prefix}…</td>
                  <td className="py-3 pr-4 text-ink-muted">{formatDateTime(key.created_at)}</td>
                  <td className="py-3 pr-4 text-ink-muted">{key.last_used_at ? formatDateTime(key.last_used_at) : "Never"}</td>
                  <td className="py-3 text-right">
                    <button
                      type="button"
                      className="btn btn-danger px-3 py-1.5"
                      onClick={() => revoke(key)}
                      disabled={pending && revokingId === key.id}
                    >
                      {pending && revokingId === key.id ? "Revoking…" : "Revoke"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!listError && (
        <form onSubmit={create} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label htmlFor={nameId} className="label">
              New key name
            </label>
            <input
              id={nameId}
              className="input"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="ci, laptop, render-farm…"
              maxLength={64}
            />
          </div>
          <button type="submit" className="btn btn-secondary" disabled={pending}>
            {pending && !revokingId ? "Creating…" : "Create key"}
          </button>
        </form>
      )}

      {created && (
        <SecretDialog
          created={created}
          onClose={() => {
            setCreated(null);
            router.refresh();
          }}
        />
      )}
    </div>
  );
}

function SecretDialog({ created, onClose }: { created: ApiKeyCreated; onClose: () => void }) {
  const titleId = useId();
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div role="dialog" aria-modal="true" aria-labelledby={titleId} className="card w-full max-w-lg space-y-4 shadow-2xl">
        <h3 id={titleId} className="text-lg font-semibold">
          Your new API key
        </h3>
        <p className="text-sm text-ink-muted">
          This is the only time the full key is shown. Copy it now and store it somewhere safe — if you lose it, revoke it
          and create a new one.
        </p>
        <code className="block overflow-x-auto rounded-md border border-line bg-surface-2 p-3 font-mono text-sm break-all">
          {created.key}
        </code>
        <p className="text-xs text-ink-dim">
          Send it as <code className="kbd">X-API-Key</code>. Key name: {created.name}.
        </p>
        <div className="flex flex-wrap justify-end gap-2">
          <CopyButton value={created.key} label="Copy key" className="btn btn-primary" />
          <button ref={closeRef} type="button" className="btn btn-secondary" onClick={onClose}>
            I have saved it
          </button>
        </div>
      </div>
    </div>
  );
}

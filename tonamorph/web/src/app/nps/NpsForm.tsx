"use client";

import { useId, useState } from "react";
import { brand } from "@/lib/brand";
import { track } from "@/lib/track";
import { submitNpsAction } from "./actions";
import { NPS_COMMENT_MAX_LENGTH } from "./constants";

const SCORES = Array.from({ length: 11 }, (_, index) => index);

type Status = "idle" | "submitting" | "done" | "already_answered";

export function NpsForm({ initialScore }: { initialScore: number | null }) {
  const commentId = useId();
  const [score, setScore] = useState<number | null>(initialScore);
  const [comment, setComment] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (score === null) {
      setError("Pick a score first.");
      return;
    }
    setStatus("submitting");
    const result = await submitNpsAction(score, comment);
    if (result.ok) {
      track("nps_submitted", { score });
      setStatus("done");
      return;
    }
    if (result.reason === "already_answered") {
      setStatus("already_answered");
      return;
    }
    setError(result.message);
    setStatus("idle");
  }

  if (status === "done") {
    return (
      <div className="space-y-3" aria-live="polite">
        <h2 className="text-xl font-semibold">Thanks.</h2>
        <p className="text-sm text-ink-muted">
          Your answer helps decide what gets built next. If something specific needs fixing, {brand.supportEmail} reads
          every message.
        </p>
      </div>
    );
  }

  if (status === "already_answered") {
    return (
      <p className="text-sm text-ink-muted" aria-live="polite">
        Thanks, you already answered recently.
      </p>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-6" noValidate>
      {error && (
        <p role="alert" className="alert alert-error">
          {error}
        </p>
      )}
      <fieldset>
        <legend className="label">How likely are you to recommend {brand.productName} to another producer?</legend>
        <div className="mt-2 grid grid-cols-11 gap-1" role="radiogroup" aria-label="Score from 0 to 10">
          {SCORES.map((value) => {
            const selected = value === score;
            return (
              <button
                key={value}
                type="button"
                role="radio"
                aria-checked={selected}
                onClick={() => setScore(value)}
                className={`rounded-md border py-2.5 text-sm font-medium transition-colors ${
                  selected ? "border-accent bg-accent text-accent-ink" : "border-line bg-surface-2 text-ink-muted hover:border-ink-dim hover:text-ink"
                }`}
              >
                {value}
              </button>
            );
          })}
        </div>
        <div className="mt-1.5 flex justify-between text-xs text-ink-dim">
          <span>Not likely</span>
          <span>Very likely</span>
        </div>
      </fieldset>
      <div>
        <label htmlFor={commentId} className="label">
          What is the main reason for your score? <span className="text-ink-dim">(optional)</span>
        </label>
        <textarea
          id={commentId}
          name="comment"
          className="input min-h-28"
          maxLength={NPS_COMMENT_MAX_LENGTH}
          value={comment}
          onChange={(event) => setComment(event.target.value)}
        />
      </div>
      <button type="submit" className="btn btn-primary w-full" disabled={status === "submitting"}>
        {status === "submitting" ? "Sending…" : "Send"}
      </button>
    </form>
  );
}

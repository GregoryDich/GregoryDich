"use client";

import { useId, useState } from "react";

export const MIN_PASSWORD_LENGTH = 8;

export function passwordStrength(value: string): { score: 0 | 1 | 2 | 3; label: string } {
  if (value.length < MIN_PASSWORD_LENGTH) return { score: 0, label: `At least ${MIN_PASSWORD_LENGTH} characters` };
  let variety = 0;
  if (/[a-z]/.test(value)) variety += 1;
  if (/[A-Z]/.test(value)) variety += 1;
  if (/\d/.test(value)) variety += 1;
  if (/[^A-Za-z0-9]/.test(value)) variety += 1;
  if (value.length >= 14 && variety >= 3) return { score: 3, label: "Strong" };
  if (value.length >= 10 && variety >= 2) return { score: 2, label: "Good" };
  return { score: 1, label: "Weak — add length, numbers or symbols" };
}

interface Props {
  name: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete: "new-password" | "current-password";
  showStrength?: boolean;
  required?: boolean;
}

export function PasswordField({ name, label, value, onChange, autoComplete, showStrength = false, required = true }: Props) {
  const id = useId();
  const [visible, setVisible] = useState(false);
  const strength = passwordStrength(value);
  const colours = ["bg-line-strong", "bg-danger", "bg-accent", "bg-success"];

  return (
    <div>
      <div className="flex items-baseline justify-between">
        <label htmlFor={id} className="label">
          {label}
        </label>
        <button type="button" className="text-xs text-ink-dim hover:text-ink" onClick={() => setVisible((v) => !v)}>
          {visible ? "Hide" : "Show"}
        </button>
      </div>
      <input
        id={id}
        name={name}
        type={visible ? "text" : "password"}
        className="input"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        autoComplete={autoComplete}
        minLength={showStrength ? MIN_PASSWORD_LENGTH : undefined}
        required={required}
        aria-describedby={showStrength ? `${id}-hint` : undefined}
      />
      {showStrength && (
        <div id={`${id}-hint`} className="mt-2">
          <div className="flex gap-1" aria-hidden="true">
            {[1, 2, 3].map((step) => (
              <div key={step} className={`h-1 flex-1 rounded-full ${strength.score >= step ? colours[strength.score] : "bg-line"}`} />
            ))}
          </div>
          <p className="mt-1.5 text-xs text-ink-dim">{value ? strength.label : `At least ${MIN_PASSWORD_LENGTH} characters.`}</p>
        </div>
      )}
    </div>
  );
}

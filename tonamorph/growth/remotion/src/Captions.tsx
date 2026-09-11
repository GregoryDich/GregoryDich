import React from "react";
import { theme } from "./theme";
import type { Caption } from "./types";

export const Captions: React.FC<{ captions: Caption[]; time: number }> = ({ captions, time }) => {
  const current = captions.find((c) => c.start <= time && time < c.end);
  if (!current) {
    return null;
  }
  return (
    <div
      style={{
        position: "absolute",
        left: 60,
        right: 60,
        bottom: 200,
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        gap: "10px 18px",
        padding: "28px 32px",
        borderRadius: 28,
        background: "#05070dcc",
        backdropFilter: "blur(6px)",
      }}
    >
      {(current.words.length > 0
        ? current.words
        : [{ word: current.text, start: current.start, end: current.end }]
      ).map((w, i) => {
        const active = w.start <= time && time < w.end;
        const spoken = time >= w.end;
        return (
          <span
            key={`${w.word}-${i}`}
            style={{
              fontSize: 64,
              lineHeight: 1.1,
              fontWeight: 800,
              color: active ? theme.hot : spoken ? theme.text : theme.muted,
              transform: active ? "scale(1.08)" : "scale(1)",
              textShadow: active ? `0 0 24px ${theme.hot}` : "none",
            }}
          >
            {w.word}
          </span>
        );
      })}
    </div>
  );
};

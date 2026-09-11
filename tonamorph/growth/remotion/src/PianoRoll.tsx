import React, { useMemo } from "react";
import { theme } from "./theme";
import type { MidiNote } from "./types";

const BLACK = new Set([1, 3, 6, 8, 10]);
const PIXELS_PER_SECOND = 220;
const LOOKAHEAD_SECONDS = 2.5;

type Props = {
  notes: MidiNote[];
  time: number;
  width: number;
  height: number;
};

const keyRange = (notes: MidiNote[]): { low: number; high: number } => {
  if (notes.length === 0) {
    return { low: 36, high: 72 };
  }
  const pitches = notes.map((n) => n.pitch);
  let low = Math.min(...pitches);
  let high = Math.max(...pitches);
  while (high - low < 24) {
    low -= 1;
    high += 1;
  }
  low = Math.max(21, Math.floor(low / 12) * 12);
  high = Math.min(108, Math.ceil((high + 1) / 12) * 12 - 1);
  return { low, high };
};

/** Falling-note view: notes drop onto a playhead line and light the key underneath. */
export const PianoRoll: React.FC<Props> = ({ notes, time, width, height }) => {
  const { low, high } = useMemo(() => keyRange(notes), [notes]);
  const whiteKeys = useMemo(() => {
    const keys: number[] = [];
    for (let p = low; p <= high; p += 1) {
      if (!BLACK.has(p % 12)) {
        keys.push(p);
      }
    }
    return keys;
  }, [low, high]);
  const whiteWidth = width / whiteKeys.length;
  const keyboardHeight = Math.min(220, height * 0.32);
  const laneHeight = height - keyboardHeight;

  const whiteIndex = new Map<number, number>();
  whiteKeys.forEach((p, i) => whiteIndex.set(p, i));

  const keyX = (pitch: number): { x: number; w: number; black: boolean } => {
    if (!BLACK.has(pitch % 12)) {
      const i = whiteIndex.get(pitch) ?? 0;
      return { x: i * whiteWidth, w: whiteWidth, black: false };
    }
    let below = pitch - 1;
    while (BLACK.has(below % 12)) {
      below -= 1;
    }
    const i = whiteIndex.get(below) ?? 0;
    const w = whiteWidth * 0.62;
    return { x: (i + 1) * whiteWidth - w / 2, w, black: true };
  };

  const active = new Set(
    notes.filter((n) => n.start <= time && time < n.start + n.duration).map((n) => n.pitch),
  );
  const visible = notes.filter(
    (n) => n.start + n.duration >= time - 0.2 && n.start <= time + LOOKAHEAD_SECONDS,
  );

  return (
    <div style={{ position: "relative", width, height, overflow: "hidden" }}>
      <div style={{ position: "absolute", left: 0, top: 0, width, height: laneHeight }}>
        {visible.map((n, i) => {
          const { x, w } = keyX(n.pitch);
          const bottom = (n.start - time) * PIXELS_PER_SECOND;
          const h = Math.max(10, n.duration * PIXELS_PER_SECOND);
          const lit = active.has(n.pitch) && n.start <= time;
          return (
            <div
              key={`${n.start}-${n.pitch}-${i}`}
              style={{
                position: "absolute",
                left: x + 3,
                width: w - 6,
                bottom,
                height: h,
                borderRadius: 8,
                background: lit ? theme.hot : theme.accent,
                boxShadow: lit ? `0 0 28px ${theme.hot}` : `0 0 12px ${theme.accent}66`,
                opacity: 0.55 + (n.velocity / 127) * 0.45,
              }}
            />
          );
        })}
        <div
          style={{
            position: "absolute",
            left: 0,
            width,
            bottom: 0,
            height: 4,
            background: theme.accentSoft,
            boxShadow: `0 0 18px ${theme.accentSoft}`,
          }}
        />
      </div>
      <div
        style={{
          position: "absolute",
          left: 0,
          top: laneHeight,
          width,
          height: keyboardHeight,
          background: theme.keyBlack,
        }}
      >
        {whiteKeys.map((p) => {
          const { x, w } = keyX(p);
          const lit = active.has(p);
          return (
            <div
              key={p}
              style={{
                position: "absolute",
                left: x,
                width: w - 2,
                top: 0,
                height: keyboardHeight,
                background: lit ? theme.hot : theme.keyWhite,
                borderRadius: "0 0 8px 8px",
                boxShadow: lit ? `0 0 30px ${theme.hot}` : "none",
              }}
            />
          );
        })}
        {Array.from({ length: high - low + 1 }, (_, i) => low + i)
          .filter((p) => BLACK.has(p % 12))
          .map((p) => {
            const { x, w } = keyX(p);
            const lit = active.has(p);
            return (
              <div
                key={p}
                style={{
                  position: "absolute",
                  left: x,
                  width: w,
                  top: 0,
                  height: keyboardHeight * 0.6,
                  background: lit ? theme.hot : "#05070d",
                  borderRadius: "0 0 6px 6px",
                  boxShadow: lit ? `0 0 30px ${theme.hot}` : "0 4px 10px #00000088",
                }}
              />
            );
          })}
      </div>
    </div>
  );
};

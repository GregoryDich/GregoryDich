import React from "react";
import { interpolate } from "remotion";
import { PianoRoll } from "./PianoRoll";
import { theme } from "./theme";
import type { MidiNote } from "./types";

const LANES = ["drums", "bass", "synth", "vocals", "tonamorph"] as const;
const LOOP_SECONDS = 8;

type Props = { time: number; notes: MidiNote[]; stemName: string; title: string };

/** DAW arrangement view: clip lanes with a moving playhead above the piano roll. */
export const DawScene: React.FC<Props> = ({ time, notes, stemName, title }) => {
  const width = 1000;
  const playheadX = ((time % LOOP_SECONDS) / LOOP_SECONDS) * width;
  const rollFade = interpolate(time, [2.5, 3.2], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div style={{ position: "absolute", inset: 0, padding: 40 }}>
      <div
        style={{
          height: "100%",
          borderRadius: 36,
          background: theme.panel,
          border: `2px solid ${theme.panelBorder}`,
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            padding: "24px 40px",
            borderBottom: `2px solid ${theme.panelBorder}`,
            color: theme.text,
            fontSize: 36,
            fontWeight: 700,
          }}
        >
          <span>{title} · session</span>
          <span style={{ color: theme.muted }}>{Math.floor(time * 4)} / 4</span>
        </div>
        <div style={{ position: "relative", height: 360 }}>
          {LANES.map((lane, i) => {
            const isPlugin = lane === "tonamorph";
            const highlighted = lane === (stemName === "other" ? "synth" : stemName) || isPlugin;
            return (
              <div
                key={lane}
                style={{
                  position: "absolute",
                  top: i * 70 + 10,
                  left: 0,
                  width,
                  height: 62,
                  display: "flex",
                  alignItems: "center",
                }}
              >
                <span
                  style={{
                    width: 190,
                    paddingLeft: 30,
                    color: highlighted ? theme.text : theme.muted,
                    fontSize: 30,
                    fontWeight: 600,
                  }}
                >
                  {lane}
                </span>
                <div
                  style={{
                    position: "relative",
                    flex: 1,
                    height: 50,
                    marginRight: 30,
                    borderRadius: 12,
                    background: theme.bg,
                    overflow: "hidden",
                  }}
                >
                  {[0, 0.5].map((offset) => (
                    <div
                      key={offset}
                      style={{
                        position: "absolute",
                        left: `${offset * 100}%`,
                        width: "48%",
                        top: 6,
                        bottom: 6,
                        borderRadius: 10,
                        background: isPlugin ? theme.hot : highlighted ? theme.accent : theme.panelBorder,
                        opacity: isPlugin ? Math.min(1, Math.max(0, time - 2.5)) : 1,
                      }}
                    />
                  ))}
                </div>
              </div>
            );
          })}
          <div
            style={{
              position: "absolute",
              top: 0,
              bottom: 0,
              left: 190 + playheadX * 0.79,
              width: 4,
              background: theme.accentSoft,
              boxShadow: `0 0 16px ${theme.accentSoft}`,
            }}
          />
        </div>
        <div style={{ flex: 1, opacity: rollFade }}>
          <PianoRoll notes={notes} time={Math.max(0, time - 3)} width={width} height={470} />
        </div>
      </div>
    </div>
  );
};

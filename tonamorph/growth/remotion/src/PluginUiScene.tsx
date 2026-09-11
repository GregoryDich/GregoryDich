import React from "react";
import { interpolate } from "remotion";
import { PianoRoll } from "./PianoRoll";
import { theme } from "./theme";
import type { MidiNote } from "./types";

const STEMS = ["bass", "drums", "other", "vocals"] as const;
const DROP_END = 3;
const STEMS_END = 6;

type Props = { time: number; notes: MidiNote[]; stemName: string; title: string };

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** Stylised Tonamorph UI: drop zone → stems appear → keys light with the transcription. */
export const PluginUiScene: React.FC<Props> = ({ time, notes, stemName, title }) => {
  const dropProgress = interpolate(time, [0, DROP_END * 0.7], [0, 1], clamp);
  const dropFade = interpolate(time, [DROP_END - 0.4, DROP_END], [1, 0], clamp);
  const stemsFade = interpolate(time, [DROP_END, DROP_END + 0.4], [0, 1], clamp);
  const rollFade = interpolate(time, [STEMS_END - 0.3, STEMS_END + 0.3], [0, 1], clamp);
  const chipY = interpolate(dropProgress, [0, 1], [-260, 0]);
  const rollTime = Math.max(0, time - STEMS_END);

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
            alignItems: "center",
            justifyContent: "space-between",
            padding: "28px 40px",
            borderBottom: `2px solid ${theme.panelBorder}`,
          }}
        >
          <span style={{ color: theme.text, fontSize: 44, fontWeight: 800 }}>{title}</span>
          <span style={{ color: theme.muted, fontSize: 28 }}>audio → MIDI</span>
        </div>

        <div style={{ position: "relative", flex: 1 }}>
          {dropFade > 0 ? (
            <div
              style={{
                position: "absolute",
                inset: 40,
                opacity: dropFade,
                border: `4px dashed ${theme.accentSoft}`,
                borderRadius: 32,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexDirection: "column",
                gap: 24,
              }}
            >
              <div
                style={{
                  transform: `translateY(${chipY}px)`,
                  padding: "22px 40px",
                  borderRadius: 20,
                  background: theme.accent,
                  color: theme.text,
                  fontSize: 40,
                  fontWeight: 700,
                }}
              >
                loop.wav
              </div>
              <span style={{ color: theme.muted, fontSize: 34 }}>Drop a clip</span>
            </div>
          ) : null}

          {time >= DROP_END && rollFade < 1 ? (
            <div
              style={{
                position: "absolute",
                inset: 40,
                opacity: stemsFade * (1 - rollFade),
                display: "flex",
                flexDirection: "column",
                gap: 22,
                justifyContent: "center",
              }}
            >
              {STEMS.map((stem, i) => {
                const appear = interpolate(
                  time,
                  [DROP_END + i * 0.35, DROP_END + i * 0.35 + 0.3],
                  [0, 1],
                  clamp,
                );
                const chosen = stem === stemName;
                return (
                  <div
                    key={stem}
                    style={{
                      opacity: appear,
                      transform: `translateX(${(1 - appear) * -40}px)`,
                      padding: "26px 36px",
                      borderRadius: 20,
                      background: chosen ? theme.accent : theme.bg,
                      border: `2px solid ${chosen ? theme.accentSoft : theme.panelBorder}`,
                      color: theme.text,
                      fontSize: 40,
                      fontWeight: chosen ? 800 : 500,
                      display: "flex",
                      justifyContent: "space-between",
                    }}
                  >
                    <span>{stem === "other" ? "synth" : stem}</span>
                    <span style={{ color: chosen ? theme.text : theme.muted }}>
                      {chosen ? "→ keys" : "ready"}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : null}

          {rollFade > 0 ? (
            <div style={{ position: "absolute", inset: 0, opacity: rollFade }}>
              <PianoRoll notes={notes} time={rollTime} width={1000} height={820} />
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};

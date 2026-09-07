import { useAudioData, visualizeAudio } from "@remotion/media-utils";
import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "./theme";

const BARS = 64;

export const Waveform: React.FC<{ src: string }> = ({ src }) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const audioData = useAudioData(src);
  const values = audioData
    ? visualizeAudio({ fps, frame, audioData, numberOfSamples: BARS, smoothing: true })
    : new Array<number>(BARS).fill(0);
  const gap = 8;
  const barWidth = (width - gap * (BARS + 1)) / BARS;
  const maxHeight = 420;

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        top: 120,
        width,
        height: maxHeight,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap,
      }}
    >
      {values.map((v, i) => {
        const h = Math.max(12, Math.min(1, v * 2.2) * maxHeight);
        return (
          <div
            key={i}
            style={{
              width: barWidth,
              height: h,
              borderRadius: barWidth / 2,
              background: `linear-gradient(180deg, ${theme.accentSoft}, ${theme.accent})`,
              boxShadow: `0 0 16px ${theme.accent}55`,
            }}
          />
        );
      })}
    </div>
  );
};

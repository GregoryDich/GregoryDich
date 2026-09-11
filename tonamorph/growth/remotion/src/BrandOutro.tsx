import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "./theme";

export const BrandOutro: React.FC<{ cta: string; title: string }> = ({ cta, title }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const fade = interpolate(frame, [0, 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const pop = spring({ frame: frame - 6, fps, config: { damping: 12, stiffness: 140 } });

  return (
    <AbsoluteFill
      style={{
        opacity: fade,
        background: `radial-gradient(circle at 50% 35%, ${theme.accent}55 0%, ${theme.bg} 60%)`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        gap: 40,
        fontFamily: theme.font,
      }}
    >
      <div style={{ color: theme.text, fontSize: 120, fontWeight: 900, letterSpacing: -3 }}>
        {title}
      </div>
      <div style={{ color: theme.muted, fontSize: 44 }}>Audio → playable MIDI in 2 seconds</div>
      <div
        style={{
          transform: `scale(${pop})`,
          marginTop: 30,
          padding: "34px 70px",
          borderRadius: 999,
          background: theme.hot,
          color: theme.text,
          fontSize: 66,
          fontWeight: 800,
          boxShadow: `0 0 60px ${theme.hot}88`,
        }}
      >
        {cta}
      </div>
      <div style={{ color: theme.text, fontSize: 40, marginTop: 10 }}>Free plugin · link in bio</div>
    </AbsoluteFill>
  );
};

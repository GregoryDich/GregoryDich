import React from "react";
import { AbsoluteFill, Audio, OffthreadVideo, Sequence, useCurrentFrame, useVideoConfig } from "remotion";
import { BrandOutro } from "./BrandOutro";
import { Captions } from "./Captions";
import { DawScene } from "./DawScene";
import { PluginUiScene } from "./PluginUiScene";
import { Waveform } from "./Waveform";
import { resolveSrc } from "./media";
import { theme } from "./theme";
import { OUTRO_START_FRAME, type SplitScreenShortProps } from "./types";

const TOP_HEIGHT = 960;

export const SplitScreenShort: React.FC<SplitScreenShortProps> = ({
  audioSrc,
  voiceoverSrc,
  midiNotes,
  captions,
  scene,
  presenter,
  avatarSrc,
  cta,
  title,
  stemName,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const time = frame / fps;
  const stemUrl = resolveSrc(audioSrc);
  const voiceUrl = voiceoverSrc ? resolveSrc(voiceoverSrc) : null;
  const avatarUrl = avatarSrc ? resolveSrc(avatarSrc) : null;
  const presenterAudio = voiceUrl ?? stemUrl;

  return (
    <AbsoluteFill style={{ backgroundColor: theme.bg, fontFamily: theme.font }}>
      <Audio src={stemUrl} volume={voiceUrl ? 0.55 : 0.9} />
      {voiceUrl ? <Audio src={voiceUrl} /> : null}

      <div style={{ position: "absolute", top: 0, left: 0, width, height: TOP_HEIGHT }}>
        {scene === "daw" ? (
          <DawScene time={time} notes={midiNotes} stemName={stemName} title={title} />
        ) : (
          <PluginUiScene time={time} notes={midiNotes} stemName={stemName} title={title} />
        )}
      </div>

      <div
        style={{
          position: "absolute",
          top: TOP_HEIGHT,
          left: 0,
          width,
          height: height - TOP_HEIGHT,
          overflow: "hidden",
          background: `linear-gradient(180deg, ${theme.panel} 0%, ${theme.bg} 100%)`,
          borderTop: `2px solid ${theme.panelBorder}`,
        }}
      >
        {presenter === "avatar_clip" && avatarUrl ? (
          <OffthreadVideo
            src={avatarUrl}
            muted
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        ) : (
          <Waveform src={presenterAudio} />
        )}
        <Captions captions={captions} time={time} />
      </div>

      <Sequence from={OUTRO_START_FRAME} layout="none">
        <BrandOutro cta={cta} title={title} />
      </Sequence>
    </AbsoluteFill>
  );
};

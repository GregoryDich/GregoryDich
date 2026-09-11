import React from "react";
import { Composition } from "remotion";
import { SplitScreenShort } from "./SplitScreenShort";
import { DURATION_IN_FRAMES, FPS, HEIGHT, WIDTH, type SplitScreenShortProps } from "./types";

const demoNotes = Array.from({ length: 24 }, (_, i) => ({
  start: i * 0.5,
  duration: 0.4,
  pitch: 41 + [0, 3, 5, 7, 10, 12, 10, 7][i % 8],
  velocity: 90 + (i % 3) * 10,
}));

const defaultProps: SplitScreenShortProps = {
  audioSrc: "stem.wav",
  voiceoverSrc: null,
  midiNotes: demoNotes,
  captions: [
    {
      text: "Sample to playable keys in two seconds",
      start: 0.2,
      end: 2.8,
      words: [
        { word: "Sample", start: 0.2, end: 0.6 },
        { word: "to", start: 0.6, end: 0.8 },
        { word: "playable", start: 0.8, end: 1.4 },
        { word: "keys", start: 1.4, end: 1.8 },
        { word: "in", start: 1.8, end: 2.0 },
        { word: "two", start: 2.0, end: 2.3 },
        { word: "seconds", start: 2.3, end: 2.8 },
      ],
    },
  ],
  scene: "plugin_ui",
  presenter: "waveform",
  avatarSrc: null,
  cta: "3 free credits",
  title: "Tonamorph",
  stemName: "bass",
};

export const Root: React.FC = () => {
  return (
    <Composition
      id="SplitScreenShort"
      component={SplitScreenShort}
      durationInFrames={DURATION_IN_FRAMES}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      defaultProps={defaultProps}
    />
  );
};

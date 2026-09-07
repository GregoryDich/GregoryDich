export type MidiNote = {
  start: number;
  duration: number;
  pitch: number;
  velocity: number;
};

export type CaptionWord = {
  word: string;
  start: number;
  end: number;
};

export type Caption = {
  text: string;
  start: number;
  end: number;
  words: CaptionWord[];
};

export type Scene = "daw" | "plugin_ui";
export type Presenter = "waveform" | "avatar_clip";

export type SplitScreenShortProps = {
  audioSrc: string;
  voiceoverSrc: string | null;
  midiNotes: MidiNote[];
  captions: Caption[];
  scene: Scene;
  presenter: Presenter;
  avatarSrc: string | null;
  cta: string;
  title: string;
  stemName: string;
};

export const FPS = 30;
export const WIDTH = 1080;
export const HEIGHT = 1920;
export const DURATION_IN_FRAMES = 450;
export const OUTRO_START_FRAME = 360;

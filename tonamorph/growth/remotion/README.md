# Tonamorph short — Remotion project

`SplitScreenShort` (1080x1920, 450 frames at 30 fps) is the composition rendered by the
growth engine's `render_video` tool.

## Props

```ts
{
  audioSrc: string;            // chosen stem (file in the public dir, or URL)
  voiceoverSrc: string | null; // ElevenLabs narration
  midiNotes: { start: number; duration: number; pitch: number; velocity: number }[];
  captions: { text: string; start: number; end: number; words: { word; start; end }[] }[];
  scene: "daw" | "plugin_ui";
  presenter: "waveform" | "avatar_clip";
  avatarSrc: string | null;
  cta: string;                 // "3 free credits"
  title: string;               // "Tonamorph"
  stemName: string;            // bass | drums | other | vocals
}
```

Components: `PianoRoll` (falling notes onto a playhead, lit keys), `Waveform`
(`@remotion/media-utils` bars from the narration or the stem), `Captions` (word-timed),
`PluginUiScene` (drop zone → stems → keys), `DawScene` (arrangement lanes + playhead),
`BrandOutro` (last 3 s, CTA).

## Rendering

```bash
npm install
npx remotion render src/index.ts SplitScreenShort out/short.mp4 \
  --props=props.json --public-dir=/path/with/stem.wav
```

The growth engine passes `--props`, `--public-dir`, `--concurrency` and, from the
environment, `--browser-executable` (`REMOTION_BROWSER_EXECUTABLE`) and `--gl`
(`REMOTION_GL`).

### Rendering in this container

Node 22 lives in `/opt/node22/bin` and Chromium under `/opt/pw-browsers`. The full Chrome
binary there has dropped the old headless mode, so use the headless shell (or the full binary
with `--chrome-mode=chrome-for-testing`):

```bash
export PATH=/opt/node22/bin:$PATH
export REMOTION_BROWSER_EXECUTABLE=/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell
npx remotion render src/index.ts SplitScreenShort out/short.mp4 --props=props.json \
  --public-dir=./public --frames=0-59            # add --gl=swiftshader if GL init fails
```

`npm run typecheck` runs `tsc --noEmit`; `npm run preview` opens Remotion Studio.

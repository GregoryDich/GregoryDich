import { Config } from "@remotion/cli/config";

type Gl = Parameters<typeof Config.setChromiumOpenGlRenderer>[0];
const GL_RENDERERS: readonly Gl[] = ["swangle", "angle", "egl", "swiftshader", "vulkan", "angle-egl"];

Config.setEntryPoint("./src/index.ts");
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);

// Headless sandboxes (CI, containers) point these at a local Chromium and a software GL.
if (process.env.REMOTION_BROWSER_EXECUTABLE) {
  Config.setBrowserExecutable(process.env.REMOTION_BROWSER_EXECUTABLE);
}
const gl = process.env.REMOTION_GL as Gl | undefined;
if (gl && GL_RENDERERS.includes(gl)) {
  Config.setChromiumOpenGlRenderer(gl);
}

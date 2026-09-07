import { staticFile } from "remotion";

/** Absolute URLs and data URIs pass through; anything else is served from the public dir. */
export const resolveSrc = (src: string): string => {
  if (/^(https?:|data:|blob:)/.test(src)) {
    return src;
  }
  return staticFile(src);
};

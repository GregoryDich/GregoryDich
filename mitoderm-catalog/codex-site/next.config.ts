import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Page metadata (title, description, canonical address, social preview) always goes into <head>. By default it is
  // streamed into <body> for ordinary browsers and for Googlebot; the product pages take theirs from static data, so
  // waiting for it costs nothing, and every search robot and audit reads it where it expects it.
  htmlLimitedBots: /.*/,
};

export default nextConfig;

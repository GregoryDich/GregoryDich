import type { NextConfig } from "next";

/**
 * Security headers. The CSP is assembled at build time from the public env so the
 * Supabase project and the API are the only remote origins the browser may talk to;
 * Klaviyo is allowed only when a company id is configured. Next.js hydrates through inline
 * scripts without nonces on statically rendered pages, hence `'unsafe-inline'` in
 * script-src (a per-request nonce would force every page to render dynamically).
 */
function origin(value: string | undefined): string | null {
  if (!value) return null;
  try {
    return new URL(value).origin;
  } catch {
    return null;
  }
}

const supabaseOrigin = origin(process.env.NEXT_PUBLIC_SUPABASE_URL);
const apiOrigin = origin(process.env.NEXT_PUBLIC_API_URL);
const klaviyoEnabled = Boolean(process.env.NEXT_PUBLIC_KLAVIYO_COMPANY_ID?.trim());
const paddleEnabled = Boolean(process.env.NEXT_PUBLIC_PADDLE_CLIENT_TOKEN?.trim());
const isDev = process.env.NODE_ENV === "development";

const scriptSrc = ["'self'", "'unsafe-inline'", "https://va.vercel-scripts.com"];
const connectSrc = ["'self'", "https://vitals.vercel-insights.com"];
const imgSrc = ["'self'", "data:", "blob:"];
const frameSrc: string[] = [];
if (isDev) scriptSrc.push("'unsafe-eval'");
if (supabaseOrigin) {
  connectSrc.push(supabaseOrigin, supabaseOrigin.replace(/^http/, "ws"));
}
if (apiOrigin) connectSrc.push(apiOrigin);
if (klaviyoEnabled) {
  scriptSrc.push("https://static.klaviyo.com", "https://static-tracking.klaviyo.com");
  connectSrc.push("https://a.klaviyo.com", "https://static.klaviyo.com", "https://static-tracking.klaviyo.com");
  imgSrc.push("https://static.klaviyo.com", "https://a.klaviyo.com");
}
if (paddleEnabled) {
  // Paddle.js and the overlay checkout it opens in an iframe.
  scriptSrc.push("https://cdn.paddle.com");
  connectSrc.push("https://*.paddle.com");
  imgSrc.push("https://*.paddle.com");
  frameSrc.push("https://buy.paddle.com", "https://sandbox-buy.paddle.com", "https://cdn.paddle.com");
}

const contentSecurityPolicy = [
  "default-src 'self'",
  `script-src ${scriptSrc.join(" ")}`,
  "style-src 'self' 'unsafe-inline'",
  `img-src ${imgSrc.join(" ")}`,
  "font-src 'self'",
  `connect-src ${connectSrc.join(" ")}`,
  "media-src 'self'",
  `frame-src ${frameSrc.length > 0 ? frameSrc.join(" ") : "'none'"}`,
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  ...(isDev ? [] : ["upgrade-insecure-requests"]),
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: contentSecurityPolicy },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()" },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
];

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  async headers() {
    return [{ source: "/(.*)", headers: securityHeaders }];
  },
};

export default nextConfig;

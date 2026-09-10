import { ImageResponse } from "next/og";
import { brand } from "@/lib/brand";

export const alt = `${brand.productName} — ${brand.tagline}`;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: 72,
          background: "#0a0a0c",
          color: "#f2f2f4",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <div style={{ width: 56, height: 56, borderRadius: 14, background: "#f2b33d" }} />
          <div style={{ fontSize: 36, fontWeight: 600 }}>{brand.productName}</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <div style={{ fontSize: 76, fontWeight: 600, lineHeight: 1.05, letterSpacing: -2, maxWidth: 1000 }}>{brand.tagline}</div>
          <div style={{ fontSize: 30, color: "#a3a3ad" }}>Stems · MIDI · Key and BPM · VST3 and AU · 3 free credits</div>
        </div>
      </div>
    ),
    size,
  );
}

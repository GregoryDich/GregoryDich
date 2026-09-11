import type { MetadataRoute } from "next";
import { brand } from "@/lib/brand";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: ["/account", "/auth/", "/login", "/signup", "/reset-password"] }],
    sitemap: `${brand.siteUrl}/sitemap.xml`,
  };
}

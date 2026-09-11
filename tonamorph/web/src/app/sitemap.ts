import type { MetadataRoute } from "next";
import { brand } from "@/lib/brand";
import { availableLegalSlugs } from "@/lib/legal";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  const pages: MetadataRoute.Sitemap = [
    { url: `${brand.siteUrl}/`, lastModified: now, changeFrequency: "weekly", priority: 1 },
    { url: `${brand.siteUrl}/pricing`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${brand.siteUrl}/download`, lastModified: now, changeFrequency: "weekly", priority: 0.8 },
    { url: `${brand.siteUrl}/changelog`, lastModified: now, changeFrequency: "weekly", priority: 0.5 },
    { url: `${brand.siteUrl}/roadmap`, lastModified: now, changeFrequency: "monthly", priority: 0.5 },
    { url: `${brand.siteUrl}/status`, lastModified: now, changeFrequency: "hourly", priority: 0.4 },
  ];
  if (brand.samplabPageEnabled) {
    pages.push({ url: `${brand.siteUrl}/samplab`, lastModified: now, changeFrequency: "monthly", priority: 0.6 });
  }
  // `/m/<code>` referral links are personal (noindex) and never listed.
  for (const slug of availableLegalSlugs()) {
    pages.push({ url: `${brand.siteUrl}/legal/${slug}`, lastModified: now, changeFrequency: "yearly", priority: 0.3 });
  }
  return pages;
}

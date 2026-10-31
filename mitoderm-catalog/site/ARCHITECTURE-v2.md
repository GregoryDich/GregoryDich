# MITODERM site v2 — page architecture (owner, 31/10/2026, verbatim)

Build every page as three stacked layers, lowest to highest z-index:

1. **Background (z 0):** one solid colour or vertical gradient per section. Brand base #0a0a0b / #111114. A line's colour
   appears only inside that line's section: V-TECH FACE black + gold #c9a24b, PEELING champagne #d8c48a, BIOSPICULE green
   #1E4634, DEVICES silver #d9d4cc, HAIR black + gold. MITOTECH, you know colors. Full-bleed, fixed, no product images here.
2. **Motion (z 10):** only the animated elements — soft shapeless smoke and glow in the section's colour, particles of real
   ingredients, the product (3D or image). pointer-events: none except on the products. Nothing invented: no lines, rings,
   dots, markers, panels, pedestals.
3. **Content (z 20):** all text, buttons, cards, forms — always above the motion layer. Desktop: copy on the right (RTL),
   product in the left column, never under the text. Phone: the product in its own stage under the heading.

Rules: dir="rtl" lang="he", Rubik, product names in Latin, texts only from MITODERM-3D-story.xlsx, assets at ≥ 2× their CSS
size, prefers-reduced-motion stops layer 2, visible keyboard focus.

Home hero: the lineup image (desktop 2000×1243, phone 853×1844, swapped by breakpoint). Each product is a hotspot: on
hover/focus its packaging glows (the glow image is the hover state) and its name appears as a small label; click opens the
product page. Touch: first tap shows the label, second opens.

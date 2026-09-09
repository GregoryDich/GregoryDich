"""Debug image: mask + contour + length line + max-width line (+ a top-down panel)."""
from __future__ import annotations

import cv2
import numpy as np

from .geometry import project
from .measure import Measurement, clean_mask
from .util import bgr, rotate_to_upright

GREEN, YELLOW, RED, BLUE, WHITE = (0, 200, 0), (0, 220, 255), (0, 0, 255), (255, 120, 0), (255, 255, 255)


def _pt(p3: np.ndarray, K: np.ndarray) -> tuple[int, int]:
    uv = project(p3[None, :], K)[0]
    return int(round(uv[0])), int(round(uv[1]))


def render_topdown(m: Measurement, mm_per_px: float = 1.0, pad: int = 25) -> np.ndarray:
    ab = m.outline_ab_mm
    a0, b0 = ab[:, 0].min() - pad, ab[:, 1].min() - pad
    Wt = int((ab[:, 0].max() - a0 + pad) / mm_per_px) + 1
    Ht = int((ab[:, 1].max() - b0 + pad) / mm_per_px) + 1
    img = np.full((Ht, Wt, 3), 30, np.uint8)
    px = np.round((ab - [a0, b0]) / mm_per_px).astype(np.int32)
    if m.method == "contour":
        cv2.fillPoly(img, [px], (60, 120, 60))
        cv2.polylines(img, [px], True, YELLOW, 1)
    else:
        img[px[:, 1].clip(0, Ht - 1), px[:, 0].clip(0, Wt - 1)] = (60, 160, 60)
    heel_a = ab[:, 0].min(); toe_a = ab[:, 0].max(); b_mid = float(np.median(ab[:, 1]))
    p = lambda a, b: (int(round((a - a0) / mm_per_px)), int(round((b - b0) / mm_per_px)))
    cv2.line(img, p(heel_a, b_mid), p(toe_a, b_mid), RED, 1)
    wa = heel_a + m.width_at_mm
    cv2.line(img, p(wa, ab[:, 1].min() - 5), p(wa, ab[:, 1].max() + 5), BLUE, 1)
    return img


def render_debug(rgb: np.ndarray, mask: np.ndarray, m: Measurement, K: np.ndarray, confidence: float | None = None,
                 orientation: str | None = None, rotate: bool = False, title: str = "") -> np.ndarray:
    img = bgr(rgb).copy()
    mk = clean_mask(mask)
    tint = img.copy()
    tint[mk] = (0.55 * img[mk] + 0.45 * np.array(GREEN)).astype(np.uint8)
    img = tint
    cnts, _ = cv2.findContours(mk.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(img, cnts, -1, YELLOW, 2)
    heel, toe = _pt(m.heel_3d, K), _pt(m.toe_3d, K)
    wl, wr = _pt(m.width_left_3d, K), _pt(m.width_right_3d, K)
    cv2.line(img, heel, toe, RED, 3)
    cv2.circle(img, heel, 8, RED, -1); cv2.circle(img, toe, 8, RED, -1)
    cv2.line(img, wl, wr, BLUE, 3)
    cv2.circle(img, wl, 8, BLUE, -1); cv2.circle(img, wr, 8, BLUE, -1)
    if rotate:
        img = rotate_to_upright(img, orientation)
    lines = [f"{title}  L = {m.length_mm:.1f} mm   W = {m.width_mm:.1f} mm".strip(),
             f"method={m.method} conf={'-' if confidence is None else f'{confidence:.2f}'} "
             f"lidar_pts={m.n_points} h={m.foot_height_mm:.0f}mm plane_rms={m.plane_rms_mm:.1f}mm "
             f"inliers={m.floor_inliers}"]
    lines += [f"! {w}" for w in m.warnings]
    y = 34
    for i, s in enumerate(lines):
        cv2.putText(img, s, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 1.0 if i == 0 else 0.7, (0, 0, 0), 5)
        cv2.putText(img, s, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 1.0 if i == 0 else 0.7, WHITE, 2)
        y += 38 if i == 0 else 28
    # top-down panel (1 px = 1 mm), scaled to at most 45% of the frame width, on a black strip
    top = render_topdown(m)
    scale = min(0.45 * img.shape[1] / top.shape[1], 0.6 * img.shape[0] / top.shape[0])
    top = cv2.resize(top, (int(top.shape[1] * scale), int(top.shape[0] * scale)), interpolation=cv2.INTER_NEAREST)
    strip = np.zeros((img.shape[0], top.shape[1] + 20, 3), np.uint8)
    y0 = (img.shape[0] - top.shape[0]) // 2
    strip[y0:y0 + top.shape[0], 10:10 + top.shape[1]] = top
    cv2.putText(strip, f"top-down (floor plane)  L={m.length_mm:.1f} mm  W={m.width_mm:.1f} mm", (10, y0 - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 2)
    cv2.putText(strip, f"scale {1 / scale:.2f} mm/px, max width at {m.width_at_mm:.0f} mm from heel", (10, y0 + top.shape[0] + 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, WHITE, 1)
    return np.hstack([img, strip])

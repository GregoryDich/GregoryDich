"""Small shared helpers: display rotation, image conversions."""
from __future__ import annotations

import cv2
import numpy as np

# ARKit's capturedImage is always in the sensor's native landscape orientation
# (equivalent to UI orientation "landscapeRight"). These rotations are for
# DISPLAY / RF-DETR input only; all geometry stays in the sensor frame.
_ROTATE_CODE = {
    "portrait": cv2.ROTATE_90_CLOCKWISE,
    "portraitUpsideDown": cv2.ROTATE_90_COUNTERCLOCKWISE,
    "landscapeLeft": cv2.ROTATE_180,
    "landscapeRight": None,
    "unknown": None,
    None: None,
}
_INVERSE = {
    cv2.ROTATE_90_CLOCKWISE: cv2.ROTATE_90_COUNTERCLOCKWISE,
    cv2.ROTATE_90_COUNTERCLOCKWISE: cv2.ROTATE_90_CLOCKWISE,
    cv2.ROTATE_180: cv2.ROTATE_180,
}


def rotate_to_upright(img: np.ndarray, orientation: str | None) -> np.ndarray:
    """Rotate a sensor-frame image so it looks upright for the given UI orientation."""
    code = _ROTATE_CODE.get(orientation)
    return img if code is None else cv2.rotate(img, code)


def rotate_from_upright(img: np.ndarray, orientation: str | None) -> np.ndarray:
    """Inverse of rotate_to_upright: bring an upright image back to the sensor frame."""
    code = _ROTATE_CODE.get(orientation)
    return img if code is None else cv2.rotate(img, _INVERSE[code])


def bgr(rgb: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def rgb(bgr_img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)

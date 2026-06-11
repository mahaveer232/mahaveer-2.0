"""
video_processor.py — Utility helpers for video source management.
The actual processing loop lives in app.py to share Flask's global state cleanly.
"""

import cv2


def get_video_info(path: str) -> dict | None:
    """Return basic metadata about a video file, or None if unreadable."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return None
    fps    = cap.get(cv2.CAP_PROP_FPS) or 30
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    info   = {
        "fps"        : round(fps, 2),
        "width"      : int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height"     : int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "frame_count": frames,
        "duration_s" : round(frames / fps, 1),
    }
    cap.release()
    return info


def camera_available(index: int = 0) -> bool:
    """Return True if a camera at *index* can be opened."""
    cap       = cv2.VideoCapture(index)
    available = cap.isOpened()
    cap.release()
    return available

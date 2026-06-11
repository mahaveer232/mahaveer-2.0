"""
detector.py — YOLOv8-based helmet & rider detection engine.

Downloads a pre-trained helmet detection model from HuggingFace on first run.
Falls back gracefully to the standard YOLOv8-COCO model if download fails.
"""

import os
import sys
import cv2
import numpy as np
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    MODEL_DIR, HELMET_MODEL_PATH, HELMET_MODEL_URL,
    CONFIDENCE_THRESHOLD, IOU_THRESHOLD
)

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("[DETECTOR] ERROR: ultralytics not installed. Run: pip install ultralytics")


# ─── Class-name → helmet-status mapping ───────────────────────────────────────
# Handles different naming conventions across helmet detection models
_HELMET_POSITIVE = {
    'helmet', 'hardhat', 'hard_hat', 'with_helmet', 'safety_helmet',
    'wearing_helmet', 'helmet_on', 'with-helmet',
}
_HELMET_NEGATIVE = {
    'no_helmet', 'no-helmet', 'without_helmet', 'no_hardhat', 'no-hardhat',
    'head', 'bare_head', 'without-helmet', 'no helmet', 'no hardhat',
}


def _classify_class(name: str):
    """
    Returns True  → has helmet
            False → no helmet
            None  → unrelated class (skip)
    """
    n = name.lower().strip().replace(' ', '_').replace('-', '_')

    if n in _HELMET_POSITIVE:
        return True
    if n in _HELMET_NEGATIVE:
        return False

    # Fuzzy: name contains 'helmet' but NOT 'no'/'without'
    if 'helmet' in n and 'no' not in n and 'without' not in n:
        return True
    # Fuzzy: starts with 'no' and contains 'helmet'/'hardhat'
    if ('no_' in n or 'without' in n) and ('helmet' in n or 'hardhat' in n):
        return False

    return None   # e.g. 'car', 'person', 'motorcycle' – ignore


# ─── Color constants (BGR) ────────────────────────────────────────────────────
GREEN = (34, 197, 94)    # Helmet detected
RED   = (59, 46, 239)    # No Helmet  (BGR of #EF2E3B)
WHITE = (255, 255, 255)


class HelmetDetector:
    """
    Loads a YOLOv8 helmet detection model and processes frames.
    Also uses a secondary YOLOv8-COCO model to detect motorcycles
    so that the OCR engine has vehicle regions to scan.
    """

    def __init__(self):
        if not YOLO_AVAILABLE:
            raise RuntimeError(
                "ultralytics is not installed. Run: pip install ultralytics"
            )
        os.makedirs(MODEL_DIR, exist_ok=True)

        print("[DETECTOR] Loading helmet detection model ...")
        self.helmet_model = self._load_helmet_model()

        print("[DETECTOR] Loading vehicle detection model (YOLOv8n COCO) ...")
        self.vehicle_model = YOLO("yolov8n.pt")   # auto-downloaded by ultralytics

        # Build index → helmet_status map
        self.helmet_names = self.helmet_model.names   # {int: str}
        self._idx_map     = {}   # int → True/False/None
        for idx, name in self.helmet_names.items():
            self._idx_map[idx] = _classify_class(name)

        # Log model info
        has_classes    = [n for i,n in self.helmet_names.items() if self._idx_map[i] is True]
        no_has_classes = [n for i,n in self.helmet_names.items() if self._idx_map[i] is False]
        print(f"[DETECTOR]   Helmet classes   : {has_classes}")
        print(f"[DETECTOR]   No-Helmet classes: {no_has_classes}")

        # COCO class IDs for motorcycles / bikes
        self._vehicle_cls = [3, 1]   # 3=motorcycle, 1=bicycle

    # ──────────────────────────────────────────────────────────────────────────
    # Model loading
    # ──────────────────────────────────────────────────────────────────────────

    def _load_helmet_model(self) -> "YOLO":
        if os.path.exists(HELMET_MODEL_PATH):
            print(f"[DETECTOR]   Found local model: {HELMET_MODEL_PATH}")
            return YOLO(HELMET_MODEL_PATH)

        print("[DETECTOR]   Model not found locally. Downloading from HuggingFace ...")
        try:
            self._download(HELMET_MODEL_URL, HELMET_MODEL_PATH)
            return YOLO(HELMET_MODEL_PATH)
        except Exception as exc:
            print(f"[DETECTOR]   Download failed ({exc}). "
                  f"Using base YOLOv8n (COCO) as fallback — helmet accuracy will be limited.")
            # Remove incomplete file if present
            if os.path.exists(HELMET_MODEL_PATH):
                os.remove(HELMET_MODEL_PATH)
            return YOLO("yolov8n.pt")

    @staticmethod
    def _download(url: str, dest: str):
        with requests.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            total    = int(r.headers.get("content-length", 0))
            written  = 0
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=16384):
                    f.write(chunk)
                    written += len(chunk)
                    if total:
                        pct = 100 * written / total
                        bar = "█" * int(pct // 5) + "░" * (20 - int(pct // 5))
                        print(f"\r  [{bar}] {pct:5.1f}%", end="", flush=True)
        print(f"\n[DETECTOR]   Saved → {dest}")

    # ──────────────────────────────────────────────────────────────────────────
    # Frame processing
    # ──────────────────────────────────────────────────────────────────────────

    def detect_frame(self, frame: np.ndarray):
        """
        Run helmet detection on one frame.

        Returns
        -------
        annotated : np.ndarray   — frame with bounding boxes drawn
        detections: list[dict]   — each dict has keys:
            bbox       : [x1, y1, x2, y2]
            has_helmet : bool
            confidence : float
            class_name : str
        """
        annotated  = frame.copy()
        detections = []
        h, w       = frame.shape[:2]

        results = self.helmet_model.track(
            frame,
            conf    = CONFIDENCE_THRESHOLD,
            iou     = IOU_THRESHOLD,
            persist = True,
            verbose = False,
        )

        for result in results:
            for box in result.boxes:
                cls_id     = int(box.cls[0])
                conf       = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                track_id   = int(box.id[0]) if box.id is not None else -1

                # Clamp to frame bounds
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)

                class_name = self.helmet_names.get(cls_id, "unknown")
                has_helmet = self._idx_map.get(cls_id)

                if has_helmet is None:
                    continue    # Unrelated detection (vehicle, person, etc.)

                color      = GREEN if has_helmet else RED
                label_text = f"{'Helmet Detected' if has_helmet else 'No Helmet'}  {conf:.0%}"

                # ── Bounding box ───────────────────────────────────────────────
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

                # ── Label background pill ──────────────────────────────────────
                (tw, th), baseline = cv2.getTextSize(
                    label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1
                )
                pad   = 5
                lx    = x1
                ly    = max(y1 - th - 2 * pad, 0)
                cv2.rectangle(
                    annotated,
                    (lx, ly),
                    (lx + tw + 2 * pad, ly + th + 2 * pad),
                    color, -1
                )
                cv2.putText(
                    annotated, label_text,
                    (lx + pad, ly + th + pad - 1),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, WHITE, 1, cv2.LINE_AA
                )

                detections.append({
                    "bbox"       : [x1, y1, x2, y2],
                    "has_helmet" : has_helmet,
                    "confidence" : conf,
                    "class_name" : class_name,
                    "track_id"   : track_id,
                })

        # ── Status overlay bar at bottom ───────────────────────────────────────
        n_helmet    = sum(1 for d in detections if d["has_helmet"])
        n_no_helmet = sum(1 for d in detections if not d["has_helmet"])

        overlay = annotated.copy()
        cv2.rectangle(overlay, (0, h - 32), (w, h), (15, 20, 35), -1)
        cv2.addWeighted(overlay, 0.75, annotated, 0.25, 0, annotated)

        status_text = (
            f"  Helmet: {n_helmet}   |   No Helmet: {n_no_helmet}"
            f"   |   Total Detected: {len(detections)}"
        )
        cv2.putText(
            annotated, status_text,
            (8, h - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.50, (200, 210, 220), 1, cv2.LINE_AA
        )

        return annotated, detections

    def detect_vehicles(self, frame: np.ndarray):
        """
        Detect motorcycles/bicycles using the COCO model.
        Used to extract regions for number-plate OCR.
        """
        results  = self.vehicle_model(
            frame,
            classes = self._vehicle_cls,
            conf    = 0.30,
            verbose = False,
        )
        vehicles = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                vehicles.append({
                    "bbox"       : [x1, y1, x2, y2],
                    "confidence" : float(box.conf[0]),
                })
        return vehicles

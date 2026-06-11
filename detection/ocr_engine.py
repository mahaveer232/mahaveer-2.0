"""
ocr_engine.py — EasyOCR-based number plate reader for Indian vehicles.

Searches below/around a rider's bounding box for plate text,
applies image preprocessing for better accuracy, and validates
extracted text against the Indian number plate format.
"""

import cv2
import re
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import easyocr
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("[OCR] WARNING: easyocr not installed. Run: pip install easyocr")

# Indian plate pattern examples: MH12AB1234 | DL 5S AF 1234 | KA-03-MJ-7654
_PLATE_PATTERN = re.compile(
    r'[A-Z]{2}\s*\d{1,2}\s*[A-Z]{1,3}\s*\d{4}',
    re.IGNORECASE
)

# Characters allowed on Indian number plates
_ALLOWLIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "


class OCREngine:
    """
    Wraps EasyOCR for number-plate text extraction.
    GPU is disabled by default for broad compatibility.
    """

    def __init__(self):
        self.reader = None
        if OCR_AVAILABLE:
            print("[OCR] Initialising EasyOCR (first run downloads ~200 MB language model) ...")
            try:
                self.reader = easyocr.Reader(
                    ['en'],
                    gpu     = True,
                    verbose = False,
                )
                print("[OCR] EasyOCR ready.")
            except Exception as exc:
                print(f"[OCR] Failed to initialise EasyOCR: {exc}")
        else:
            print("[OCR] EasyOCR unavailable — plate reading disabled.")

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def read_plate_from_frame(
        self,
        frame: np.ndarray,
        rider_bbox: list,
    ) -> str | None:
        """
        Attempt to read an Indian number plate from the region
        below/around *rider_bbox* = [x1, y1, x2, y2].

        Returns a cleaned plate string (e.g. "MH12AB1234") or None.
        """
        if self.reader is None:
            return None

        h, w    = frame.shape[:2]
        x1, y1, x2, y2 = rider_bbox
        bh      = y2 - y1
        bw      = x2 - x1

        # Search region: Since rider_bbox is now the motorcycle,
        # the plate is typically in the bottom half of the bounding box.
        sx1 = max(0, x1)
        sx2 = min(w, x2)
        sy1 = max(0, y1 + int(bh * 0.35))  # Start from 35% down the bike
        sy2 = min(h, y2 + int(bh * 0.15))  # Allow slightly below the bike

        roi = frame[sy1:sy2, sx1:sx2]
        if roi.size == 0 or roi.shape[0] < 10 or roi.shape[1] < 20:
            return None

        # Run OCR on multiple preprocessed versions for best coverage
        candidates = []
        for processed in self._preprocess(roi):
            try:
                texts = self.reader.readtext(
                    processed,
                    detail    = 0,
                    allowlist = _ALLOWLIST,
                    paragraph = False,
                )
                raw = " ".join(texts).upper()
                plate = self._extract_plate(raw)
                if plate:
                    candidates.append(plate)
            except Exception:
                pass

        if candidates:
            # Return the most-seen candidate
            return max(set(candidates), key=candidates.count)

        return None

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _preprocess(roi: np.ndarray) -> list:
        """
        Return a list of preprocessed image variants to maximise OCR hits.
        """
        results = []

        # Scale up for small regions
        scale = max(1.0, 80 / max(roi.shape[0], 1))
        resized = cv2.resize(roi, None, fx=scale, fy=scale,
                             interpolation=cv2.INTER_CUBIC)

        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

        # Version 1: Adaptive threshold (good for varying lighting)
        adaptive = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        results.append(adaptive)

        # Version 2: Otsu threshold (good for high contrast plates)
        _, otsu = cv2.threshold(gray, 0, 255,
                                cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        results.append(otsu)

        # Version 3: Enhanced contrast (CLAHE)
        clahe   = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        results.append(enhanced)

        return results

    @staticmethod
    def _extract_plate(text: str) -> str | None:
        """
        Try to find and normalise an Indian number plate in *text*.
        Returns a compact string like "MH12AB1234" or None.
        """
        cleaned = re.sub(r'[^A-Z0-9\s]', '', text.upper())

        # Try strict pattern first
        match = _PLATE_PATTERN.search(cleaned)
        if match:
            plate = re.sub(r'\s+', '', match.group(0)).upper()
            if len(plate) >= 8:
                return plate

        # Loose fallback: any 8-10 char alphanumeric block
        tokens  = cleaned.split()
        compact = ''.join(tokens)
        if 8 <= len(compact) <= 12 and re.search(r'[A-Z]', compact) \
                and re.search(r'\d', compact):
            return compact[:10]

        return None

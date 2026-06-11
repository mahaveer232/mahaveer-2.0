"""
app.py — Mahaveer 2.0 · AI Helmet Detection System
Flask backend with threaded video processing and MJPEG streaming.

Run:  python app.py
Open: http://localhost:5000
"""

import os
import sys
import time
import threading
import cv2
import numpy as np
from datetime        import datetime
from flask           import Flask, render_template, Response, request, jsonify
from flask_cors      import CORS
from werkzeug.utils  import secure_filename

# ─── Local imports ─────────────────────────────────────────────────────────────
from config import *
from detection.detector        import HelmetDetector
from detection.ocr_engine      import OCREngine
from detection.video_processor import get_video_info, camera_available
from database.db_manager       import DatabaseManager
from notifications.email_sender import EmailSender

# ─── Flask setup ──────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["SECRET_KEY"]         = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
CORS(app)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MODEL_DIR,     exist_ok=True)

# ─── System initialisation ────────────────────────────────────────────────────
print("\n" + "=" * 62)
print("  MAHAVEER 2.0 — AI Highway Helmet Detection System")
print("=" * 62)
print("[SYSTEM] Initialising modules …\n")

detector     = HelmetDetector()
ocr_engine   = OCREngine()
db_manager   = DatabaseManager()
email_sender = EmailSender()

print("\n[SYSTEM] All modules ready. Starting Flask server …\n")

# ─── Shared processing state (protected by _lock) ─────────────────────────────
_lock        = threading.Lock()
_frame: np.ndarray | None = None       # Latest annotated frame
_violations: list         = []         # Violation log (newest first)
_stats = {
    "total_detected" : 0,
    "helmet_count"   : 0,
    "no_helmet_count": 0,
    "challans_sent"  : 0,
    "fps"            : 0.0,
    "is_running"     : False,
    "source_label"   : "—",
}
_emails_sent: set     = set()
_processed_tracks: set = set()
_proc_thread: threading.Thread | None = None
_stop_event           = threading.Event()


# ─── Background processing loop ───────────────────────────────────────────────

def _process_video(source, is_camera: bool = False):
    global _frame, _violations, _stats, _emails_sent

    cap = cv2.VideoCapture(0 if is_camera else str(source))
    if not cap.isOpened():
        print(f"[VIDEO] Cannot open source: {source}")
        with _lock:
            _stats["is_running"] = False
        return

    with _lock:
        _stats["is_running"]   = True
        _stats["source_label"] = "Live Camera" if is_camera else os.path.basename(str(source))

    frame_n = 0
    fps_t   = time.time()
    fps_cnt = 0

    print(f"[VIDEO] Processing started — source: {source}")

    while not _stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            if not is_camera:
                # Loop the video file
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            break

        frame_n += 1

        # Prevent browser MJPEG stream crash by setting the correct resolution immediately
        if frame_n == 1:
            with _lock:
                _frame = frame.copy()

        # ── YOLO detection ────────────────────────────────────────────────────
        try:
            annotated, detections = detector.detect_frame(frame)
        except Exception as exc:
            print(f"[VIDEO] Detection error: {exc}")
            with _lock:
                _frame = frame.copy()
            continue

        # ── Process each detection ────────────────────────────────────────────
        for det in detections:
            track_id = det.get("track_id", -1)
            
            with _lock:
                is_new = (track_id == -1) or (track_id not in _processed_tracks)
                if is_new and track_id != -1:
                    _processed_tracks.add(track_id)
                    _stats["total_detected"] += 1
                    if det["has_helmet"]:
                        _stats["helmet_count"] += 1
                    else:
                        _stats["no_helmet_count"] += 1

            # Only perform OCR on new no-helmet violators
            if det["has_helmet"] or not is_new:
                continue

            # ── No-Helmet path ────────────────────────────────────────────────

            # Find the motorcycle for this rider
            vehicles = detector.detect_vehicles(frame)
            best_bike = None
            hx1, hy1, hx2, hy2 = det["bbox"]
            for v in vehicles:
                vx1, vy1, vx2, vy2 = v["bbox"]
                # Heuristic: rider head is mostly within horizontal bounds, and vertically above bottom of bike
                if vx1 - 50 <= hx1 and hx2 <= vx2 + 50 and vy1 - 50 <= hy1 <= vy2:
                    best_bike = v["bbox"]
                    break

            plate_bbox = best_bike if best_bike else det["bbox"]

            # OCR for number plate
            plate      = None
            owner_info = None
            email_sent = False

            try:
                plate = ocr_engine.read_plate_from_frame(frame, plate_bbox)
            except Exception as exc:
                print(f"[OCR] Error: {exc}")

            if plate:
                try:
                    owner_info = db_manager.get_vehicle_by_plate(plate)
                except Exception as exc:
                    print(f"[DB] Lookup error: {exc}")

                if owner_info:
                    with _lock:
                        already = plate in _emails_sent

                    if not already:
                        success = email_sender.send_challan(owner_info, plate)
                        if success:
                            with _lock:
                                _emails_sent.add(plate)
                                _stats["challans_sent"] += 1
                            email_sent = True
                            try:
                                db_manager.log_challan(
                                    plate,
                                    owner_info.get("owner_name", "Unknown"),
                                    owner_info.get("email", "N/A"),
                                    email_sent=True,
                                )
                            except Exception as exc:
                                print(f"[DB] Challan log error: {exc}")

            violation = {
                "timestamp"  : datetime.now().strftime("%d-%m %H:%M:%S"),
                "plate"      : plate or "—",
                "owner"      : owner_info.get("owner_name", "Unknown") if owner_info else "Unknown",
                "vehicle"    : owner_info.get("vehicle_model", "—")     if owner_info else "—",
                "email"      : owner_info.get("email", "N/A")           if owner_info else "N/A",
                "email_sent" : email_sent,
                "confidence" : f"{det['confidence']:.0%}",
            }
            with _lock:
                _violations.insert(0, violation)
                if len(_violations) > 100:
                    _violations.pop()

        # ── FPS counter ───────────────────────────────────────────────────────
        fps_cnt += 1
        elapsed  = time.time() - fps_t
        if elapsed >= 1.0:
            with _lock:
                _stats["fps"] = round(fps_cnt / elapsed, 1)
            fps_cnt = 0
            fps_t   = time.time()

        with _lock:
            _frame = annotated

        # Throttle to avoid burning CPU
        time.sleep(max(0.0, 1 / MAX_STREAM_FPS - 0.008))

    cap.release()
    with _lock:
        _stats["is_running"] = False
    print("[VIDEO] Processing stopped.")


def _start_processor(source, is_camera: bool = False):
    global _proc_thread, _stop_event, _frame, _violations, _stats, _emails_sent

    # Stop existing thread
    _stop_event.set()
    if _proc_thread and _proc_thread.is_alive():
        _proc_thread.join(timeout=5)

    # Reset state
    _stop_event = threading.Event()
    with _lock:
        _frame      = None
        _violations = []
        _emails_sent = set()
        _processed_tracks = set()
        for k in ("total_detected", "helmet_count", "no_helmet_count",
                  "challans_sent", "fps"):
            _stats[k] = 0

    _proc_thread = threading.Thread(
        target  = _process_video,
        args    = (source, is_camera),
        daemon  = True,
        name    = "VideoProcessor",
    )
    _proc_thread.start()


# ─── MJPEG frame generator ────────────────────────────────────────────────────

def _gen_frames():
    """Yield MJPEG frames indefinitely for the /video_feed endpoint."""
    # Placeholder shown when no source is active
    _WAIT = np.zeros((480, 854, 3), dtype=np.uint8)
    cv2.putText(_WAIT, "Waiting for video source ...",
                (170, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.85,
                (80, 90, 110), 2, cv2.LINE_AA)
    cv2.putText(_WAIT, "Click  'Load Sample Video'  or  'Upload Video'  to begin.",
                (60, 285), cv2.FONT_HERSHEY_SIMPLEX, 0.50,
                (55, 65, 85), 1, cv2.LINE_AA)

    while True:
        with _lock:
            f = _frame

        send = f if f is not None else _WAIT
        ok, buf = cv2.imencode(".jpg", send,
                               [cv2.IMWRITE_JPEG_QUALITY, 83])
        if ok:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + buf.tobytes()
                + b"\r\n"
            )
        time.sleep(1 / MAX_STREAM_FPS)


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video_feed")
def video_feed():
    return Response(
        _gen_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/api/start_sample", methods=["POST"])
def start_sample():
    if not os.path.exists(SAMPLE_VIDEO):
        return jsonify({"error": f"Sample video not found: {SAMPLE_VIDEO}"}), 404
    _start_processor(SAMPLE_VIDEO)
    info = get_video_info(SAMPLE_VIDEO) or {}
    return jsonify({"status": "started", "source": "sample", **info})


@app.route("/api/start_camera", methods=["POST"])
def start_camera():
    if not camera_available(0):
        return jsonify({"error": "No camera detected on this machine."}), 404
    _start_processor(0, is_camera=True)
    return jsonify({"status": "started", "source": "camera"})


@app.route("/api/stop", methods=["POST"])
def stop():
    _stop_event.set()
    return jsonify({"status": "stopped"})


@app.route("/api/upload_video", methods=["POST"])
def upload_video():
    if "video" not in request.files:
        return jsonify({"error": "No video field in request"}), 400
    f = request.files["video"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400

    safe_name = f"upload_{int(time.time())}_{secure_filename(f.filename)}"
    save_path = os.path.join(UPLOAD_FOLDER, safe_name)
    f.save(save_path)

    _start_processor(save_path)
    info = get_video_info(save_path) or {}
    return jsonify({
        "status"  : "started",
        "source"  : "upload",
        "filename": safe_name,
        **info,
    })


@app.route("/api/violations")
def get_violations():
    with _lock:
        return jsonify(_violations[:50])


@app.route("/api/stats")
def get_stats():
    with _lock:
        return jsonify(dict(_stats))


@app.route("/api/vehicles")
def get_vehicles():
    return jsonify(db_manager.get_all_vehicles())


@app.route("/api/challans")
def get_challans():
    return jsonify(db_manager.get_all_challans())


@app.route("/api/db_stats")
def get_db_stats():
    return jsonify(db_manager.get_db_stats())


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n{'─'*62}")
    print(f"  Dashboard → http://localhost:{PORT}")
    print(f"  Press Ctrl+C to stop")
    print(f"{'─'*62}\n")
    app.run(
        host     = "0.0.0.0",
        port     = PORT,
        debug    = False,
        threaded = True,
    )

import os

# ─── Base Directory ────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Email Configuration ───────────────────────────────────────────────────────
# If email sending fails with "Authentication Error", do this:
#   1. Enable 2-Step Verification at https://myaccount.google.com/security
#   2. Generate an App Password at https://myaccount.google.com/apppasswords
#   3. Replace EMAIL_PASSWORD below with the 16-character App Password (no spaces)
EMAIL_SENDER    = "rtoheadquarters@gmail.com"
EMAIL_PASSWORD  = "Veer@112005"          # ← Replace with App Password if 2FA is on
EMAIL_SMTP_HOST = "smtp.gmail.com"
EMAIL_SMTP_PORT = 587

# ─── File Paths ────────────────────────────────────────────────────────────────
MODEL_DIR         = os.path.join(BASE_DIR, "models")
HELMET_MODEL_PATH = os.path.join(MODEL_DIR, "helmet_detection.pt")
DB_PATH           = os.path.join(BASE_DIR, "database", "traffic_system.db")
UPLOAD_FOLDER     = os.path.join(BASE_DIR, "static", "uploads")
SAMPLE_VIDEO      = os.path.join(BASE_DIR, "14571160_1920_1080_60fps.mp4")

# Publicly hosted helmet detection model (YOLOv8n, no API key required)
HELMET_MODEL_URL = (
    "https://huggingface.co/iam-tsr/yolov8n-helmet-detection"
    "/resolve/main/best.pt"
)

# ─── Detection Settings ────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD = 0.40   # Min confidence to count a detection
IOU_THRESHOLD        = 0.45   # Non-max suppression IoU threshold
FRAME_SKIP           = 2      # Run detection every Nth frame (higher = faster)
MAX_STREAM_FPS       = 20     # Max FPS for MJPEG stream

# ─── Flask Settings ────────────────────────────────────────────────────────────
SECRET_KEY         = "mahaveer_helmet_detection_system_2024"
MAX_CONTENT_LENGTH = 500 * 1024 * 1024   # 500 MB upload limit
PORT               = 5000

# ─── Challan Settings ─────────────────────────────────────────────────────────
FINE_AMOUNT_INR = 1000
RTO_OFFICE      = "Regional Transport Office, Highway Monitoring Cell"

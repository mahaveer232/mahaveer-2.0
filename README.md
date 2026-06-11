# 🦺 Mahaveer 2.0 — AI Highway Helmet Detection System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Object%20Detection-00BFFF?style=for-the-badge)
![Flask](https://img.shields.io/badge/Flask-Web%20App-000000?style=for-the-badge&logo=flask&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)

**Real-time AI system that detects helmetless riders, reads number plates via OCR, and automatically sends e-challans.**

</div>

---

## 🔍 What Does This Project Do?

Mahaveer 2.0 is an AI-powered traffic safety system that:

1. 🎥 **Watches a video / live camera feed** of a highway or road
2. 🧠 **Detects riders** — whether they are wearing a helmet or NOT
3. 🔢 **Reads the number plate** of the violating vehicle using OCR
4. 📧 **Automatically sends an e-challan** (fine notice) to the vehicle owner's email
5. 📊 **Shows a live web dashboard** with real-time stats and violation logs

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🎯 Real-time Detection | YOLOv8 detects helmet/no-helmet at high FPS |
| 🔢 OCR Number Plate Reading | Automatically reads vehicle number plates |
| 📧 Auto E-Challan | Sends challan email to registered vehicle owner |
| 📊 Live Dashboard | Flask web UI with live MJPEG video stream |
| 🗄️ Database Logging | All violations stored in SQLite database |
| 📹 Multiple Sources | Supports video file, live camera, and uploads |
| 🔄 Vehicle Tracking | Tracks each rider — no duplicate challans |

---

## 🛠️ Tech Stack

```
AI/ML     →  YOLOv8 (Ultralytics), Custom Trained Model
Vision    →  OpenCV, NumPy
Backend   →  Python 3.8+, Flask, Flask-CORS
Database  →  SQLite
Frontend  →  HTML5, CSS3, JavaScript (Live MJPEG Stream)
Email     →  SMTP (Auto E-Challan Sender)
```

---

## 📸 How It Works

```
[Video/Camera Feed]
       ↓
[YOLOv8 Detection] — Detects: Rider, Helmet, No-Helmet, Motorcycle
       ↓
[OCR Engine] — Reads number plate of violating vehicle
       ↓
[Database Lookup] — Finds owner name + email
       ↓
[Auto E-Challan] — Sends fine notice to owner's email
       ↓
[Live Dashboard] — Shows real-time stats + violation log
```

---

## 🖼️ Screenshots & Demo

| Dashboard | Live Detection |
|---|---|
| ![Dashboard](screenshots/dashboard.png) | ![Detection](screenshots/detection.png) |

| Violations Log | E-Challan Sent |
|---|---|
| ![Violations](screenshots/violations.png) | ![Challan](screenshots/challan.png) |

NOTE:- If you cant able to see screenshot plz open the folder named screenshot there you can see the screenshot of project
---

## 📦 Installation & Setup

### Step 1 — Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/mahaveer-2.0.git
cd mahaveer-2.0
```

### Step 2 — Create virtual environment
```bash
python -m venv .venv

# Windows:
.venv\Scripts\activate

# Mac/Linux:
source .venv/bin/activate
```

### Step 3 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Setup the database
```bash
python setup_db.py
```

### Step 5 — Run the application
```bash
python app.py
```

### Step 6 — Open in browser
```
http://localhost:5000
```

---

## 🗂️ Project Structure

```
Mahaveer 2.0/
│
├── app.py                  # Main Flask application
├── config.py               # Configuration settings
├── setup_db.py             # Database initializer
├── requirements.txt        # Python dependencies
│
├── detection/              # AI detection modules
│   ├── detector.py         # YOLOv8 helmet detector
│   ├── ocr_engine.py       # Number plate OCR
│   └── video_processor.py  # Video stream handler
│
├── database/               # Database management
│   └── db_manager.py       # SQLite operations
│
├── notifications/          # Alert system
│   └── email_sender.py     # Auto e-challan emailer
│
├── templates/              # HTML web pages
└── static/                 # CSS, JS, images
```

---

## ⚙️ Configuration

Edit `config.py` to set:
- Email SMTP settings (for challan sending)
- Detection confidence threshold
- Video stream FPS
- Upload folder path

---

## 🎯 Use Cases

- 🏛️ **Traffic Police Departments** — Automate helmet violation detection
- 🏗️ **Industrial Safety** — Monitor worker PPE compliance
- 🏙️ **Smart City Projects** — Integrate with existing CCTV infrastructure
- 🛣️ **Highway Monitoring** — Remote road safety enforcement

---

## 📝 Note on Model Weights

The custom-trained model weights (`helmet_detection.pt`) are **not included** in this repository to protect intellectual property.

The base YOLOv8 weights can be downloaded from [Ultralytics](https://ultralytics.com/).

---

## 👨‍💻 Developer

**Mahaveer Sudhakar Saitwal**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0077B5?style=for-the-badge&logo=linkedin)](https://linkedin.com/in/www.linkedin.com/in/mahaveer-saitwal-6a7394316)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-181717?style=for-the-badge&logo=github)](https://github.com/mahaveer232)

---

## 📄 License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
⭐ If you find this project useful, please give it a star!
</div>

"""
email_sender.py — Gmail SMTP challan email automation.

Sends a formatted HTML challan email to vehicle owners detected
without helmets. Screenshot attachment and payment links are excluded.
"""

import smtplib
import os
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text       import MIMEText
from datetime              import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    EMAIL_SENDER, EMAIL_PASSWORD,
    EMAIL_SMTP_HOST, EMAIL_SMTP_PORT,
    FINE_AMOUNT_INR, RTO_OFFICE,
)


# ─── HTML Email Template ───────────────────────────────────────────────────────
_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Traffic Challan Notice</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',Arial,sans-serif;background:#eef2f7;padding:24px}}
  .wrap{{max-width:600px;margin:0 auto;background:#fff;border-radius:14px;
         overflow:hidden;box-shadow:0 6px 30px rgba(0,0,0,.12)}}
  /* Header */
  .hdr{{background:linear-gradient(135deg,#b91c1c 0%,#7f1d1d 100%);
        padding:32px 28px;text-align:center;color:#fff}}
  .hdr .icon{{font-size:44px;line-height:1;margin-bottom:10px}}
  .hdr h1{{font-size:20px;font-weight:700;letter-spacing:.5px;margin-bottom:6px}}
  .hdr p{{font-size:12px;opacity:.8;margin-bottom:12px}}
  .badge{{display:inline-block;background:rgba(255,255,255,.18);
          border:1px solid rgba(255,255,255,.35);border-radius:20px;
          padding:4px 16px;font-size:11px;letter-spacing:.8px;font-weight:600}}
  /* Body */
  .body{{padding:28px}}
  .alert{{background:#fef2f2;border:1px solid #fecaca;border-left:4px solid #dc2626;
          border-radius:8px;padding:14px 18px;margin-bottom:24px}}
  .alert-title{{color:#b91c1c;font-weight:700;font-size:14px;margin-bottom:4px}}
  .alert-body{{color:#7f1d1d;font-size:13px;line-height:1.5}}
  .sec-title{{font-size:11px;font-weight:700;color:#6b7280;
              text-transform:uppercase;letter-spacing:.7px;
              margin:22px 0 10px;padding-bottom:6px;
              border-bottom:1px solid #f3f4f6}}
  table.info{{width:100%;border-collapse:collapse}}
  table.info td{{padding:9px 10px;font-size:13.5px;
                  border-bottom:1px solid #f3f4f6;vertical-align:top}}
  table.info td:first-child{{color:#6b7280;font-weight:600;width:155px}}
  table.info td:last-child{{color:#111827;font-weight:500}}
  /* Fine box */
  .fine-box{{background:linear-gradient(135deg,#1e3a5f,#1e40af);
             border-radius:12px;padding:22px;text-align:center;margin:24px 0;color:#fff}}
  .fine-lbl{{font-size:11px;letter-spacing:1px;opacity:.75;
             text-transform:uppercase;margin-bottom:8px}}
  .fine-amt{{font-size:38px;font-weight:800;letter-spacing:-1px}}
  .fine-sub{{font-size:12px;opacity:.65;margin-top:6px}}
  /* Violation tag */
  .vtag{{display:inline-block;background:#fef2f2;border:1px solid #fecaca;
          color:#dc2626;border-radius:6px;padding:3px 10px;
          font-size:12px;font-weight:700}}
  /* Footer */
  .footer{{background:#f9fafb;border-top:1px solid #f3f4f6;
           padding:20px 28px;text-align:center}}
  .footer p{{font-size:11.5px;color:#9ca3af;line-height:1.7}}
  .footer strong{{color:#6b7280}}
  .challan-id{{font-family:monospace;font-size:12px;
               color:#4b5563;background:#f3f4f6;
               border-radius:4px;padding:2px 8px}}
</style>
</head>
<body>
<div class="wrap">

  <div class="hdr">
    <div class="icon">🚔</div>
    <h1>TRAFFIC VIOLATION CHALLAN</h1>
    <p>Issued under Motor Vehicles Act, 1988 · Section 129</p>
    <span class="badge">AI HIGHWAY MONITORING SYSTEM</span>
  </div>

  <div class="body">

    <div class="alert">
      <div class="alert-title">⚠️  Helmet Violation Detected</div>
      <div class="alert-body">
        Your vehicle was captured by the AI Highway Monitoring System
        without a helmet. Riding without a helmet is a punishable offence
        under the Motor Vehicles Act, 1988.
      </div>
    </div>

    <div class="sec-title">👤  Owner Information</div>
    <table class="info">
      <tr><td>Owner Name</td>   <td><strong>{owner_name}</strong></td></tr>
      <tr><td>Email</td>        <td>{email}</td></tr>
      <tr><td>Phone</td>        <td>{phone}</td></tr>
      <tr><td>Address</td>      <td>{address}</td></tr>
    </table>

    <div class="sec-title">🏍️  Vehicle Details</div>
    <table class="info">
      <tr><td>Registration No.</td><td><strong>{plate_number}</strong></td></tr>
      <tr><td>Vehicle Model</td>   <td>{vehicle_model}</td></tr>
      <tr><td>Detection Date</td>  <td>{date}</td></tr>
      <tr><td>Detection Time</td>  <td>{time}</td></tr>
      <tr><td>Violation</td>
          <td><span class="vtag">Riding without Helmet</span></td></tr>
    </table>

    <div class="fine-box">
      <div class="fine-lbl">Challan Fine Amount</div>
      <div class="fine-amt">₹ {fine_amount}/-</div>
      <div class="fine-sub">Due within 30 days of this notice</div>
    </div>

    <p style="font-size:12.5px;color:#6b7280;text-align:center;line-height:1.6">
      This challan has been generated automatically by the AI Highway Monitoring
      System.<br>For queries or disputes, contact your nearest RTO office.<br>
      <strong>{rto_office}</strong>
    </p>

  </div>

  <div class="footer">
    <p>
      <strong>Regional Transport Office · Highway Monitoring Cell</strong><br>
      This is a system-generated notice. Do not reply to this email.<br>
      Challan Reference: <span class="challan-id">CHN-{challan_id}</span>
    </p>
  </div>

</div>
</body>
</html>"""


class EmailSender:
    """Sends HTML challan emails via Gmail SMTP with STARTTLS."""

    def __init__(self):
        self.sender          = EMAIL_SENDER
        self.password        = EMAIL_PASSWORD
        self._challan_serial = 10000

    def send_challan(self, owner_info: dict, plate_number: str) -> bool:
        """
        Build and send a challan email to *owner_info['email']*.

        Parameters
        ----------
        owner_info  : dict with keys name, email, phone, address, vehicle_model
        plate_number: detected plate string

        Returns True on success, False on failure.
        """
        self._challan_serial += 1
        now        = datetime.now()
        challan_id = f"{self._challan_serial:05d}"

        html = _TEMPLATE.format(
            owner_name    = owner_info.get("owner_name", "Vehicle Owner"),
            email         = owner_info.get("email", "N/A"),
            phone         = owner_info.get("phone", "N/A"),
            address       = owner_info.get("address", "N/A"),
            plate_number  = plate_number,
            vehicle_model = owner_info.get("vehicle_model", "N/A"),
            date          = now.strftime("%d %B %Y"),
            time          = now.strftime("%I:%M %p"),
            fine_amount   = FINE_AMOUNT_INR,
            rto_office    = RTO_OFFICE,
            challan_id    = challan_id,
        )

        msg              = MIMEMultipart("alternative")
        msg["Subject"]   = (
            f"\U0001f6a8 Traffic Challan | No Helmet | "
            f"{plate_number} | \u20b9{FINE_AMOUNT_INR}"
        )
        msg["From"]      = self.sender
        msg["To"]        = owner_info["email"]
        msg.attach(MIMEText(html, "html"))

        try:
            with smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, timeout=25) as srv:
                srv.ehlo()
                srv.starttls()
                srv.login(self.sender, self.password)
                srv.sendmail(self.sender, owner_info["email"], msg.as_string())

            print(f"[EMAIL] SENT  Challan {challan_id} sent -> {owner_info['email']}  [{plate_number}]")
            return True

        except smtplib.SMTPAuthenticationError:
            print(
                "[EMAIL] AUTH FAILED!\n"
                "        -> Enable 2-Step Verification on your Google Account,\n"
                "           then create an App Password at:\n"
                "           https://myaccount.google.com/apppasswords\n"
                "        -> Update EMAIL_PASSWORD in config.py with the App Password."
            )
            return False

        except smtplib.SMTPException as exc:
            print(f"[EMAIL] SMTP error: {exc}")
            return False

        except Exception as exc:
            print(f"[EMAIL] Unexpected error: {exc}")
            return False

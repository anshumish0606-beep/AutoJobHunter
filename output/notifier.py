import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from pathlib import Path


class EmailNotifier:
    """
    Sends job report to your email automatically.
    Uses Gmail SMTP with App Password.
    """

    def __init__(self, sender_email: str, sender_app_password: str, recipient_email: str):
        self.sender = sender_email
        self.password = sender_app_password
        self.recipient = recipient_email

    def send_report(self, all_jobs: list, html_report_path: str = None, excel_report_path: str = None):
        """Send job results via email with attachments."""
        print(f"\n📩 Sending report to {self.recipient}...")

        try:
            msg = MIMEMultipart("alternative")
            timestamp = datetime.now().strftime("%d %b %Y, %I:%M %p")
            msg["Subject"] = f"🤖 AutoJobHunter — {len(all_jobs)} Jobs Found | {timestamp}"
            msg["From"] = self.sender
            msg["To"] = self.recipient

            # Build email body
            high_jobs = [j for j in all_jobs if j.get("relevance") == "high"]
            medium_jobs = [j for j in all_jobs if j.get("relevance") == "medium"]

            html_body = self._build_email_html(all_jobs, high_jobs, medium_jobs, timestamp)
            msg.attach(MIMEText(html_body, "html"))

            # Attach Excel report if available
            if excel_report_path and Path(excel_report_path).exists():
                with open(excel_report_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={Path(excel_report_path).name}")
                msg.attach(part)

            # Send via Gmail SMTP
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.sender, self.password)
                server.sendmail(self.sender, self.recipient, msg.as_string())

            print(f"✅ Email sent successfully to {self.recipient}!")
            return True

        except Exception as e:
            print(f"❌ Email failed: {str(e)}")
            print("💡 Make sure you're using Gmail App Password, not your regular password.")
            return False

    def _build_email_html(self, all_jobs, high_jobs, medium_jobs, timestamp):
        """Build beautiful HTML email body."""

        # Top 10 high-relevance jobs for email preview
        preview_jobs = (high_jobs + medium_jobs)[:10]

        jobs_html = ""
        for job in preview_jobs:
            relevance = job.get("relevance", "medium")
            color = "#2e7d32" if relevance == "high" else "#f57f17"
            link = job.get("apply_link", "#")

            jobs_html += f"""
            <tr>
              <td style="padding:10px;border-bottom:1px solid #f0f0f0;">
                <strong style="color:#1a73e8;">{job.get('title', 'N/A')}</strong><br>
                <span style="color:#555;">{job.get('company', 'N/A')}</span>
              </td>
              <td style="padding:10px;border-bottom:1px solid #f0f0f0;color:#555;">{job.get('location', 'N/A')}</td>
              <td style="padding:10px;border-bottom:1px solid #f0f0f0;">{job.get('portal', 'N/A')}</td>
              <td style="padding:10px;border-bottom:1px solid #f0f0f0;">
                <span style="color:{color};font-weight:bold;">{relevance.upper()}</span>
              </td>
              <td style="padding:10px;border-bottom:1px solid #f0f0f0;">
                <a href="{link}" style="background:#1a73e8;color:white;padding:5px 12px;border-radius:15px;text-decoration:none;font-size:12px;">Apply →</a>
              </td>
            </tr>
"""

        return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:'Segoe UI',sans-serif;background:#f0f2f5;margin:0;padding:20px;">

<div style="max-width:800px;margin:0 auto;background:white;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.1);">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1a73e8,#0d47a1);color:white;padding:30px 40px;">
    <h1 style="margin:0;font-size:24px;">🤖 AutoJobHunter Report</h1>
    <p style="margin:8px 0 0;opacity:0.85;">Generated on {timestamp}</p>
  </div>

  <!-- Stats -->
  <div style="display:flex;gap:15px;padding:20px 40px;background:#f8f9fa;border-bottom:1px solid #e0e0e0;">
    <div style="text-align:center;flex:1;background:white;padding:15px;border-radius:8px;">
      <div style="font-size:28px;font-weight:bold;color:#1a73e8;">{len(all_jobs)}</div>
      <div style="font-size:12px;color:#666;margin-top:4px;">Total Jobs</div>
    </div>
    <div style="text-align:center;flex:1;background:white;padding:15px;border-radius:8px;">
      <div style="font-size:28px;font-weight:bold;color:#2e7d32;">{len(high_jobs)}</div>
      <div style="font-size:12px;color:#666;margin-top:4px;">High Match</div>
    </div>
    <div style="text-align:center;flex:1;background:white;padding:15px;border-radius:8px;">
      <div style="font-size:28px;font-weight:bold;color:#f57f17;">{len(medium_jobs)}</div>
      <div style="font-size:12px;color:#666;margin-top:4px;">Medium Match</div>
    </div>
  </div>

  <!-- Jobs Table -->
  <div style="padding:30px 40px;">
    <h2 style="color:#333;margin-bottom:15px;">Top Matching Jobs</h2>
    <table style="width:100%;border-collapse:collapse;">
      <thead>
        <tr style="background:#f8f9fa;">
          <th style="padding:10px;text-align:left;color:#555;font-size:13px;">Job Title / Company</th>
          <th style="padding:10px;text-align:left;color:#555;font-size:13px;">Location</th>
          <th style="padding:10px;text-align:left;color:#555;font-size:13px;">Portal</th>
          <th style="padding:10px;text-align:left;color:#555;font-size:13px;">Match</th>
          <th style="padding:10px;text-align:left;color:#555;font-size:13px;">Apply</th>
        </tr>
      </thead>
      <tbody>
        {jobs_html}
      </tbody>
    </table>
    <p style="color:#999;font-size:12px;margin-top:15px;">Showing top {len(preview_jobs)} of {len(all_jobs)} jobs. Full report attached as Excel file.</p>
  </div>

  <!-- Footer -->
  <div style="padding:20px 40px;background:#f8f9fa;text-align:center;color:#999;font-size:12px;">
    AutoJobHunter — Running automatically every 6 hours 🚀
  </div>

</div>
</body>
</html>
"""

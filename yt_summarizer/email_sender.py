"""
Send HTML summary emails via SMTP (smtplib).
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

from yt_summarizer.summarize import FinalSummary

logger = logging.getLogger(__name__)


def _ul(items: list[str]) -> str:
    if not items:
        return "<p><em>(none)</em></p>"
    lis = "".join(f"<li>{escape(i)}</li>" for i in items)
    return f"<ul>{lis}</ul>"


def build_summary_email_html(
    video_title: str,
    video_url: str,
    final_summary: FinalSummary,
) -> str:
    """
    Build a minimal, readable HTML body for the daily summary email.
    """
    title_safe = escape(video_title)
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{title_safe}</title></head>
<body style="font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;line-height:1.5;color:#222;">
  <h1 style="font-size:1.25rem;">{title_safe}</h1>
  <p><a href="{escape(video_url)}">Watch on YouTube</a></p>

  <h2>TL;DR</h2>
  {_ul(final_summary.tldr_bullets)}

  <h2>Key insights</h2>
  {_ul(final_summary.all_key_insights)}

  <h2>Main takeaways</h2>
  {_ul(final_summary.main_takeaways)}

  <h2>Timeline</h2>
  {_ul(final_summary.timeline)}

  <hr style="margin-top:2rem;border:none;border-top:1px solid #ddd;"/>
  <p style="font-size:0.85rem;color:#666;">Sent by yt_summarizer</p>
</body>
</html>"""


def send_html_email(
    smtp_host: str,
    smtp_port: int,
    use_tls: bool,
    from_addr: str,
    to_addr: str,
    password: str,
    subject: str,
    html_body: str,
    timeout: float = 60.0,
) -> None:
    """
    Send an HTML email using SMTP authentication.

    Args:
        smtp_host: SMTP server hostname.
        smtp_port: SMTP port (587 typical for STARTTLS).
        use_tls: If True, use ``starttls`` after connect.
        from_addr: From address.
        to_addr: Recipient address.
        password: SMTP password or app password.
        subject: Email subject line.
        html_body: HTML content.
        timeout: Socket timeout in seconds.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    logger.info("Sending email to %s via %s:%s", to_addr, smtp_host, smtp_port)
    with smtplib.SMTP(smtp_host, smtp_port, timeout=timeout) as server:
        if use_tls:
            server.starttls()
        if password:
            server.login(from_addr, password)
        server.sendmail(from_addr, [to_addr], msg.as_string())

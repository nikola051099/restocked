"""
Weekly reorder digest email — the retention hook.

build_digest_html() renders a clean, mobile-friendly email from a recommendations
payload. send_email() ships it via SMTP (skipped gracefully if SMTP isn't
configured). run_digests() walks every installed shop and emails its merchant.
"""
from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .config import settings
from .store import store

LABEL = {"imminent": "Reorder now", "soon": "Order soon", "ok": "Healthy"}
COL = {"imminent": "#e0392b", "soon": "#e6a417", "ok": "#29845a"}


def build_digest_subject(payload: dict) -> str:
    recs = payload.get("recommendations", [])
    now = [r for r in recs if r.get("stockout_risk") == "imminent"]
    if now:
        return f"{len(now)} size{'s' if len(now)!=1 else ''} need reordering this week"
    return "Your weekly inventory forecast"


def build_digest_html(shop: str, payload: dict, app_url: str | None = None) -> str:
    app_url = (app_url or settings.APP_URL).rstrip("/")
    recs = payload.get("recommendations", [])
    now = [r for r in recs if r.get("stockout_risk") == "imminent"]
    soon = [r for r in recs if r.get("stockout_risk") == "soon"]
    total_units = sum(int(r.get("recommended_order_qty", 0)) for r in recs)

    def row(r):
        c = COL.get(r.get("stockout_risk"), "#616161")
        size = r.get("size", ""); color = r.get("color", "")
        qty = int(round(r.get("recommended_order_qty", 0)))
        days = r.get("days_of_cover_left", "")
        days = "365+" if isinstance(days, (int, float)) and days > 365 else days
        return (
            f'<tr>'
            f'<td style="padding:9px 12px;border-bottom:1px solid #ececec;">'
            f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{c};margin-right:8px;"></span>'
            f'<b>{size} · {color}</b></td>'
            f'<td style="padding:9px 12px;border-bottom:1px solid #ececec;color:#616161;">{days} days left</td>'
            f'<td style="padding:9px 12px;border-bottom:1px solid #ececec;text-align:right;"><b>{qty}</b></td>'
            f'</tr>'
        )

    top = (now + soon)[:12]
    rows = "".join(row(r) for r in top) or (
        '<tr><td colspan="3" style="padding:16px;color:#616161;">'
        'Nothing urgent this week — stock levels look healthy.</td></tr>'
    )

    return f"""<!doctype html><html><body style="margin:0;background:#f4f4f5;
      font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#303030;">
    <div style="max-width:560px;margin:0 auto;padding:24px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
        <span style="display:inline-block;width:24px;height:24px;border-radius:6px;background:#303030;color:#fff;
          text-align:center;line-height:24px;font-weight:700;">R</span>
        <span style="font-size:17px;font-weight:600;">Restocked</span>
      </div>
      <p style="color:#616161;font-size:13px;margin:0 0 18px 0;">Weekly reorder forecast for {shop}</p>

      <div style="background:#fff;border:1px solid #e3e3e3;border-radius:10px;padding:18px 20px;margin-bottom:16px;">
        <p style="margin:0 0 4px 0;font-size:15px;">
          <b>{len(now)}</b> size{'s' if len(now)!=1 else ''} need reordering now ·
          <b>{total_units}</b> total units suggested
        </p>
        <p style="margin:0;color:#616161;font-size:13px;">
          Based on size-level demand, current stock and a {payload.get('lead_time_days',30)}-day lead time.</p>
      </div>

      <div style="background:#fff;border:1px solid #e3e3e3;border-radius:10px;overflow:hidden;">
        <table style="width:100%;border-collapse:collapse;font-size:14px;">
          <thead><tr style="background:#fbfbfb;">
            <th style="text-align:left;padding:10px 12px;font-size:11px;letter-spacing:.04em;
              text-transform:uppercase;color:#616161;">Variant</th>
            <th style="text-align:left;padding:10px 12px;font-size:11px;letter-spacing:.04em;
              text-transform:uppercase;color:#616161;">Cover</th>
            <th style="text-align:right;padding:10px 12px;font-size:11px;letter-spacing:.04em;
              text-transform:uppercase;color:#616161;">Order</th>
          </tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>

      <div style="text-align:center;margin:22px 0;">
        <a href="https://admin.shopify.com/store/{shop.split('.')[0]}/apps/{settings.API_KEY}"
           style="background:#303030;color:#fff;text-decoration:none;padding:11px 22px;border-radius:8px;
           font-weight:500;display:inline-block;">Open full dashboard</a>
      </div>
      <p style="color:#8a8a8a;font-size:12px;text-align:center;margin:0;">
        You're receiving this because Restocked is installed on {shop}.</p>
    </div></body></html>"""


def send_email(to_email: str, subject: str, html: str) -> bool:
    """Send one email. Returns True if sent, False if skipped (no SMTP config)."""
    if not settings.SMTP_HOST or not to_email:
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.FROM_EMAIL
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as s:
        s.starttls()
        if settings.SMTP_USER:
            s.login(settings.SMTP_USER, settings.SMTP_PASS)
        s.sendmail(settings.FROM_EMAIL, [to_email], msg.as_string())
    return True


def run_digests() -> dict:
    """Email every installed shop its latest digest. Uses cached last_run."""
    sent, skipped = 0, 0
    for shop in store.all_shops():
        data = store.get(shop)
        payload = data.get("last_run")
        email = data.get("email")
        if not payload or not email:
            skipped += 1
            continue
        try:
            ok = send_email(email, build_digest_subject(payload),
                            build_digest_html(shop, payload))
            sent += 1 if ok else 0
            skipped += 0 if ok else 1
        except Exception:
            skipped += 1
    return {"sent": sent, "skipped": skipped, "shops": len(store.all_shops())}

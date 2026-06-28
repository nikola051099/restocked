from app.forecasting import build_demo_payload
from app.digest import build_digest_html, build_digest_subject, send_email

def test_subject_counts_imminent():
    s = build_digest_subject(build_demo_payload())
    assert "need reordering" in s

def test_html_contains_key_bits():
    h = build_digest_html("demo-store.myshopify.com", build_demo_payload())
    assert "Restocked" in h and "Open full dashboard" in h and "M · Black" in h

def test_send_skips_without_smtp():
    # No SMTP_HOST configured in tests -> returns False (skipped), no crash
    assert send_email("x@example.com", "Hi", "<b>hi</b>") is False

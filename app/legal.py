"""Public legal pages (privacy policy + terms) served by the app, so the
App Store listing has working URLs without extra hosting."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_STYLE = """
<style>
body{font:16px/1.7 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
color:#303030;max-width:760px;margin:0 auto;padding:40px 22px;}
h1{font-size:28px;margin:0 0 4px;} h2{font-size:18px;margin:28px 0 6px;}
.muted{color:#6d7175;font-size:14px;} a{color:#1f6f5c;}
</style>"""


@router.get("/privacy", response_class=HTMLResponse)
async def privacy():
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Restocked — Privacy Policy</title>{_STYLE}</head><body>
<h1>Privacy Policy</h1>
<p class="muted">Last updated: June 28, 2026</p>
<p>Restocked ("the app", "we") provides size-level demand forecasting and reorder
planning for Shopify merchants. This policy explains what data we access, why, and
how we handle it.</p>

<h2>Information we access</h2>
<p>With the store owner's authorization, Restocked reads the following from the
merchant's Shopify store via the Shopify Admin API:</p>
<ul>
<li><b>Order history</b> — order dates and line items (variant and quantity), used to
measure historical demand.</li>
<li><b>Products and variants</b> — product/variant identifiers, size and color options,
and current inventory levels.</li>
<li><b>Store contact email</b> — used solely to send the optional weekly reorder digest.</li>
</ul>
<p>We do <b>not</b> collect customer names, addresses, emails, or payment information.
Demand is stored only in aggregate, per product variant.</p>

<h2>How we use it</h2>
<p>Data is used exclusively to generate inventory forecasts and reorder
recommendations shown to the merchant inside the app, and to send the optional
weekly email digest. We do not sell or share data with third parties, and we do not
use it for advertising.</p>

<h2>Data retention &amp; deletion</h2>
<p>We store the access token and the latest computed recommendations for each store.
When a merchant uninstalls the app, the associated record is deleted automatically.
Merchants may also request deletion at any time by emailing us. We honor Shopify's
mandatory data-erasure (GDPR) webhooks.</p>

<h2>Security</h2>
<p>All requests use authenticated, encrypted (HTTPS) connections. Access tokens are
stored securely and never exposed to third parties.</p>

<h2>Contact</h2>
<p>Questions or deletion requests: <a href="mailto:nikola050304@gmail.com">nikola050304@gmail.com</a></p>
</body></html>"""


@router.get("/terms", response_class=HTMLResponse)
async def terms():
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Restocked — Terms of Service</title>{_STYLE}</head><body>
<h1>Terms of Service</h1>
<p class="muted">Last updated: June 28, 2026</p>
<p>By installing or using Restocked, you agree to these terms.</p>
<h2>Service</h2>
<p>Restocked provides inventory demand forecasts and reorder recommendations. The
recommendations are estimates to assist your purchasing decisions; you are
responsible for your own ordering and inventory choices.</p>
<h2>Subscriptions &amp; billing</h2>
<p>Paid plans are billed monthly through Shopify's billing system. A free trial may
apply. You can cancel at any time by uninstalling the app; charges already incurred
are non-refundable except where required by law.</p>
<h2>Availability</h2>
<p>We aim for high availability but do not guarantee uninterrupted service. The app is
provided "as is" without warranties of any kind.</p>
<h2>Limitation of liability</h2>
<p>To the maximum extent permitted by law, Restocked is not liable for indirect or
consequential losses arising from use of the app, including inventory decisions made
based on its recommendations.</p>
<h2>Contact</h2>
<p><a href="mailto:nikola050304@gmail.com">nikola050304@gmail.com</a></p>
</body></html>"""

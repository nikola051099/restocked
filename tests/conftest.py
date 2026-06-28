import os
# Set env BEFORE app modules import (config reads env at import time).
os.environ.setdefault("SHOPIFY_API_KEY", "test-key")
os.environ.setdefault("SHOPIFY_API_SECRET", "test-secret")
os.environ.setdefault("CRON_SECRET", "test-cron")
os.environ.setdefault("DEMO", "1")

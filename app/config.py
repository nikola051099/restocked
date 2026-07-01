"""Central config loaded from environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    API_KEY: str = os.getenv("SHOPIFY_API_KEY", "")
    API_SECRET: str = os.getenv("SHOPIFY_API_SECRET", "")
    SCOPES: str = os.getenv("SHOPIFY_SCOPES", "read_orders,read_products,read_inventory")
    APP_URL: str = os.getenv("APP_URL", "http://localhost:8000").rstrip("/")
    APP_HANDLE: str = (os.getenv("SHOPIFY_APP_HANDLE") or "restocked-7").strip()
    APP_SECRET: str = os.getenv("APP_SECRET", "dev-insecure-secret")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    DEFAULT_LEAD_TIME_DAYS: int = int(os.getenv("DEFAULT_LEAD_TIME_DAYS", "30"))

    # DEMO=1 runs the app with synthetic data and no Shopify calls/auth,
    # so you can open it locally and click around. NEVER enable in production.
    DEMO: bool = os.getenv("DEMO", "0") == "1"

    API_VERSION: str = os.getenv("SHOPIFY_API_VERSION", "2026-04")

    # Shared secret the scheduler sends (header X-Cron-Secret) to run jobs.
    CRON_SECRET: str = os.getenv("CRON_SECRET", "")

    # Email (weekly digest). If SMTP_HOST is empty, sending is skipped.
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASS: str = os.getenv("SMTP_PASS", "")
    FROM_EMAIL: str = os.getenv("FROM_EMAIL", "Restocked <noreply@restocked.app>")

    @property
    def redirect_uri(self) -> str:
        return f"{self.APP_URL}/auth/callback"


settings = Settings()

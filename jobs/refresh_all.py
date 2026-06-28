"""Nightly job: recompute forecasts for every installed shop.
Run on a schedule (e.g. Render Cron):  python -m jobs.refresh_all"""
import asyncio
from app.store import store
from app.forecasting import compute_recommendations

async def main():
    done = failed = 0
    for shop in store.all_shops():
        d = store.get(shop)
        if not d.get("token"):
            continue
        try:
            r = await compute_recommendations(shop, d["token"], d.get("lead_time_days"))
            d["last_run"] = r
            d["email"] = r.get("shop_email") or d.get("email")
            store.put(shop, d); done += 1
        except Exception as e:
            failed += 1; print(f"[refresh] {shop} failed: {e}")
    print(f"[refresh] done={done} failed={failed}")

if __name__ == "__main__":
    asyncio.run(main())

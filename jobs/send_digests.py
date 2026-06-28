"""Weekly job: email each merchant their reorder digest.
Run on a schedule (e.g. Render Cron):  python -m jobs.send_digests"""
from app.digest import run_digests

if __name__ == "__main__":
    print("[digest]", run_digests())

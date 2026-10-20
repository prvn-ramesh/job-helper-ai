#!/usr/bin/env python3
"""AutoJob AI — Interactive Dashboard & Live Job Hunting Launcher.

Initializes the environment, launches the FastAPI Control Plane, and
automatically opens the interactive web dashboard in your browser.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

HOST = "127.0.0.1"
PORT = 8000
DASHBOARD_URL = f"http://{HOST}:{PORT}"
HEALTH_URL = f"{DASHBOARD_URL}/health"


def free_port(port: int) -> None:
    """Kill any existing process listening on the target port to ensure clean start."""
    with contextlib.suppress(Exception):
        out = subprocess.check_output(["lsof", "-ti", f":{port}"], text=True).strip()
        if out:
            pids = [int(p) for p in out.splitlines() if p.strip()]
            for pid in pids:
                if pid != os.getpid():
                    os.kill(pid, signal.SIGTERM)
            time.sleep(0.5)


def wait_for_server(url: str, timeout: float = 12.0) -> bool:
    """Poll the server until /health responds 200 OK."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.25)
    return False


def main() -> None:
    print("\n" + "=" * 74)
    print("⚡ AUTOJOB AI — MISSION CONTROL INITIALIZING")
    print("=" * 74)

    # 1. Initialize DB if needed
    try:
        from infrastructure.database.sqlite import init_db
        init_db()
        print("✓ SQLite database verified (WAL mode)")
    except Exception as e:
        print(f"⚠ Database check warning: {e}")

    # 2. Free port 8000 if occupied
    free_port(PORT)

    # 3. Start Uvicorn process
    print(f"✓ Starting FastAPI Control Plane server on {DASHBOARD_URL} ...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "presentation.api.main:app",
        "--host",
        HOST,
        "--port",
        str(PORT),
        "--log-level",
        "info",
    ]

    proc = subprocess.Popen(cmd, cwd=str(PROJECT_ROOT), env=env)

    try:
        # 4. Wait for server readiness
        if wait_for_server(HEALTH_URL):
            print("✓ Server is healthy and listening!")
            print(f"✓ Automatically opening browser to {DASHBOARD_URL} ...")
            webbrowser.open(DASHBOARD_URL)
        else:
            print("⚠ Server started but health check timed out. You can open manually:")
            print(f"   {DASHBOARD_URL}")

        print("\n" + "=" * 74)
        print("🚀 MISSION CONTROL IS LIVE!")
        print("=" * 74)
        print(f"  • Dashboard URL:   {DASHBOARD_URL}")
        print("  • Google Sheet:    https://docs.google.com/spreadsheets/d/16N4kXGHWP9KhyKyRoqvjNJTMX20W5LaM5gfs3AiQOzg")
        print("  • Candidate:       Praveen Ramesh | 2 yrs exp | Notice: 60 days")
        print("  • Compensation:    Current: ₹4 LPA | Target: ₹8 LPA")
        print("  • Mode:            Semi-Auto (Review Gate Active)")
        print("=" * 74)
        print("💡 Click 'Run Discovery', 'Run Triage', or 'Run Batch Apply' in the UI.")
        print("   Press [Ctrl + C] in this terminal at any time to stop the server.\n")

        # Stream server logs until user interrupts
        proc.wait()

    except KeyboardInterrupt:
        print("\nStopping AutoJob AI server...")
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=3)
        print("✓ Server stopped cleanly. Good luck with your job hunt!")


if __name__ == "__main__":
    main()

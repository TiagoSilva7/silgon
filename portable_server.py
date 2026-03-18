import argparse
import os
import socket
import time
import webbrowser

from app import app, ensure_initialized, BASE_DIR, DB_PATH


def wait_for_port(host: str, port: int, timeout_s: float = 10.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="SILGON Portable Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--no-open", action="store_true", help="Do not open browser")
    parser.add_argument("--reset-db", action="store_true", help="Delete DB file before starting")
    args = parser.parse_args()

    os.chdir(BASE_DIR)

    if args.reset_db and os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except OSError:
            pass

    ensure_initialized()

    url = f"http://{args.host}:{args.port}/"
    if not args.no_open:
        # Open browser shortly after the server starts listening.
        def _open_when_ready():
            if wait_for_port(args.host, args.port, timeout_s=8.0):
                try:
                    webbrowser.open(url)
                except Exception:
                    pass

        # Fire-and-forget in a simple way: start a thread.
        import threading

        t = threading.Thread(target=_open_when_ready, daemon=True)
        t.start()

    # Important: debug must be False in portable
    app.run(host=args.host, port=args.port, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

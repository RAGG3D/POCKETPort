import argparse
import os
import signal
import sys
import threading

from pocketport.controller import Controller
from pocketport.web import Dashboard


def main():
    parser = argparse.ArgumentParser(prog="pocketport", description="POCKETPort · 口袋港")
    parser.add_argument("command", choices=["desktop", "mcp"], nargs="?", default="desktop")
    args = parser.parse_args()
    if os.name != "nt":
        os.umask(0o077)
    controller = Controller()
    try:
        dashboard = Dashboard(controller)
    except OSError as exc:
        print(f"POCKETPort could not open local port 8766: {exc}. Close the other POCKETPort window/agent process and retry.", file=sys.stderr)
        return 1

    def interrupted(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupted)
    try:
        if args.command == "mcp":
            from pocketport.mcp_server import run
            run(controller, dashboard)
        else:
            result = dashboard.open()
            if not result["opened"]:
                print("Open this private local link in your browser (do not share it):", file=sys.stderr)
                print(f"http://127.0.0.1:8766/#{dashboard.token}", file=sys.stderr)
            print("POCKETPort is running. Leave this window open; Ctrl+C to quit.", file=sys.stderr)
            threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        dashboard.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

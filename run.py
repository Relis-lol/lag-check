"""GUI entry point and private worker entry point (also used by the EXE)."""

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Lag Check — passive Windows diagnostics"
    )
    parser.add_argument("--monitor", action="store_true")
    parser.add_argument("--seconds", type=int, default=0)
    parser.add_argument("--no-network", action="store_true")
    parser.add_argument("--no-events", action="store_true")
    parser.add_argument("--no-alt-tab", action="store_true")
    parser.add_argument(
        "--data-dir", help="Custom local storage directory, e.g. for isolated tests"
    )
    args = parser.parse_args()
    if args.data_dir:
        os.environ["LAGCHECK_DATA_DIR"] = os.path.abspath(args.data_dir)
    if sys.platform != "win32":
        raise SystemExit("Lag Check benötigt Windows 10/11 (64 Bit).")
    if args.monitor:
        from lagcheck.engine import run

        run(
            args.seconds,
            {
                "network": not args.no_network,
                "events": not args.no_events,
                "alt_tab": not args.no_alt_tab,
            },
        )
    else:
        from lagcheck.gui import main as gui_main

        gui_main()


if __name__ == "__main__":
    main()

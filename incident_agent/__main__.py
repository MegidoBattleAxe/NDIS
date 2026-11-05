import argparse
import sys
import time
from pathlib import Path

from .agent import build_agent
from .config import Config


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="incident_agent",
        description="Scan Outlook for incident forms from a sender, download them to one folder, "
                    "and maintain a severity-sorted incident register with NDIS-reportable rows in red.",
    )
    parser.add_argument("--env", help="path to env file (see config.example.env)")
    parser.add_argument("--demo", action="store_true", help="run offline against ./samples instead of Outlook")
    parser.add_argument("--samples", default="samples", help="directory of sample form files for --demo")
    parser.add_argument("--interval", type=int, default=None, help="poll every N seconds instead of running once")
    args = parser.parse_args(argv)

    cfg = Config.from_env(args.env, require_live=not args.demo)
    if args.demo:
        sample_dir = Path(args.samples)
        if not sample_dir.is_dir():
            print(f"samples directory not found: {sample_dir}", file=sys.stderr)
            return 2
        demo_files = sorted(p for p in sample_dir.iterdir() if p.is_file())
    else:
        demo_files = None

    agent = build_agent(cfg, demo=args.demo)

    def run():
        stats = agent.run_once(demo_files=demo_files)
        print(
            f"run complete: {stats['messages_new']}/{stats['messages_seen']} new messages, "
            f"{stats['rows']} new rows, register now holds {stats['total_in_register']} incidents "
            f"-> {stats['register']}"
        )
        for a in stats["attachments"]:
            if a["status"] != "processed":
                print(f"  {a['status']}: {a['file']} ({a.get('reason', '')})")
        return stats

    run()
    if args.interval:
        while True:
            time.sleep(args.interval)
            run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

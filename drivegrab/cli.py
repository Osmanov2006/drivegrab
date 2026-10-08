"""Command line interface."""

import argparse
from pathlib import Path

from drivegrab import __version__
from drivegrab.grabber import Grabber


def build_parser():
    p = argparse.ArgumentParser(
        prog="drivegrab",
        description="Download view-only PDFs and whole folders from Google Drive.",
    )
    p.add_argument("urls", nargs="*",
                   help="Drive file or folder links. Leave empty for interactive mode.")
    p.add_argument("-o", "--out", default="downloads",
                   help="output directory (default: ./downloads)")
    p.add_argument("--no-zip", action="store_true",
                   help="don't pack folders into a .zip")
    p.add_argument("-q", "--quality", type=float, default=0.92,
                   help="JPEG quality for captured pages, 0.1-1.0 (default: 0.92)")
    p.add_argument("--size", type=parse_size, default="1920x1080",
                   help="browser window size, bigger = sharper pages (default: 1920x1080)")
    p.add_argument("--profile", default=str(Path.home() / ".drivegrab" / "profile"),
                   help="browser profile dir, keeps your Google login between runs")
    p.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    return p


def parse_size(s):
    try:
        w, h = s.lower().split("x")
        return int(w), int(h)
    except ValueError:
        raise argparse.ArgumentTypeError(f"bad size '{s}', expected something like 1920x1080") from None


def print_report(report):
    print()
    if report.archive:
        print(f"zip: {report.archive}")
    print(f"saved: {len(report.saved)}  failed: {len(report.failed)}")
    for f in report.failed:
        print(f"   x {Path(f).as_posix()}")


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not 0.1 <= args.quality <= 1.0:
        raise SystemExit("--quality must be between 0.1 and 1.0")
    width, height = args.size

    # imported here so `drivegrab --help` works even before `playwright install`
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            args.profile,
            headless=False,          # visible on purpose: you may need to sign in
            accept_downloads=True,
            viewport={"width": width, "height": height},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        grabber = Grabber(page, args.out, quality=args.quality, viewport=(width, height))

        def run(url):
            try:
                print_report(grabber.grab(url, make_zip=not args.no_zip))
            except ValueError as e:
                print(f"error: {e}")
            except Exception as e:
                print(f"something went wrong: {e}")

        try:
            if args.urls:
                for url in args.urls:
                    run(url)
            else:
                while True:
                    url = input("\nDrive link (empty to quit): ").strip()
                    if not url:
                        break
                    run(url)
        except (KeyboardInterrupt, EOFError):
            print("\nbye")
        finally:
            ctx.close()


if __name__ == "__main__":
    main()

"""
drivegrab - download view-only files and whole folders from Google Drive.

    python drivegrab.py                  # then paste a link
    python drivegrab.py <link> <link>    # or pass links directly

https://github.com/Osmanov2006/drivegrab
"""

import argparse
import base64
import re
import shutil
from pathlib import Path

import img2pdf
from playwright.sync_api import sync_playwright

__version__ = "1.1.0"

DRIVE = "https://drive.google.com"


# ---------------------------------------------------------------- JS in page

# Every loaded page of the Drive viewer is an <img> with a blob: src.
# We return its index and y position inside the scroll container - Drive
# unloads pages far off screen, so the position is how we keep the order.
SCAN_PAGES = """() => {
    const res = [];
    let atBottom = false;
    const imgs = [...document.images];
    for (let i = 0; i < imgs.length; i++) {
        const img = imgs[i];
        if (!img.src.startsWith('blob:https://drive.google.com/')) continue;
        if (!img.complete || !img.naturalWidth) continue;

        let box = img.parentElement;
        while (box && box.scrollHeight <= box.clientHeight + 5) box = box.parentElement;
        const boxTop = box ? box.getBoundingClientRect().top : 0;
        const st = box ? box.scrollTop : window.scrollY;
        if (box) atBottom = box.scrollTop + box.clientHeight >= box.scrollHeight - 5;

        res.push({ i: i, y: Math.round(img.getBoundingClientRect().top - boxTop + st), w: img.naturalWidth });
    }
    return { pages: res, atBottom: atBottom };
}"""

# draw one page on a canvas and export as jpeg (white fill so nothing turns black)
GRAB_PAGE = """([i, quality]) => {
    const img = document.images[i];
    const c = document.createElement('canvas');
    c.width = img.naturalWidth;
    c.height = img.naturalHeight;
    const ctx = c.getContext('2d');
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, c.width, c.height);
    ctx.drawImage(img, 0, 0);
    return c.toDataURL('image/jpeg', quality);
}"""

# embeddedfolderview is a plain html folder listing - way easier to parse than the drive UI
LIST_FOLDER = """() => [...document.querySelectorAll('.flip-entry')].map(e => {
    const a = e.querySelector('a');
    const t = e.querySelector('.flip-entry-title');
    return {
        href: a ? a.href : '',
        id: (e.id || '').replace('entry-', ''),
        name: t ? t.textContent.trim() : ''
    };
})"""

FILE_TITLE = """() => document.querySelector('meta[itemprop="name"]')?.content || document.title"""


# ---------------------------------------------------------------- helpers

def folder_id(url):
    m = re.search(r"/folders/([\w-]{20,})", url or "")
    return m.group(1) if m else None


def file_id(url):
    if not url or folder_id(url):
        return None
    m = re.search(r"/d/([\w-]{20,})", url) or re.search(r"[?&]id=([\w-]{20,})", url)
    return m.group(1) if m else None


def safe_name(name, fallback="untitled"):
    name = re.sub(r"\s*-\s*Google\s*(Drive|Диск|Drive'ı)?\s*$", "", name or "", flags=re.I).strip()
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name).rstrip(" .")
    return name or fallback


def unique_path(folder, name):
    p = Path(folder) / name
    stem, suffix = Path(name).stem, Path(name).suffix
    n = 1
    while p.exists():
        p = Path(folder) / f"{stem} ({n}){suffix}"
        n += 1
    return p


# ---------------------------------------------------------------- the browser part

class Grabber:
    def __init__(self, page, out_dir, quality=0.92, viewport=(1920, 1080)):
        self.page = page
        self.out_dir = Path(out_dir)
        self.quality = quality
        self.viewport = viewport

    def grab(self, url, make_zip=True):
        fold = folder_id(url)
        if fold:
            return self.grab_folder(fold, make_zip)

        fid = file_id(url)
        if not fid:
            print("that's not a Google Drive file or folder link")
            return
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.download(fid, self.out_dir, "")

    def grab_folder(self, fold_id, make_zip):
        root_name, _ = self.list_folder(fold_id)
        print(f"folder: {root_name}\ncollecting file list...")
        files = self.walk(fold_id)
        print(f"files found: {len(files)}\n")

        root = self.out_dir / root_name
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)

        failed = []
        for n, (rel, fid, name) in enumerate(files, 1):
            print(f"[{n}/{len(files)}] {(rel / name).as_posix()}")
            try:
                ok = self.download(fid, root / rel, name)
            except Exception as e:  # one broken file shouldn't stop the rest
                print(f"    error: {e}")
                ok = None
            if not ok:
                failed.append(rel / name)

        print()
        if make_zip:
            zip_path = shutil.make_archive(str(self.out_dir / root_name), "zip", self.out_dir, root_name)
            print(f"zip: {zip_path}")
        print(f"saved: {len(files) - len(failed)}  failed: {len(failed)}")
        for f in failed:
            print(f"   x {f.as_posix()}")

    # ---- folders

    def wait_login(self):
        if "accounts.google.com" in self.page.url or "ServiceLogin" in self.page.url:
            input(">> sign in to Google in the browser window, then press Enter here...")
            self.page.wait_for_load_state("networkidle")
            return True
        return False

    def list_folder(self, fold_id):
        url = f"{DRIVE}/embeddedfolderview?id={fold_id}#list"
        self.page.goto(url, wait_until="domcontentloaded")
        if self.wait_login():
            self.page.goto(url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(1500)
        return safe_name(self.page.title(), fold_id), self.page.evaluate(LIST_FOLDER)

    def walk(self, fold_id, rel=Path("."), out=None):
        # returns [(relative folder, file id, name), ...] for every file inside
        out = [] if out is None else out
        _, items = self.list_folder(fold_id)
        print(f"  {rel.as_posix()}: {len(items)} items")
        for it in items:
            name = safe_name(it["name"])
            sub = folder_id(it["href"])
            if sub:
                self.walk(sub, rel / name, out)
            else:
                fid = file_id(it["href"]) or it["id"]
                if fid:
                    out.append((rel, fid, name))
        return out

    # ---- one file

    def download(self, fid, dest, name):
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)

        path = self.direct_download(fid, dest)
        if path:
            print(f"    original file saved: {path.name}")
            return path

        print("    download is disabled, capturing the preview...")
        path = self.capture_preview(fid, dest, name)
        print(f"    done: {path.name}" if path else "    failed: no preview or no access")
        return path

    def direct_download(self, fid, dest):
        # works when the owner allows downloading
        try:
            with self.page.expect_download(timeout=4000) as info:
                try:
                    self.page.goto(f"{DRIVE}/uc?export=download&id={fid}")
                except Exception:
                    pass  # goto throws when it turns into a download, that's fine
                # big files get a "can't scan for viruses" page first
                btn = self.page.locator("#uc-download-link, form#download-form [type=submit]")
                if btn.count():
                    btn.first.click()
            dl = info.value
        except Exception:
            return None
        path = unique_path(dest, safe_name(dl.suggested_filename))
        dl.save_as(path)
        return path

    def capture_preview(self, fid, dest, name):
        # view-only: scroll the viewer, save every page image, glue them into a pdf
        self.page.goto(f"{DRIVE}/file/d/{fid}/view", wait_until="domcontentloaded")
        self.wait_login()
        self.page.wait_for_timeout(4000)

        name = name or safe_name(self.page.evaluate(FILE_TITLE), fid)
        if not name.lower().endswith(".pdf"):
            name += ".pdf"

        pages = []   # [y, width, jpeg bytes]
        w, h = self.viewport
        self.page.mouse.move(w // 2, h // 2)
        idle = 0

        for _ in range(3000):
            scan = self.page.evaluate(SCAN_PAGES)
            new = 0
            for p in scan["pages"]:
                old = next((x for x in pages if abs(x[0] - p["y"]) < 30), None)
                if old and old[1] >= p["w"]:
                    continue
                data = self.page.evaluate(GRAB_PAGE, [p["i"], self.quality])
                jpg = base64.b64decode(data.split(",", 1)[1])
                if old:
                    old[1], old[2] = p["w"], jpg   # sharper version of a page we have
                else:
                    pages.append([p["y"], p["w"], jpg])
                    new += 1

            if new:
                print(f"\r    pages: {len(pages)}", end="", flush=True)

            # at the bottom and nothing new for a while -> done
            if new == 0 and scan["atBottom"]:
                idle += 1
                if idle >= 6:
                    break
            else:
                idle = 0

            self.page.mouse.wheel(0, 700)
            self.page.wait_for_timeout(300)

        if not pages:
            return None
        print()
        pages.sort(key=lambda x: x[0])
        path = unique_path(dest, name)
        path.write_bytes(img2pdf.convert([p[2] for p in pages]))
        return path


# ---------------------------------------------------------------- cli

def parse_size(s):
    try:
        w, h = s.lower().split("x")
        return int(w), int(h)
    except ValueError:
        raise argparse.ArgumentTypeError(f"bad size '{s}', use something like 1920x1080") from None


def main():
    ap = argparse.ArgumentParser(description="Download view-only PDFs and whole folders from Google Drive.")
    ap.add_argument("urls", nargs="*", help="Drive file or folder links (empty = paste them one by one)")
    ap.add_argument("-o", "--out", default="downloads", help="output folder (default: downloads)")
    ap.add_argument("--no-zip", action="store_true", help="don't zip folders")
    ap.add_argument("-q", "--quality", type=float, default=0.92, help="jpeg quality 0.1-1.0 (default: 0.92)")
    ap.add_argument("--size", type=parse_size, default="1920x1080", help="window size, bigger = sharper")
    ap.add_argument("--profile", default=str(Path.home() / ".drivegrab"), help="where the google login is kept")
    ap.add_argument("-V", "--version", action="version", version=f"drivegrab {__version__}")
    args = ap.parse_args()

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            args.profile,
            headless=False,          # visible on purpose, you might need to sign in
            accept_downloads=True,
            viewport={"width": args.size[0], "height": args.size[1]},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        grabber = Grabber(page, args.out, args.quality, args.size)

        def run(url):
            try:
                grabber.grab(url, make_zip=not args.no_zip)
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

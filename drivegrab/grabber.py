"""The part that actually drives the browser."""

import base64
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import img2pdf

from drivegrab import scripts
from drivegrab.links import file_id, folder_id
from drivegrab.paths import as_pdf, safe_name, unique_path

DRIVE = "https://drive.google.com"


@dataclass
class Entry:
    rel: Path      # folder path relative to the root folder
    id: str
    name: str


@dataclass
class Report:
    saved: list = field(default_factory=list)
    failed: list = field(default_factory=list)
    archive: Path = None


class Grabber:
    def __init__(self, page, out_dir, quality=0.92, direct_timeout=4000,
                 viewport=(1920, 1080), log=print):
        self.page = page
        self.out_dir = Path(out_dir)
        self.quality = quality
        self.direct_timeout = direct_timeout
        self.viewport = viewport
        self.log = log

    # ---------- entry point ----------

    def grab(self, url, make_zip=True):
        fold = folder_id(url)
        if fold:
            return self.grab_folder(fold, make_zip)

        fid = file_id(url)
        if not fid:
            raise ValueError("not a Google Drive file or folder link")

        report = Report()
        self.out_dir.mkdir(parents=True, exist_ok=True)
        path = self.download(fid, self.out_dir, "")
        (report.saved if path else report.failed).append(path or fid)
        return report

    def grab_folder(self, fold_id, make_zip=True):
        root_name, _ = self.list_folder(fold_id)
        self.log(f"folder: {root_name}")
        self.log("collecting file list...")
        entries = self.walk(fold_id)
        self.log(f"files found: {len(entries)}\n")

        root = self.out_dir / root_name
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)

        report = Report()
        total = len(entries)
        for n, e in enumerate(entries, 1):
            where = e.rel.as_posix()
            self.log(f"[{n}/{total}] {'' if where == '.' else where + '/'}{e.name}")
            try:
                path = self.download(e.id, root / e.rel, e.name)
            except Exception as err:  # one broken file shouldn't kill the whole run
                self.log(f"    error: {err}")
                path = None
            if path:
                report.saved.append(path)
            else:
                report.failed.append(e.rel / e.name)

        if make_zip:
            report.archive = Path(shutil.make_archive(
                str(self.out_dir / root_name), "zip", self.out_dir, root_name))
        return report

    # ---------- folders ----------

    def _wait_login(self):
        url = self.page.url
        if "accounts.google.com" in url or "ServiceLogin" in url:
            input(">> Google wants you to sign in. Do it in the browser window, then press Enter here...")
            self.page.wait_for_load_state("networkidle")
            return True
        return False

    def list_folder(self, fold_id):
        url = f"{DRIVE}/embeddedfolderview?id={fold_id}#list"
        self.page.goto(url, wait_until="domcontentloaded")
        if self._wait_login():
            self.page.goto(url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(1500)
        return safe_name(self.page.title(), fold_id), self.page.evaluate(scripts.LIST_FOLDER)

    def walk(self, fold_id, rel=Path("."), out=None):
        """Recursively collect every file under a folder."""
        out = [] if out is None else out
        _, items = self.list_folder(fold_id)
        self.log(f"  {rel.as_posix()}: {len(items)} items")

        for it in items:
            name = safe_name(it["name"])
            sub = folder_id(it["href"])
            if sub:
                self.walk(sub, rel / name, out)
                continue
            fid = file_id(it["href"]) or it["id"]
            if fid:
                out.append(Entry(rel, fid, name))
        return out

    # ---------- single file ----------

    def download(self, fid, dest, name):
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)

        path = self.direct_download(fid, dest)
        if path:
            self.log(f"    original file saved: {path.name}")
            return path

        self.log("    download is disabled, capturing the preview...")
        path = self.capture_preview(fid, dest, name)
        if path:
            self.log(f"    done: {path.name}")
        else:
            self.log("    failed: no preview or no access")
        return path

    def direct_download(self, fid, dest):
        """Works for files where the owner allows downloading."""
        url = f"{DRIVE}/uc?export=download&id={fid}"
        try:
            with self.page.expect_download(timeout=self.direct_timeout) as info:
                try:
                    self.page.goto(url)
                except Exception:
                    pass  # goto throws when the navigation turns into a download - expected
                # big files land on a "can't scan for viruses" page first
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
        """For view-only files: scroll the viewer and save every rendered page."""
        self.page.goto(f"{DRIVE}/file/d/{fid}/view", wait_until="domcontentloaded")
        self._wait_login()
        self.page.wait_for_timeout(4000)

        if not name:
            name = safe_name(self.page.evaluate(scripts.FILE_TITLE), fid)

        pages = self._collect_pages()
        if not pages:
            return None

        path = unique_path(dest, as_pdf(name))
        path.write_bytes(img2pdf.convert(pages))
        return path

    def _collect_pages(self, max_steps=3000):
        pages = []   # [y, width, jpeg bytes]
        w, h = self.viewport
        self.page.mouse.move(w // 2, h // 2)
        idle = 0

        for _ in range(max_steps):
            scan = self.page.evaluate(scripts.SCAN_PAGES)
            new = 0

            for p in scan["pages"]:
                old = next((x for x in pages if abs(x[0] - p["y"]) < 30), None)
                if old and old[1] >= p["w"]:
                    continue
                data = self.page.evaluate(scripts.GRAB_PAGE, [p["i"], self.quality])
                jpg = base64.b64decode(data.split(",", 1)[1])
                if old:
                    old[1], old[2] = p["w"], jpg   # sharper version of a page we already have
                else:
                    pages.append([p["y"], p["w"], jpg])
                    new += 1

            if new:
                print(f"\r    pages: {len(pages)}", end="", flush=True)

            # stop once we're at the bottom and nothing new shows up for a while
            if new == 0 and scan["atBottom"]:
                idle += 1
                if idle >= 6:
                    break
            else:
                idle = 0

            self.page.mouse.wheel(0, 700)
            self.page.wait_for_timeout(300)

        if pages:
            print()
        pages.sort(key=lambda x: x[0])
        return [p[2] for p in pages]

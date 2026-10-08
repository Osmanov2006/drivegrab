<p align="center">
  <img src="assets/banner.svg" alt="drivegrab" width="100%">
</p>

<p align="center">
  <a href="https://github.com/Osmanov2006/drivegrab/actions/workflows/ci.yml"><img src="https://github.com/Osmanov2006/drivegrab/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT">
</p>

<p align="center"><b>English</b> · <a href="README.ru.md">Русский</a></p>

---

## What is this?

Some Google Drive files can only be **viewed**, not downloaded. There's no download button, and printing is blocked too.

**drivegrab** saves them anyway. You paste a link, and it gives you the files.

- Works with a **single file** or a **whole folder**, including all subfolders.
- Keeps the **same folder structure** and packs everything into a **.zip**.
- If a file *can* be downloaded normally, you get the original file.

## Quick start

**1. Install** (one time). You need [Python 3.9+](https://www.python.org/downloads/).

```bash
git clone https://github.com/Osmanov2006/drivegrab.git
cd drivegrab
pip install -r requirements.txt
playwright install chromium
```

**2. Run**

```bash
python -m drivegrab
```

**3. Paste a link and press Enter**

```text
Drive link (empty to quit): https://drive.google.com/drive/folders/1n64NVPN...
```

A browser window opens and starts working by itself. **Don't close it.** When it's done:

```text
zip: downloads/Probability and Random Variables.zip
saved: 69  failed: 0
```

Your files are in the **`downloads`** folder next to the project.

## What does it look like while running?

```text
folder: Probability and Random Variables
collecting file list...
  Exercises: 3 items
  Lecture Notes: 4 items
  Slides: 4 items
files found: 69

[1/69] Exercises/Chapter_1_Exercises_EN.pdf
    download is disabled, capturing the preview...
    pages: 12
    done: Chapter_1_Exercises_EN.pdf
```

- **"download is disabled"** means the file is view-only, so drivegrab rebuilds it page by page from the preview. That's normal.
- **"original file saved"** means the file was downloadable, so you got the real file.

## Common questions

**It asks me to sign in.**
The file isn't public. Sign in to Google in the browser window that opened, then press Enter in the terminal. You only do this once, because the login is remembered.

**Pages look blurry.**
Run it with a bigger window: `python -m drivegrab --size 2560x1440`

**I can't select text in the PDF.**
View-only files are rebuilt from page images, so the text isn't selectable. Run them through [OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) if you need searchable text.

**Some files failed.**
They're listed at the end. Usually that's a video or a file with no preview.

**Can I give links without the prompt?**
Yes: `python -m drivegrab <link1> <link2>`

## All options

| Option | What it does |
|---|---|
| `-o folder` | Save somewhere other than `downloads` |
| `--no-zip` | Don't create a zip, just the folder |
| `--size 2560x1440` | Bigger window, sharper pages |
| `-q 0.8` | JPEG quality (lower means smaller files) |

## What's in this repo

The actual program is the `drivegrab/` folder. Everything else is the standard setup that makes a Python project installable and tested.

| File | Why it's there |
|---|---|
| `drivegrab/grabber.py` | **The main logic**: opens Drive, walks folders, downloads files, captures pages |
| `drivegrab/scripts.py` | Small JavaScript pieces that run inside the Drive page and read the page images |
| `drivegrab/cli.py` | What you see in the terminal: the link prompt and the options |
| `drivegrab/links.py` | Pulls the file or folder ID out of a Drive link |
| `drivegrab/paths.py` | Makes file names safe for Windows and avoids overwriting files |
| `tests/` | Automatic checks that the link and file-name logic works |
| `.github/workflows/ci.yml` | Runs those checks on GitHub after every change (the green **CI** badge) |
| `pyproject.toml`, `requirements.txt` | Lists the dependencies so `pip install` works |

## How it works (short version)

1. For a folder, it opens Google's simple folder listing page and goes through every subfolder.
2. For each file, it first tries a normal download.
3. If downloading is blocked, it opens the file viewer and scrolls through it. Drive shows each page as an image, so drivegrab saves every page image as it appears and puts them together into a PDF.

## Please use it responsibly

drivegrab only works on files you can already open in your browser. It doesn't break any access rights. Use it for material you're allowed to keep, like your own course files.

## Credits

Based on the browser-console trick from
[zeltox/Google-Drive-PDF-Downloader](https://github.com/zeltox/Google-Drive-PDF-Downloader).
drivegrab turns it into a full tool with folder support.

License: [MIT](LICENSE) © Magamedkhan Osmanov

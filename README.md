# ZS (Zoeller System) — offline Windows utility

- Offline-first: runs on a clean Windows machine without Internet.
- Distribution: copy a single `ZS.exe` (built on the dev machine) via USB/disk.
- Versioning: tags like `v0.1.0` are for my review only (manual stable snapshots). No auto-updates.
- Code rules: English comments in code; small, useful commits; **one function = one commit**.

## How to read this repo
- 📄 **File** blocks = paste this into a file.
- 💻 **Commands** blocks = run these in Git Bash.

## Local build (dev machine)
1) `python -m venv .venv && . .venv/Scripts/activate`
2) `pip install --upgrade pip`
3) `pip install -r requirements.txt`
4) `pip install pyinstaller`
5) `pyinstaller --onefile --name ZS main.py` → `dist/ZS.exe`

## Run on target (offline) machine
- Copy `ZS.exe` (and optionally `ZS.ods`) to any user folder and double-click.
- No Internet required.
# Build & Distribute Offline

- Build on the dev machine (with Internet to fetch deps once).
- Deliver `dist/ZS.exe` via USB/disk to the target machine (no Python, no Internet).

Steps:
1) `python -m venv .venv && . .venv/Scripts/activate`
2) `pip install -r requirements.txt && pip install pyinstaller`
3) `pyinstaller --onefile --name ZS main.py`
4) Copy `dist/ZS.exe` (and optionally `ZS.ods`) to the target machine.
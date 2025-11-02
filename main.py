"""ZS (Zoeller System) CLI.
Offline-first single-file utility for ODS (LibreOffice/OpenOffice) spreadsheets.
Project rules: English comments; small useful commits; one function = one commit.
"""

import os
import sys
from pathlib import Path

def appdata_dir() -> Path:
    """Return %APPDATA%/ZS (create if missing)."""
    base = os.getenv("APPDATA") or str(Path.home())
    p = Path(base) / "ZS"
    p.mkdir(parents=True, exist_ok=True)
    return p

def main():
    """Bootstrap entry-point. No features yet — functions will be added incrementally."""
    print("ZS CLI bootstrap — no features yet. Next commits will add functions one by one.")
    return 0

if __name__ == "__main__":
    sys.exit(main())

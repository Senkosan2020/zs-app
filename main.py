"""ZS (Zoeller System) CLI.
Offline-first single-file utility for ODS (LibreOffice/OpenOffice) spreadsheets.
Project rules: English comments; small useful commits; one function = one commit.
"""

import os
import sys
import json
from pathlib import Path

DEFAULT_DB_NAME = "ZS.ods"
DEFAULT_RETENTION = 24
DEFAULT_BACKUP_FREQ_MIN = 60


def appdata_dir() -> Path:
    """Return %APPDATA%/ZS (create if missing)."""
    base = os.getenv("APPDATA") or str(Path.home())
    p = Path(base) / "ZS"
    p.mkdir(parents=True, exist_ok=True)
    return p


def localappdata_backups_dir() -> Path:
    """Return %LOCALAPPDATA%/ZS/Backups and create it if missing.
    This is the default location for automatic backups on Windows.
    """
    base = os.getenv("LOCALAPPDATA") or str(Path.home())
    p = Path(base) / "ZS" / "Backups"
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_path() -> Path:
    """Return the full path to the app config file under APPDATA."""
    return appdata_dir() / "config.json"


def load_config() -> dict:
    """Load config JSON from %APPDATA%/ZS/config.json or return sensible defaults."""
    cp = config_path()
    if cp.exists():
        try:
            return json.loads(cp.read_text(encoding="utf-8"))
        except Exception:
            # Fall through to defaults if the file is malformed
            pass
    return {
        "db_path": DEFAULT_DB_NAME,
        "lang": "en",
        "backup_dir": str(localappdata_backups_dir()),
        "backup_retention": DEFAULT_RETENTION,
        "backup_frequency_minutes": DEFAULT_BACKUP_FREQ_MIN,
        "last_backup_time": None
    }


def main():
    """Bootstrap entry-point. No features yet — functions will be added incrementally."""
    print("ZS CLI bootstrap — no features yet. Next commits will add functions one by one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

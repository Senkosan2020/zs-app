"""ZS (Zoeller System) CLI.
Offline-first single-file utility for ODS (LibreOffice/OpenOffice) spreadsheets.
Project rules: English comments; small useful commits; one function = one commit.
"""

import os
import sys
import json
from pathlib import Path
from odf.opendocument import OpenDocumentSpreadsheet, load
from odf.table import Table, TableRow, TableCell
from odf.text import P
from typing import Any


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


def save_config(cfg: dict) -> None:
    """Persist config to %APPDATA%/ZS/config.json (simple atomic-like write)."""
    cp = config_path()
    tmp = cp.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(cp)


def ensure_ods(path: Path) -> None:
    """Ensure an ODS file exists at 'path' with the expected header row.
    If present but malformed (no sheet or wrong header), rewrite headers.
    """
    headers = ["ROK", "DATUM ZAPŮJČENÍ", "ČÍSLO", "REGÁL", "VRÁCENO:", "KDE BYLO:"]

    def append_header_row(tbl: Table) -> None:
        """Append the exact header row to the given table."""
        row = TableRow()
        for h in headers:
            cell = TableCell()
            cell.addElement(P(text=h))
            row.addElement(cell)
        tbl.addElement(row)

    # If file exists, try to validate and repair it
    if path.exists():
        try:
            doc = load(str(path))
            tables = [e for e in doc.spreadsheet.childNodes if isinstance(e, Table)]
            if not tables:
                tbl = Table(name="List1")
                doc.spreadsheet.addElement(tbl)
                append_header_row(tbl)
                doc.save(str(path))
                return

            tbl = tables[0]
            rows = [e for e in tbl.childNodes if isinstance(e, TableRow)]
            if not rows:
                append_header_row(tbl)
                doc.save(str(path))
                return

            # Read first row texts to compare with expected headers
            first = rows[0]
            cells = [e for e in first.childNodes if isinstance(e, TableCell)]
            texts = []
            for c in cells:
                txt = ""
                for ch in c.childNodes:
                    if getattr(ch, "tagName", None) == "text:p":
                        txt += (getattr(ch, "firstChild", None).data
                                if getattr(ch, "firstChild", None) else "")
                texts.append(txt)

            if texts[:len(headers)] != headers:
                # Wipe table content and write only the header row
                for ch in list(tbl.childNodes):
                    tbl.removeChild(ch)
                append_header_row(tbl)

            doc.save(str(path))
            return
        except Exception:
            # Fall through to create a fresh ODS if load/repair failed
            pass

    # Create a brand new ODS with a single sheet and header row
    doc = OpenDocumentSpreadsheet()
    tbl = Table(name="List1")
    doc.spreadsheet.addElement(tbl)
    append_header_row(tbl)
    doc.save(str(path))


def ensure_meta_sheet(doc):
    """Ensure hidden-like _ZS_META sheet with MONTH_COLORS (month|color_hex) exists.
    The sheet is internal and may be skipped by exports. Returns the meta table element.
    """
    from odf.table import Table, TableRow, TableCell
    from odf.text import P

    def _is_table(el: Any) -> bool:
        return getattr(el, "tagName", None) == "table:table"

    def _is_row(el: Any) -> bool:
        return getattr(el, "tagName", None) == "table:table-row"

    def _is_cell(el: Any) -> bool:
        return getattr(el, "tagName", None) == "table:table-cell"

    def _cell_text(cell: Any) -> str:
        txt = ""
        for node in getattr(cell, "childNodes", []):
            if getattr(node, "tagName", None) == "text:p":
                first = getattr(node, "firstChild", None)
                txt += (getattr(first, "data", "") if first else "")
        return txt.strip()

    # find existing _ZS_META by table:name
    meta_table = None
    tables = [e for e in getattr(doc.spreadsheet, "childNodes", []) if _is_table(e)]
    for t in tables:
        if t.getAttribute("table:name") == "_ZS_META":
            meta_table = t
            break

    # create if missing
    if meta_table is None:
        meta_table = Table(name="_ZS_META")
        try:
            meta_table.setAttribute("table:visibility", "collapse")
        except Exception:
            pass
        doc.spreadsheet.addElement(meta_table)
        header = TableRow()
        for h in ("month", "color_hex"):
            c = TableCell(); c.addElement(P(text=h)); header.addElement(c)
        meta_table.addElement(header)

    # ensure header row texts exactly match
    rows = [e for e in getattr(meta_table, "childNodes", []) if _is_row(e)]
    if not rows:
        header = TableRow()
        for h in ("month", "color_hex"):
            c = TableCell(); c.addElement(P(text=h)); header.addElement(c)
        meta_table.addElement(header)
        rows = [header]

    header_cells = [e for e in getattr(rows[0], "childNodes", []) if _is_cell(e)]
    want_hdr = ("month", "color_hex")
    need_fix = len(header_cells) < 2 or _cell_text(header_cells[0]) != "month" or _cell_text(header_cells[1]) != "color_hex"
    if need_fix:
        for node in list(getattr(rows[0], "childNodes", [])):
            rows[0].removeChild(node)
        for h in want_hdr:
            c = TableCell(); c.addElement(P(text=h)); rows[0].addElement(c)

    # index existing months
    existing = {}
    rows = [e for e in getattr(meta_table, "childNodes", []) if _is_row(e)]
    for r in rows[1:]:
        cells = [e for e in getattr(r, "childNodes", []) if _is_cell(e)]
        if not cells:
            continue
        m_txt = _cell_text(cells[0])
        try:
            m_int = int(m_txt)
        except Exception:
            continue
        if 1 <= m_int <= 12 and m_int not in existing:
            existing[m_int] = r

    # ensure 1..12 present
    for m in range(1, 13):
        if m not in existing:
            row = TableRow()
            c1 = TableCell(); c1.addElement(P(text=str(m)))
            c2 = TableCell(); c2.addElement(P(text=""))
            row.addElement(c1); row.addElement(c2)
            meta_table.addElement(row)

    return meta_table


def main():
    """Bootstrap entry-point. No features yet — functions will be added incrementally."""
    print("ZS CLI bootstrap — no features yet. Next commits will add functions one by one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

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

    def _is_table(el) -> bool:
        return getattr(el, "tagName", None) == "table:table"

    def _is_row(el) -> bool:
        return getattr(el, "tagName", None) == "table:table-row"

    def _is_cell(el) -> bool:
        return getattr(el, "tagName", None) == "table:table-cell"

    def _cell_text(cell: TableCell) -> str:
        txt = ""
        for ch in cell.childNodes:
            if getattr(ch, "tagName", None) == "text:p":
                txt += (getattr(ch, "firstChild", None).data
                        if getattr(ch, "firstChild", None) else "")
        return txt.strip()

    # find existing _ZS_META by table:name
    meta_tbl = None
    tables = [e for e in doc.spreadsheet.childNodes if _is_table(e)]
    for t in tables:
        if t.getAttribute("table:name") == "_ZS_META":
            meta_tbl = t
            break

    # create if missing
    if meta_tbl is None:
        meta_tbl = Table(name="_ZS_META")
        # Best-effort "hidden": not all apps honor this in ODS
        try:
            meta_tbl.setAttribute("table:visibility", "collapse")
        except Exception:
            pass
        doc.spreadsheet.addElement(meta_tbl)
        hdr = TableRow()
        for h in ("month", "color_hex"):
            c = TableCell(); c.addElement(P(text=h)); hdr.addElement(c)
        meta_tbl.addElement(hdr)

    # ensure header row texts exactly match
    rows = [e for e in meta_tbl.childNodes if _is_row(e)]
    if not rows:
        hdr = TableRow()
        for h in ("month", "color_hex"):
            c = TableCell(); c.addElement(P(text=h)); hdr.addElement(c)
        meta_tbl.addElement(hdr)
        rows = [hdr]

    hdr_cells = [e for e in rows[0].childNodes if _is_cell(e)]
    want_hdr = ("month", "color_hex")
    need_fix = False
    for i, want in enumerate(want_hdr):
        if i >= len(hdr_cells) or _cell_text(hdr_cells[i]) != want:
            need_fix = True
            break
    if need_fix:
        for ch in list(rows[0].childNodes):
            rows[0].removeChild(ch)
        for h in want_hdr:
            c = TableCell(); c.addElement(P(text=h)); rows[0].addElement(c)

    # index existing months
    existing = {}
    rows = [e for e in meta_tbl.childNodes if _is_row(e)]
    for r in rows[1:]:
        cells = [e for e in r.childNodes if _is_cell(e)]
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
            meta_tbl.addElement(row)

    return meta_tbl


def main():
    """Bootstrap entry-point. No features yet — functions will be added incrementally."""
    print("ZS CLI bootstrap — no features yet. Next commits will add functions one by one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

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
        except (ValueError, OSError, UnicodeDecodeError):
            # Fall through to defaults if the file is malformed or unreadable
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

    def _is_table(el: Any) -> bool:
        return getattr(el, "tagName", None) == "table:table"

    def _is_row(el: Any) -> bool:
        return getattr(el, "tagName", None) == "table:table-row"

    def _is_cell(el: Any) -> bool:
        return getattr(el, "tagName", None) == "table:table-cell"

    def _cell_text(cell_el: Any) -> str:
        text_acc = ""
        for node_el in getattr(cell_el, "childNodes", []):
            if getattr(node_el, "tagName", None) == "text:p":
                first_child_el = getattr(node_el, "firstChild", None)
                text_acc += (getattr(first_child_el, "data", "") if first_child_el else "")
        return text_acc.strip()

    def _append_header_row(table_el: Any) -> None:
        row = TableRow()
        for h in headers:
            c = TableCell()
            c.addElement(P(text=h))
            row.addElement(c)
        table_el.addElement(row)

    try:
        if path.exists():
            doc = load(str(path))
            tables = [el for el in getattr(doc.spreadsheet, "childNodes", []) if _is_table(el)]
            if not tables:
                t_el = Table(name="List1")
                doc.spreadsheet.addElement(t_el)
                _append_header_row(t_el)
                doc.save(str(path))
                return

            t_el = tables[0]
            rows = [el for el in getattr(t_el, "childNodes", []) if _is_row(el)]
            if not rows:
                _append_header_row(t_el)
                doc.save(str(path))
                return

            first_row = rows[0]
            cells = [el for el in getattr(first_row, "childNodes", []) if _is_cell(el)]
            texts = [_cell_text(cell_el) for cell_el in cells]
            if texts[:len(headers)] != headers:
                for node_el in list(getattr(t_el, "childNodes", [])):
                    t_el.removeChild(node_el)
                _append_header_row(t_el)

            doc.save(str(path))
            return
    # noinspection PyBroadException
    except Exception:
        # odfpy may raise various internal exceptions; we fall back to creating a new file
        pass

    doc = OpenDocumentSpreadsheet()
    t_el = Table(name="List1")
    doc.spreadsheet.addElement(t_el)
    _append_header_row(t_el)
    doc.save(str(path))


def ensure_meta_sheet(doc):
    """Ensure hidden-like _ZS_META sheet with MONTH_COLORS (month|color_hex) exists.
    The sheet is internal and may be skipped by exports. Returns the meta table element.
    """

    def _is_table(el: Any) -> bool:
        return getattr(el, "tagName", None) == "table:table"

    def _is_row(el: Any) -> bool:
        return getattr(el, "tagName", None) == "table:table-row"

    def _is_cell(el: Any) -> bool:
        return getattr(el, "tagName", None) == "table:table-cell"

    def _cell_text(cell_el: Any) -> str:
        text_acc = ""
        for node_el in getattr(cell_el, "childNodes", []):
            if getattr(node_el, "tagName", None) == "text:p":
                first_child_el = getattr(node_el, "firstChild", None)
                text_acc += (getattr(first_child_el, "data", "") if first_child_el else "")
        return text_acc.strip()

    # find existing _ZS_META by table:name
    meta_table = None
    tables = [el for el in getattr(doc.spreadsheet, "childNodes", []) if _is_table(el)]
    for table_el in tables:
        if table_el.getAttribute("table:name") == "_ZS_META":
            meta_table = table_el
            break

    # create if missing
    if meta_table is None:
        meta_table = Table(name="_ZS_META")
        try:
            meta_table.setAttribute("table:visibility", "collapse")
        except (AttributeError, TypeError, ValueError):
            pass
        doc.spreadsheet.addElement(meta_table)
        header_row = TableRow()
        for hdr in ("month", "color_hex"):
            c = TableCell()
            c.addElement(P(text=hdr))
            header_row.addElement(c)
        meta_table.addElement(header_row)

    # ensure header row texts exactly match
    rows = [el for el in getattr(meta_table, "childNodes", []) if _is_row(el)]
    if not rows:
        header_row = TableRow()
        for hdr in ("month", "color_hex"):
            c = TableCell()
            c.addElement(P(text=hdr))
            header_row.addElement(c)
        meta_table.addElement(header_row)
        rows = [header_row]

    header_cells = [el for el in getattr(rows[0], "childNodes", []) if _is_cell(el)]
    need_fix = (
        len(header_cells) < 2
        or _cell_text(header_cells[0]) != "month"
        or _cell_text(header_cells[1]) != "color_hex"
    )
    if need_fix:
        for node_el in list(getattr(rows[0], "childNodes", [])):
            rows[0].removeChild(node_el)
        for hdr in ("month", "color_hex"):
            c = TableCell()
            c.addElement(P(text=hdr))
            rows[0].addElement(c)

    # index existing months
    existing = {}
    rows = [el for el in getattr(meta_table, "childNodes", []) if _is_row(el)]
    for r in rows[1:]:
        cells = [el for el in getattr(r, "childNodes", []) if _is_cell(el)]
        if not cells:
            continue
        m_txt = _cell_text(cells[0])
        try:
            m_int = int(m_txt)
        except ValueError:
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

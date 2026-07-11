#!/usr/bin/env python3
"""generate_templates.py — builds /templates/<SECTION>.xlsx|csv from
pipeline_config.yaml. Templates and pipeline/validate.py both read the same
config, so a template can never drift out of sync with what CI validates.

Run whenever pipeline_config.yaml's header definitions change:
    python generate_templates.py
"""
import csv
from pathlib import Path
import openpyxl

from pipeline.config import load_config

BASE = Path(__file__).parent
TEMPLATES_DIR = BASE / "templates"

NOTE = ("Fill in your data below the header row shown here. Columns not "
        "listed are ignored by the dashboard pipeline — you don't need to "
        "remove them if your source export includes extra columns, but do "
        "not rename or reorder the columns listed below.")


def _write_xlsx_sheet(ws, sheet_cfg: dict):
    header_row = 1 if sheet_cfg["header_row"] in ("dynamic", 1) else sheet_cfg["header_row"]
    specs = sheet_cfg["required_headers"]
    if any(spec.get("column") is not None for spec in specs):
        # Column-pinned layout (e.g. ECR sheet, where position matters).
        for spec in specs:
            col = spec.get("column")
            if col is not None:
                ws.cell(row=header_row, column=col + 1, value=spec["name"])
    else:
        # No pinned columns (e.g. SWAP, POSB, PLI/RPLI sheets) — lay
        # headers out left to right in the order given.
        for i, spec in enumerate(specs):
            ws.cell(row=header_row, column=i + 1, value=spec["name"])


def generate_xlsx_template(name: str, section_cfg: dict):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for sheet_name, sheet_cfg in section_cfg["sheets"].items():
        ws = wb.create_sheet(sheet_name)
        _write_xlsx_sheet(ws, sheet_cfg)
    info = wb.create_sheet("README", 0)
    info["A1"] = f"{section_cfg['label']} — upload template"
    info["A2"] = NOTE
    out = TEMPLATES_DIR / f"{name}.xlsx"
    wb.save(out)
    return out


def generate_csv_template(name: str, section_cfg: dict):
    out = TEMPLATES_DIR / f"{name}.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(section_cfg["csv_headers"]["required"])
    return out


def main():
    cfg = load_config()
    TEMPLATES_DIR.mkdir(exist_ok=True)
    for name, section_cfg in cfg["sections"].items():
        file_type = section_cfg.get("file_type", "xlsx")
        if file_type == "xlsx":
            out = generate_xlsx_template(name, section_cfg)
        elif file_type == "csv":
            out = generate_csv_template(name, section_cfg)
        else:
            print(f"  SKIP {name}: unknown file_type {file_type!r}")
            continue
        print(f"  Wrote {out.relative_to(BASE)}")


if __name__ == "__main__":
    main()

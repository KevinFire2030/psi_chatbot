#!/usr/bin/env python3
"""Convert GSCM PSI report-style XLSX into a long-form DuckDB data mart.

The source workbook is a human-readable wide Excel report with hundreds of
period/metric columns. This script keeps source Excel column addresses and
header metadata so natural-language query layers can disambiguate duplicate
business labels such as "1분기Demand".
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Iterable

XLSX_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

DIMENSION_NAMES = [
    "key",
    "region_entity",
    "psi_model_26",
    "psi_model_25",
    "sales_model_26",
    "sales_model_25",
    "market_growth_key",
    "reserved_blank",
    "business_unit",
    "smart_category",
    "product_group",
    "model_code",
]

PERIOD_PATTERN = re.compile(r"^(1분기|2분기|3분기|상반기|[1-9]월)(.+)$")
COMPARISON_SUFFIXES = [
    "전주전년比(%)",
    "전년比(매출)",
    "전년比(수량)",
    "전년比(배수)",
    "경영比(매출)",
    "경영比(수량)",
    "경영比(%)",
    "W12比",
    "T06比",
    "확판比",
    "전주比",
    "적정比",
    "(%)",
]


def q(tag: str) -> str:
    return f"{{{XLSX_NS}}}{tag}"


def col_to_index(col: str) -> int:
    """Convert Excel column letters to zero-based index."""
    letters = "".join(ch for ch in col.upper() if ch.isalpha())
    if not letters:
        raise ValueError(f"Invalid Excel column: {col!r}")
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def index_to_col(index: int) -> str:
    """Convert zero-based index to Excel column letters."""
    if index < 0:
        raise ValueError("index must be >= 0")
    n = index + 1
    out = ""
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def cell_ref_to_index(cell_ref: str) -> int:
    return col_to_index("".join(ch for ch in cell_ref if ch.isalpha()))


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\n", " ")).strip()


def parse_number(value: str | None) -> float | None:
    text = normalize_text(value).replace(",", "")
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_metric_header(header: str) -> dict[str, str]:
    """Split a Korean PSI metric header into period, metric, and comparison.

    Examples:
    - 3분기Short-Ch_Constraint전주比 -> period=3분기, metric=Short-Ch_Constraint, comparison=전주比
    - 9월WOS(EDI+FOTA)적정比 -> period=9월, metric=WOS(EDI+FOTA), comparison=적정比
    """
    clean = normalize_text(header)
    match = PERIOD_PATTERN.match(clean)
    if not match:
        return {"period": "", "metric": clean, "comparison": ""}
    period, rest = match.groups()
    comparison = ""
    metric = rest
    for suffix in COMPARISON_SUFFIXES:
        if rest.endswith(suffix):
            comparison = suffix
            metric = rest[: -len(suffix)]
            break
    return {"period": period, "metric": metric, "comparison": comparison}


def unique_metric_key(header: str, source_column: str, sub_header: str = "") -> str:
    parsed = parse_metric_header(header)
    parts = [
        parsed["period"] or "no_period",
        parsed["metric"] or "no_metric",
        parsed["comparison"] or "actual",
        normalize_text(sub_header) or "no_sub_header",
        source_column,
    ]
    return "__".join(re.sub(r"[^0-9A-Za-z가-힣_()+.-]+", "_", p).strip("_") for p in parts)


@dataclass(frozen=True)
class SheetData:
    name: str
    rows: list[list[str]]
    max_columns: int


def _cell_text(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.get("t")
    if cell_type == "s":
        value = cell.find(q("v"))
        if value is None or value.text is None:
            return ""
        return shared_strings[int(value.text)]
    if cell_type == "inlineStr":
        return "".join((node.text or "") for node in cell.iter(q("t")))
    value = cell.find(q("v"))
    return "" if value is None or value.text is None else value.text


def read_xlsx_first_sheet(path: str, max_columns: int | None = None) -> SheetData:
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            shared = ["".join((t.text or "") for t in si.iter(q("t"))) for si in root.findall(q("si"))]

        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_by_id = {rel.get("Id"): rel.get("Target") for rel in rels}
        first_sheet = workbook.find(q("sheets")).find(q("sheet"))  # type: ignore[union-attr]
        if first_sheet is None:
            raise ValueError("Workbook has no sheets")
        sheet_name = first_sheet.get("name") or "Sheet1"
        rel_id = first_sheet.get(f"{{{REL_NS}}}id")
        target = rel_by_id.get(rel_id)
        if not target:
            raise ValueError("Unable to resolve first worksheet path")
        if not target.startswith("xl/"):
            target = "xl/" + target

        sheet = ET.fromstring(zf.read(target))
        dimension = sheet.find(q("dimension"))
        if max_columns is None and dimension is not None and dimension.get("ref"):
            end_ref = dimension.get("ref", "A1").split(":")[-1]
            max_columns = cell_ref_to_index(end_ref) + 1
        max_columns = max_columns or 0

        rows: list[list[str]] = []
        for row in sheet.findall(".//" + q("sheetData") + "/" + q("row")):
            arr = [""] * max_columns
            for cell in row.findall(q("c")):
                idx = cell_ref_to_index(cell.get("r") or "A1")
                if idx >= max_columns:
                    arr.extend([""] * (idx + 1 - len(arr)))
                    max_columns = idx + 1
                arr[idx] = normalize_text(_cell_text(cell, shared))
            rows.append(arr)
        return SheetData(sheet_name, rows, max_columns)


def build_column_metadata(rows: list[list[str]], max_columns: int) -> list[dict[str, str | int]]:
    row1 = rows[0]
    row12 = rows[11] if len(rows) > 11 else [""] * max_columns
    row13 = rows[12] if len(rows) > 12 else [""] * max_columns
    row14 = rows[13] if len(rows) > 13 else [""] * max_columns
    metadata: list[dict[str, str | int]] = []
    for idx in range(12, max_columns):
        header = row1[idx] if idx < len(row1) else ""
        if not header:
            continue
        parsed = parse_metric_header(header)
        source_column = index_to_col(idx)
        metadata.append(
            {
                "column_index": idx,
                "source_column": source_column,
                "raw_header": header,
                "period": parsed["period"],
                "metric": parsed["metric"],
                "comparison": parsed["comparison"],
                "sub_header": row12[idx] if idx < len(row12) else "",
                "header_row_13": row13[idx] if idx < len(row13) else "",
                "header_row_14": row14[idx] if idx < len(row14) else "",
                "metric_key": unique_metric_key(header, source_column, row12[idx] if idx < len(row12) else ""),
            }
        )
    return metadata


def iter_long_rows(rows: list[list[str]], metadata: list[dict[str, str | int]]) -> Iterable[tuple]:
    for excel_row_number, row in enumerate(rows[14:], start=15):
        if not any(row):
            continue
        dims = [(row[i] if i < len(row) else "") for i in range(12)]
        for meta in metadata:
            col_idx = int(meta["column_index"])
            raw_value = row[col_idx] if col_idx < len(row) else ""
            numeric_value = parse_number(raw_value)
            if numeric_value is None:
                continue
            yield (
                excel_row_number,
                *dims,
                meta["source_column"],
                meta["raw_header"],
                meta["period"],
                meta["metric"],
                meta["comparison"],
                meta["sub_header"],
                meta["header_row_13"],
                meta["header_row_14"],
                meta["metric_key"],
                numeric_value,
                raw_value,
            )


def create_duckdb(input_xlsx: str, output_db: str, sheet: SheetData) -> dict[str, int | str]:
    try:
        import duckdb
    except ImportError as exc:
        raise SystemExit("duckdb package is required. Run: uv run --with duckdb python3 PoC1/scripts/preprocess_psi.py") from exc

    if os.path.exists(output_db):
        os.remove(output_db)

    metadata = build_column_metadata(sheet.rows, sheet.max_columns)
    long_columns = [
        "excel_row_number INTEGER",
        "key TEXT",
        "region_entity TEXT",
        "psi_model_26 TEXT",
        "psi_model_25 TEXT",
        "sales_model_26 TEXT",
        "sales_model_25 TEXT",
        "market_growth_key TEXT",
        "reserved_blank TEXT",
        "business_unit TEXT",
        "smart_category TEXT",
        "product_group TEXT",
        "model_code TEXT",
        "source_column TEXT",
        "raw_header TEXT",
        "period TEXT",
        "metric TEXT",
        "comparison TEXT",
        "sub_header TEXT",
        "header_row_13 TEXT",
        "header_row_14 TEXT",
        "metric_key TEXT",
        "value DOUBLE",
        "raw_value TEXT",
    ]
    con = duckdb.connect(output_db)
    try:
        con.execute("CREATE TABLE psi_long (" + ", ".join(long_columns) + ")")
        con.execute(
            """
            CREATE TABLE psi_column_metadata (
                column_index INTEGER,
                source_column TEXT,
                raw_header TEXT,
                period TEXT,
                metric TEXT,
                comparison TEXT,
                sub_header TEXT,
                header_row_13 TEXT,
                header_row_14 TEXT,
                metric_key TEXT
            )
            """
        )
        con.execute(
            """
            CREATE TABLE psi_load_info (
                source_file TEXT,
                sheet_name TEXT,
                source_rows INTEGER,
                source_columns INTEGER,
                data_start_row INTEGER
            )
            """
        )
        con.executemany(
            "INSERT INTO psi_column_metadata VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    int(m["column_index"]),
                    m["source_column"],
                    m["raw_header"],
                    m["period"],
                    m["metric"],
                    m["comparison"],
                    m["sub_header"],
                    m["header_row_13"],
                    m["header_row_14"],
                    m["metric_key"],
                )
                for m in metadata
            ],
        )
        con.execute("INSERT INTO psi_load_info VALUES (?, ?, ?, ?, ?)", [input_xlsx, sheet.name, len(sheet.rows), sheet.max_columns, 15])

        count = 0
        column_names = [definition.split()[0] for definition in long_columns]
        with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", suffix=".csv", delete=False) as temp_csv:
            temp_csv_path = temp_csv.name
            writer = csv.writer(temp_csv)
            writer.writerow(column_names)
            for record in iter_long_rows(sheet.rows, metadata):
                writer.writerow(record)
                count += 1

        try:
            escaped_csv_path = temp_csv_path.replace("'", "''")
            con.execute(f"COPY psi_long FROM '{escaped_csv_path}' (HEADER, DELIMITER ',', NULLSTR '\\0')")
        finally:
            try:
                os.remove(temp_csv_path)
            except OSError:
                pass

        con.execute("CREATE INDEX idx_psi_long_period_metric ON psi_long(period, metric)")
        con.execute("CREATE INDEX idx_psi_long_region ON psi_long(region_entity)")
        con.execute("CREATE INDEX idx_psi_long_model ON psi_long(psi_model_26, model_code)")
        return {
            "sheet_name": sheet.name,
            "source_rows": len(sheet.rows),
            "source_columns": sheet.max_columns,
            "metric_columns": len(metadata),
            "long_rows": count,
        }
    finally:
        con.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert sample PSI XLSX to long-form DuckDB")
    parser.add_argument("--input", default="PoC1/sample_psi/sample_psi.xlsx", help="Source PSI .xlsx path")
    parser.add_argument("--output", default="PoC1/data/psi.duckdb", help="Output DuckDB path")
    args = parser.parse_args(argv)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    sheet = read_xlsx_first_sheet(args.input)
    stats = create_duckdb(args.input, args.output, sheet)
    print("Created", args.output)
    for key, value in stats.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

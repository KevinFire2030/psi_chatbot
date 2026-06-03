"""Deterministic DuckDB fast paths for common GSCM PSI chat questions.

The normal PoC2 flow intentionally goes through Hermes webhook agent runs.  For
high-frequency, low-ambiguity PSI questions this module bypasses the LLM/tool
loop and answers from DuckDB directly in ~milliseconds while preserving the same
Korean business answer style.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
DEFAULT_FAST_PATH_DB = PROJECT_ROOT / "data" / "psi.duckdb"
PLAN_BASIS = "W23_Pre plan 기준"

PERIOD_RE = re.compile(r"(1분기|2분기|3분기|상반기|[1-9]월)", re.IGNORECASE)
ENTITY_RE = re.compile(r"\b([A-Z]{2,6})\b", re.IGNORECASE)


@dataclass(frozen=True)
class FastPathIntent:
    kind: str
    period: str
    region_entity: str | None = None


def fast_path_enabled() -> bool:
    return os.getenv("PSI_FAST_PATH_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}


def default_db_path() -> str:
    return os.getenv("PSI_FAST_PATH_DB", str(DEFAULT_FAST_PATH_DB))


def detect_fast_path_intent(question: str) -> FastPathIntent | None:
    normalized = question.strip()
    lower = normalized.lower()
    period_match = PERIOD_RE.search(normalized)
    if not period_match:
        return None
    period = period_match.group(1)

    if "사업부" in normalized and "wos" in lower:
        return FastPathIntent(kind="business_unit_wos", period=period)

    if any(word in normalized for word in ["매출", "sales", "revenue"]):
        entity_match = ENTITY_RE.search(normalized)
        if entity_match:
            return FastPathIntent(
                kind="entity_quarter_sales",
                period=period,
                region_entity=entity_match.group(1).upper(),
            )
    return None


def build_fast_path_answer(question: str, db_path: str | None = None) -> str | None:
    intent = detect_fast_path_intent(question)
    if intent is None:
        return None
    db = db_path or default_db_path()
    if intent.kind == "entity_quarter_sales" and intent.region_entity:
        return _build_entity_quarter_sales_answer(intent, db)
    if intent.kind == "business_unit_wos":
        return _build_business_unit_wos_answer(intent, db)
    return None


def _connect(db_path: str):
    try:
        import duckdb
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError("duckdb package is required for PSI fast path") from exc
    return duckdb.connect(db_path, read_only=True)


def _single_value(con: Any, sql: str, params: list[Any]) -> float | None:
    row = con.execute(sql, params).fetchone()
    if not row or row[0] is None:
        return None
    return float(row[0])


def _format_musd(raw_value: float | None) -> str:
    if raw_value is None:
        return "N/A"
    return f"{raw_value / 1_000_000:,.1f} 백만불"


def _format_pct_ratio(raw_ratio: float | None) -> str:
    if raw_ratio is None:
        return "N/A"
    return f"{raw_ratio * 100:.1f}%"


def _build_entity_quarter_sales_answer(intent: FastPathIntent, db_path: str) -> str:
    # GSCM sales values are stored as raw dollars; present in million dollars.
    where_total = """
        period = ?
        AND region_entity = ?
        AND psi_model_26 = 'Total'
        AND sales_model_26 = 'Total(PC포함)'
    """
    with _connect(db_path) as con:
        current = _single_value(
            con,
            f"""
            SELECT value FROM psi_long
            WHERE {where_total}
              AND metric = '매출'
              AND sub_header = 'FP (매출)'
              AND comparison = ''
            LIMIT 1
            """,
            [intent.period, intent.region_entity],
        )
        prior = _single_value(
            con,
            f"""
            SELECT value FROM psi_long
            WHERE {where_total}
              AND metric = '매출전년'
              AND sub_header = '25년 (매출)'
              AND comparison = ''
            LIMIT 1
            """,
            [intent.period, intent.region_entity],
        )
        yoy_delta = _single_value(
            con,
            f"""
            SELECT value FROM psi_long
            WHERE {where_total}
              AND metric = '매출'
              AND comparison = '전년比(매출)'
            LIMIT 1
            """,
            [intent.period, intent.region_entity],
        )
        yoy_ratio = _single_value(
            con,
            f"""
            SELECT value FROM psi_long
            WHERE {where_total}
              AND metric = '매출'
              AND comparison = '(%)'
            LIMIT 1
            """,
            [intent.period, intent.region_entity],
        )
        wow_delta = _single_value(
            con,
            f"""
            SELECT value FROM psi_long
            WHERE {where_total}
              AND metric = '매출'
              AND comparison = '전주比'
            LIMIT 1
            """,
            [intent.period, intent.region_entity],
        )

    if current is None:
        raise ValueError(f"fast path sales row not found: period={intent.period}, region_entity={intent.region_entity}")

    return "\n".join(
        [
            PLAN_BASIS,
            "",
            f"{intent.period} **{intent.region_entity} 매출(FP)**은 **{_format_musd(current)}**입니다.",
            "",
            f"- 전년 매출: **{_format_musd(prior)}**",
            f"- 전년 대비: **{_format_musd(yoy_delta)}**",
            f"- 전년비: **{_format_pct_ratio(yoy_ratio)}**",
            f"- 전주 대비: **{_format_musd(wow_delta)}**",
        ]
    )


def _build_business_unit_wos_answer(intent: FastPathIntent, db_path: str) -> str:
    where_total = """
        period = ?
        AND business_unit = '사업부'
        AND region_entity = 'Total'
        AND psi_model_26 = 'Total'
    """
    with _connect(db_path) as con:
        current = _single_value(
            con,
            f"""
            SELECT value FROM psi_long
            WHERE {where_total}
              AND metric = 'WOS(EDI+FOTA)'
              AND sub_header = 'WOS'
              AND comparison = ''
            LIMIT 1
            """,
            [intent.period],
        )
        target = _single_value(
            con,
            f"""
            SELECT value FROM psi_long
            WHERE {where_total}
              AND metric = 'T.WOS'
              AND sub_header = 'T.WOS'
              AND comparison = ''
            LIMIT 1
            """,
            [intent.period],
        )
        ratio = _single_value(
            con,
            f"""
            SELECT value FROM psi_long
            WHERE {where_total}
              AND metric = 'WOS(EDI+FOTA)'
              AND comparison = '적정比'
            LIMIT 1
            """,
            [intent.period],
        )
        previous_delta = _single_value(
            con,
            f"""
            SELECT value FROM psi_long
            WHERE {where_total}
              AND metric = 'WOS(EDI+FOTA)전주'
              AND comparison = ''
            LIMIT 1
            """,
            [intent.period],
        )
        f4 = _single_value(
            con,
            f"""
            SELECT value FROM psi_long
            WHERE {where_total}
              AND metric = 'WOS (F4)'
              AND sub_header = 'WOS (F4)'
              AND comparison = ''
            LIMIT 1
            """,
            [intent.period],
        )

    if current is None:
        raise ValueError(f"fast path WOS row not found: period={intent.period}, business_unit=사업부")

    return "\n".join(
        [
            PLAN_BASIS,
            "",
            f"{intent.period} 사업부 WOS는 **{current:.2f}주**입니다.",
            "",
            f"- T.WOS: **{target:.2f}주**" if target is not None else "- T.WOS: **N/A**",
            f"- 적정比: **{ratio * 100:.1f}%**" if ratio is not None else "- 적정比: **N/A**",
            f"- 전주 대비: **{previous_delta:+.2f}주**" if previous_delta is not None else "- 전주 대비: **N/A**",
            f"- WOS(F4): **{f4:.2f}주**" if f4 is not None else "- WOS(F4): **N/A**",
        ]
    )

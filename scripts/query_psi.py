#!/usr/bin/env python3
"""Tiny rule-based natural-language PSI query CLI on top of data/psi.duckdb.

This is intentionally small for the PoC bootstrap. It proves the long-form data
mart can answer Korean business questions before adding an LLM/API/UI layer.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass

METRIC_ALIASES = {
    "숏": "Short",
    "short": "Short",
    "채널숏": "Short-Ch_Constraint",
    "재고": "Ch.Inventory(EDI+FOTA)",
    "유통재고": "Ch.Inventory(EDI+FOTA)",
    "wos": "WOS(EDI+FOTA)",
    "셀아웃": "Sell-Out",
    "sell-out": "Sell-Out",
    "매출": "매출",
    "물량": "물량",
    "수요": "Demand",
    "demand": "Demand",
    "gi": "GI",
}

PERIOD_RE = re.compile(r"(1분기|2분기|3분기|상반기|[1-9]월)", re.IGNORECASE)
TOP_RE = re.compile(r"top\s*(\d+)|상위\s*(\d+)", re.IGNORECASE)
THRESHOLD_RE = re.compile(r"(?:이|가)?\s*(\d+(?:\.\d+)?)\s*(?:이상|초과)")


@dataclass(frozen=True)
class QueryIntent:
    period: str
    metric: str
    limit: int = 10
    threshold: float | None = None
    order: str = "desc"


def parse_query(question: str) -> QueryIntent:
    text = question.strip()
    period_match = PERIOD_RE.search(text)
    if not period_match:
        raise ValueError("기간을 찾지 못했습니다. 예: 1분기, 3분기, 9월")
    period = period_match.group(1)

    lower = text.lower()
    metric = ""
    # Prefer longer Korean aliases first so 채널숏 wins over 숏.
    for alias in sorted(METRIC_ALIASES, key=len, reverse=True):
        if alias.lower() in lower:
            metric = METRIC_ALIASES[alias]
            break
    if not metric:
        raise ValueError("지표를 찾지 못했습니다. 예: 매출, 숏, WOS, 재고, 셀아웃")

    top_match = TOP_RE.search(text)
    limit = 10
    if top_match:
        limit = int(next(group for group in top_match.groups() if group))

    threshold_match = THRESHOLD_RE.search(text)
    threshold = float(threshold_match.group(1)) if threshold_match else None

    order = "asc" if any(word in text for word in ["낮은", "작은", "하위", "최저"]) else "desc"
    return QueryIntent(period=period, metric=metric, limit=limit, threshold=threshold, order=order)


def run_query(db_path: str, intent: QueryIntent) -> list[tuple[str, float]]:
    try:
        import duckdb
    except ImportError as exc:
        raise SystemExit("duckdb package is required. Run: uv run --with duckdb python3 scripts/query_psi.py ...") from exc

    where = [
        "period = ?",
        "metric = ?",
        "comparison = ''",
        "psi_model_26 = 'Total'",
        "region_entity <> 'Total'",
    ]
    params: list[object] = [intent.period, intent.metric]
    if intent.threshold is not None:
        where.append("value >= ?")
        params.append(intent.threshold)
    order_sql = "ASC" if intent.order == "asc" else "DESC"
    params.append(intent.limit)
    sql = f"""
        SELECT region_entity, value
        FROM psi_long
        WHERE {' AND '.join(where)}
        ORDER BY value {order_sql}
        LIMIT ?
    """
    with duckdb.connect(db_path, read_only=True) as con:
        return con.execute(sql, params).fetchall()


def main() -> int:
    parser = argparse.ArgumentParser(description="Query PSI DuckDB with a simple Korean natural-language question")
    parser.add_argument("question", help="예: '3분기 Short 상위 5개 지역 보여줘'")
    parser.add_argument("--db", default="data/psi.duckdb")
    args = parser.parse_args()

    intent = parse_query(args.question)
    rows = run_query(args.db, intent)
    print(f"질문: {args.question}")
    print(f"해석: period={intent.period}, metric={intent.metric}, threshold={intent.threshold}, limit={intent.limit}")
    for rank, (region, value) in enumerate(rows, start=1):
        print(f"{rank}. {region}: {value:g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

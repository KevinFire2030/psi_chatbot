from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from typing import Any

from scripts.query_psi import QueryIntent, parse_query


@dataclass(frozen=True)
class PsiResultRow:
    region_entity: str
    value: float


@dataclass(frozen=True)
class PsiQueryResult:
    question: str
    intent: QueryIntent
    rows: list[PsiResultRow]

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "intent": asdict(self.intent),
            "rows": [asdict(row) for row in self.rows],
        }


class PsiQueryService:
    def __init__(self, db_path: str = "data/psi.duckdb") -> None:
        self.db_path = db_path

    def query(self, question: str) -> PsiQueryResult:
        intent = parse_query(question)
        rows = self._run_intent(intent)
        return PsiQueryResult(question=question, intent=intent, rows=rows)

    def schema_summary(self) -> dict[str, Any]:
        try:
            import duckdb
        except ImportError as exc:
            raise RuntimeError("duckdb package is required") from exc

        with duckdb.connect(self.db_path, read_only=True) as con:
            periods = [row[0] for row in con.execute("SELECT DISTINCT period FROM psi_column_metadata WHERE period <> '' ORDER BY period").fetchall()]
            metrics = [row[0] for row in con.execute("SELECT DISTINCT metric FROM psi_column_metadata WHERE metric <> '' ORDER BY metric").fetchall()]
            row_count = con.execute("SELECT COUNT(*) FROM psi_long").fetchone()[0]
        return {"periods": periods, "metrics": metrics, "psi_long_rows": row_count}

    def _run_intent(self, intent: QueryIntent) -> list[PsiResultRow]:
        try:
            import duckdb
        except ImportError as exc:
            raise RuntimeError("duckdb package is required") from exc

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
        with duckdb.connect(self.db_path, read_only=True) as con:
            return [PsiResultRow(region_entity=row[0], value=float(row[1])) for row in con.execute(sql, params).fetchall()]

    def initialize_schema_for_test(self) -> None:
        try:
            import duckdb
        except ImportError as exc:
            raise RuntimeError("duckdb package is required") from exc

        if os.path.exists(self.db_path) and os.path.getsize(self.db_path) == 0:
            os.remove(self.db_path)

        with duckdb.connect(self.db_path) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS psi_long (
                    region_entity TEXT,
                    period TEXT,
                    metric TEXT,
                    comparison TEXT,
                    psi_model_26 TEXT,
                    value DOUBLE
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS psi_column_metadata (
                    period TEXT,
                    metric TEXT
                )
                """
            )

    def insert_test_row(self, region_entity: str, period: str, metric: str, value: float) -> None:
        try:
            import duckdb
        except ImportError as exc:
            raise RuntimeError("duckdb package is required") from exc

        with duckdb.connect(self.db_path) as con:
            con.execute(
                "INSERT INTO psi_long VALUES (?, ?, ?, '', 'Total', ?)",
                [region_entity, period, metric, value],
            )
            con.execute("INSERT INTO psi_column_metadata VALUES (?, ?)", [period, metric])

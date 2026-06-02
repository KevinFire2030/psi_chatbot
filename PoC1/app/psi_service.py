from __future__ import annotations

from dataclasses import asdict, dataclass, field
import os
from typing import Any

from PoC1.app.query_planner import QueryPlan, QueryPlanner


@dataclass(frozen=True)
class PsiResultRow:
    region_entity: str | None = None
    value: float | None = None
    psi_model_26: str | None = None
    delta: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if not self.extra:
            data.pop("extra")
        return {key: value for key, value in data.items() if value is not None}


@dataclass(frozen=True)
class PsiQueryResult:
    question: str
    intent: dict[str, Any]
    rows: list[PsiResultRow]
    sql: str
    explanation: str
    params: list[Any]
    planner: str = "deterministic_llm_ready_planner"

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "intent": self.intent,
            "sql": self.sql,
            "params": self.params,
            "explanation": self.explanation,
            "planner": self.planner,
            "rows": [row.to_dict() for row in self.rows],
        }


class PsiQueryService:
    def __init__(self, db_path: str = "PoC1/data/psi.duckdb", planner: QueryPlanner | None = None) -> None:
        self.db_path = db_path
        self.planner = planner or QueryPlanner()

    def query(self, question: str) -> PsiQueryResult:
        plan = self.planner.plan(question)
        rows = self._run_plan(plan)
        return PsiQueryResult(
            question=question,
            intent=plan.intent,
            rows=rows,
            sql=plan.sql,
            params=plan.params,
            explanation=plan.explanation,
        )

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

    def _run_plan(self, plan: QueryPlan) -> list[PsiResultRow]:
        try:
            import duckdb
        except ImportError as exc:
            raise RuntimeError("duckdb package is required") from exc

        with duckdb.connect(self.db_path, read_only=True) as con:
            raw_rows = con.execute(plan.sql, plan.params).fetchall()

        if plan.result_shape == "model_delta":
            return [
                PsiResultRow(
                    psi_model_26=row[0],
                    value=float(row[2]),
                    delta=float(row[3]),
                    extra={"base_value": float(row[1]), "compare_value": float(row[2])},
                )
                for row in raw_rows
            ]
        return [PsiResultRow(region_entity=row[0], value=float(row[1])) for row in raw_rows]

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

    def insert_test_row(
        self,
        region_entity: str,
        period: str,
        metric: str,
        value: float,
        psi_model_26: str = "Total",
    ) -> None:
        try:
            import duckdb
        except ImportError as exc:
            raise RuntimeError("duckdb package is required") from exc

        with duckdb.connect(self.db_path) as con:
            con.execute(
                "INSERT INTO psi_long VALUES (?, ?, ?, '', ?, ?)",
                [region_entity, period, metric, psi_model_26, value],
            )
            con.execute("INSERT INTO psi_column_metadata VALUES (?, ?)", [period, metric])

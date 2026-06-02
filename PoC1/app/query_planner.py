from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from PoC1.scripts.query_psi import QueryIntent, parse_query

PERIOD_RE = re.compile(r"(1분기|2분기|3분기|상반기|[1-9]월)", re.IGNORECASE)
LIMIT_RE = re.compile(r"top\s*(\d+)|상위\s*(\d+)", re.IGNORECASE)
REGION_RE = re.compile(r"^(.+?)에서")


@dataclass(frozen=True)
class QueryPlan:
    kind: str
    sql: str
    params: list[Any]
    explanation: str
    intent: dict[str, Any]
    result_shape: str
    region_entity: str | None = None
    base_period: str | None = None
    compare_period: str | None = None
    metric: str | None = None


class QueryPlanner:
    """LLM-ready natural-language query planner.

    The current PoC uses deterministic heuristics to produce the same structured
    artifact an LLM planner should return later: intent, SQL, bind params, and a
    Korean explanation. This keeps the API contract stable while allowing a real
    LLM NL→SQL planner to replace or augment `plan()` later.
    """

    def plan(self, question: str) -> QueryPlan:
        if self._looks_like_period_delta_by_model(question):
            return self._plan_period_delta_by_model(question)
        return self._plan_ranked_metric(question)

    def _looks_like_period_delta_by_model(self, question: str) -> bool:
        periods = PERIOD_RE.findall(question)
        return len(periods) >= 2 and any(word in question for word in ["대비", "비교"]) and any(
            word in question for word in ["모델", "model", "Model"]
        )

    def _plan_period_delta_by_model(self, question: str) -> QueryPlan:
        periods = PERIOD_RE.findall(question)
        if len(periods) < 2:
            raise ValueError("비교할 두 기간을 찾지 못했습니다. 예: 2분기 대비 3분기")
        base_period, compare_period = periods[0], periods[1]
        metric = parse_query(compare_period + " " + question).metric
        region_match = REGION_RE.search(question.strip())
        region_entity = region_match.group(1).strip() if region_match else "Total"
        limit = self._parse_limit(question)
        delta_filter = "delta > 0" if any(word in question for word in ["늘어난", "증가", "커진"]) else "delta <> 0"
        sql = f"""
WITH base AS (
    SELECT psi_model_26, SUM(value) AS base_value
    FROM psi_long
    WHERE period = ?
      AND metric = ?
      AND comparison = ''
      AND region_entity = ?
      AND psi_model_26 <> 'Total'
    GROUP BY psi_model_26
), compare AS (
    SELECT psi_model_26, SUM(value) AS compare_value
    FROM psi_long
    WHERE period = ?
      AND metric = ?
      AND comparison = ''
      AND region_entity = ?
      AND psi_model_26 <> 'Total'
    GROUP BY psi_model_26
)
SELECT
    compare.psi_model_26,
    COALESCE(base.base_value, 0) AS base_value,
    compare.compare_value,
    compare.compare_value - COALESCE(base.base_value, 0) AS delta
FROM compare
LEFT JOIN base ON base.psi_model_26 = compare.psi_model_26
WHERE {delta_filter}
ORDER BY delta DESC
LIMIT ?
""".strip()
        params: list[Any] = [base_period, metric, region_entity, compare_period, metric, region_entity, limit]
        explanation = (
            f"{region_entity} 지역에서 {base_period}와 {compare_period}의 {metric}를 모델별로 비교하고, "
            f"증가분(delta)이 큰 순서로 {limit}개를 조회합니다."
        )
        intent = {
            "kind": "period_delta_by_model",
            "region_entity": region_entity,
            "base_period": base_period,
            "compare_period": compare_period,
            "metric": metric,
            "limit": limit,
            "delta_filter": delta_filter,
        }
        return QueryPlan(
            kind="period_delta_by_model",
            sql=sql,
            params=params,
            explanation=explanation,
            intent=intent,
            result_shape="model_delta",
            region_entity=region_entity,
            base_period=base_period,
            compare_period=compare_period,
            metric=metric,
        )

    def _plan_ranked_metric(self, question: str) -> QueryPlan:
        parsed: QueryIntent = parse_query(question)
        where = [
            "period = ?",
            "metric = ?",
            "comparison = ''",
            "psi_model_26 = 'Total'",
            "region_entity <> 'Total'",
        ]
        params: list[Any] = [parsed.period, parsed.metric]
        if parsed.threshold is not None:
            where.append("value >= ?")
            params.append(parsed.threshold)
        order_sql = "ASC" if parsed.order == "asc" else "DESC"
        params.append(parsed.limit)
        sql = f"""
SELECT region_entity, value
FROM psi_long
WHERE {' AND '.join(where)}
ORDER BY value {order_sql}
LIMIT ?
""".strip()
        intent = asdict(parsed)
        intent["kind"] = "ranked_metric"
        explanation = (
            f"{parsed.period} 기간의 {parsed.metric} 지표를 지역/법인 Total 기준으로 "
            f"{parsed.order} 정렬해 {parsed.limit}개 조회합니다."
        )
        return QueryPlan(
            kind="ranked_metric",
            sql=sql,
            params=params,
            explanation=explanation,
            intent=intent,
            result_shape="ranked_region",
            metric=parsed.metric,
        )

    def _parse_limit(self, question: str) -> int:
        match = LIMIT_RE.search(question)
        if not match:
            return 10
        return int(next(group for group in match.groups() if group))

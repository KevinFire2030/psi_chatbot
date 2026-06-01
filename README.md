# PSI Chatbot PoC

GSCM PSI data를 자연어로 조회하기 위한 PoC 프로젝트입니다.

현재 구현 범위:

1. `sample_psi/sample_psi.xlsx` 분석 및 문서화
2. Excel 리포트형 wide data → long-form DuckDB 데이터마트 변환
3. Rule-based 한국어 자연어 질의 CLI
4. FastAPI 기반 `/query`, `/schema`, `/health` API
5. FastAPI 루트(`/`)에서 제공되는 간단한 앱 UI
6. LLM-ready NL→SQL/Query planner와 SQL/해석 과정 포함 API 응답

## 빠른 시작

### 1. DuckDB 데이터마트 생성

```bash
uv run python3 scripts/preprocess_psi.py \
  --input sample_psi/sample_psi.xlsx \
  --output data/psi.duckdb
```

생성 결과 예시:

```text
Created data/psi.duckdb
sheet_name=4)법인·모델별 현황 (분기_월)
source_rows=3051
source_columns=937
metric_columns=854
long_rows=2217562
```

`data/psi.duckdb`는 약 146MB이며 GitHub에는 커밋하지 않습니다. 필요 시 위 명령으로 재생성합니다.

### 2. CLI로 자연어 질의

```bash
uv run python3 scripts/query_psi.py \
  '3분기 Short가 가장 큰 지역 Top 5 보여줘' \
  --db data/psi.duckdb
```

### 3. 앱 UI/API 서버 실행

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8765
```

브라우저에서 앱 UI를 연다.

```text
http://127.0.0.1:8765/
```

UI 기능:

- 자연어 질문 입력창
- 예시 질문 버튼
- 질문 해석 intent 표시
- 지역/법인별 결과 테이블 표시
- `/query` API 호출 기반 조회

Health check:

```bash
curl http://127.0.0.1:8765/health
```

응답에는 `intent`, 생성된 `sql`, bind `params`, 한국어 `explanation`, `rows`가 포함된다.

자연어 질의:

```bash
curl -X POST http://127.0.0.1:8765/query \
  -H 'Content-Type: application/json' \
  --data '{"question":"3분기 Short가 가장 큰 지역 Top 5 보여줘"}'
```

응답 예시:

```json
{
  "question": "3분기 Short가 가장 큰 지역 Top 5 보여줘",
  "intent": {
    "period": "3분기",
    "metric": "Short",
    "limit": 5,
    "threshold": null,
    "order": "desc"
  },
  "sql": "SELECT region_entity, value FROM psi_long ... LIMIT ?",
  "params": ["3분기", "Short", 5],
  "explanation": "3분기 기간의 Short 지표를 지역/법인 Total 기준으로 desc 정렬해 5개 조회합니다.",
  "rows": [
    {"region_entity": "Latin America", "value": 3668584.0},
    {"region_entity": "Middle East", "value": 2349454.0},
    {"region_entity": "Europe", "value": 2280929.0},
    {"region_entity": "Africa", "value": 1378379.0},
    {"region_entity": "SELA", "value": 1271879.0}
  ]
}
```

Schema summary:

```bash
curl http://127.0.0.1:8765/schema
```

### 4. 비교형 Query planner 예시

현재 planner는 LLM으로 교체 가능한 구조의 deterministic planner입니다. 단순 ranking 질문 외에 기간 비교형 질문을 SQL plan으로 변환합니다.

```bash
curl -X POST http://127.0.0.1:8765/query \
  -H 'Content-Type: application/json' \
  --data '{"question":"Europe에서 2분기 대비 3분기 Short가 늘어난 모델 보여줘"}'
```

응답에는 모델별 `base_value`, `compare_value`, `delta`와 함께 생성 SQL/해석 과정이 포함됩니다.

예시 결과:

```json
{
  "intent": {
    "kind": "period_delta_by_model",
    "region_entity": "Europe",
    "base_period": "2분기",
    "compare_period": "3분기",
    "metric": "Short"
  },
  "explanation": "Europe 지역에서 2분기와 3분기의 Short를 모델별로 비교하고, 증가분(delta)이 큰 순서로 10개를 조회합니다.",
  "rows": [
    {
      "psi_model_26": "Smart",
      "value": 2280929.0,
      "delta": 1742570.0,
      "extra": {"base_value": 538359.0, "compare_value": 2280929.0}
    }
  ]
}
```

## 테스트

```bash
uv run --extra test python3 -m unittest discover -s tests -v
```

현재 테스트 범위:

- Excel column address 변환
- PSI metric header parsing
- 중복 metric key disambiguation
- 한국어 자연어 query intent parsing
- DuckDB query service
- FastAPI `/query` endpoint
- FastAPI 루트(`/`) 앱 UI HTML 서빙
- Query planner의 SQL/params/explanation 생성
- 기간 비교형 모델별 delta 조회

## 문서

- `docs/sample_psi_analysis.md`: 샘플 PSI Excel 분석 결과
- `docs/preprocessing_pipeline.md`: 전처리 파이프라인 및 DuckDB schema 설명

## 다음 단계 후보

1. 실제 LLM 기반 NL→SQL planner 연결
2. API 응답에 단위 변환 추가
3. UI에 차트/다운로드/질의 히스토리 추가
4. Streamlit 또는 React/Electron UI로 확장
5. 지역/법인/모델 hierarchy 정규화
6. 질의 결과 chart/table rendering 고도화

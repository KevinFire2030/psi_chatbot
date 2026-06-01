# PSI Chatbot PoC

GSCM PSI data를 자연어로 조회하기 위한 PoC 프로젝트입니다.

현재 구현 범위:

1. `sample_psi/sample_psi.xlsx` 분석 및 문서화
2. Excel 리포트형 wide data → long-form DuckDB 데이터마트 변환
3. Rule-based 한국어 자연어 질의 CLI
4. FastAPI 기반 `/query`, `/schema`, `/health` API
5. FastAPI 루트(`/`)에서 제공되는 간단한 앱 UI

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

## 문서

- `docs/sample_psi_analysis.md`: 샘플 PSI Excel 분석 결과
- `docs/preprocessing_pipeline.md`: 전처리 파이프라인 및 DuckDB schema 설명

## 다음 단계 후보

1. LLM 기반 NL→SQL 변환 추가
2. API 응답에 SQL/필터 설명 및 단위 변환 추가
3. UI에 차트/다운로드/질의 히스토리 추가
4. Streamlit 또는 React/Electron UI로 확장
5. 지역/법인/모델 hierarchy 정규화
6. 질의 결과 chart/table rendering 고도화

# GSCM PSI PoC1

초기 PoC1 구현 모음입니다. Excel PSI 샘플을 DuckDB long-form 데이터마트로 변환하고, deterministic rule-based parser/API로 자연어 질의를 실행합니다.

## 포함 파일

```text
PoC1/app/                    # 초기 FastAPI /query API와 Query planner
PoC1/scripts/                # Excel 전처리 및 DuckDB 직접 질의 CLI
PoC1/sample_psi/             # 샘플 PSI Excel
PoC1/docs/                   # 샘플 분석 및 전처리 문서
PoC1/tests/                  # PoC1 단위 테스트
```

## 데이터마트 생성

프로젝트 루트에서 실행합니다.

```bash
uv run python3 PoC1/scripts/preprocess_psi.py \
  --input PoC1/sample_psi/sample_psi.xlsx \
  --output PoC1/data/psi.duckdb
```

`PoC1/data/psi.duckdb`는 생성 산출물이므로 Git에 커밋하지 않습니다.

## CLI 질의

```bash
uv run python3 PoC1/scripts/query_psi.py \
  '3분기 Short가 가장 큰 지역 Top 5 보여줘' \
  --db PoC1/data/psi.duckdb
```

## PoC1 FastAPI 실행

```bash
uv run uvicorn PoC1.app.main:app --host 127.0.0.1 --port 8765
```

브라우저:

```text
http://127.0.0.1:8765/
```

API 예시:

```bash
curl -X POST http://127.0.0.1:8765/query \
  -H 'Content-Type: application/json' \
  --data '{"question":"3분기 Short가 가장 큰 지역 Top 5 보여줘"}'
```

## 테스트

```bash
uv run --extra test python3 -m unittest discover -s PoC1/tests -v
```

## 현재 PoC2와의 관계

PoC1은 초기 deterministic API/CLI 구현입니다. 현재 웹 데모와 Android APK는 루트의 `PoC2/`를 사용합니다.

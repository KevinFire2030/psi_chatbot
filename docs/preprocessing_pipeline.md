# PSI preprocessing pipeline

이 문서는 `sample_psi/sample_psi.xlsx`를 자연어 조회에 적합한 long-form DuckDB 데이터마트로 변환하는 방법을 설명한다.

## 산출물

로컬 생성 파일:

- `data/psi.duckdb`

주의: `data/psi.duckdb`는 현재 샘플 기준 약 146MB로 GitHub 단일 파일 제한 100MB를 초과할 수 있다. 따라서 Git에는 커밋하지 않고, 원본 Excel과 스크립트로 재생성한다.

## 실행 방법

프로젝트 루트에서 실행한다.

```bash
uv run --with duckdb python3 scripts/preprocess_psi.py \
  --input sample_psi/sample_psi.xlsx \
  --output data/psi.duckdb
```

실행 결과 예시:

```text
Created data/psi.duckdb
sheet_name=4)법인·모델별 현황 (분기_월)
source_rows=3051
source_columns=937
metric_columns=854
long_rows=2217562
```

## DuckDB 테이블

### `psi_long`

자연어 질의용 long-form fact table이다.

주요 컬럼:

- `excel_row_number`: 원본 Excel 행 번호
- `key`: 원본 Key
- `region_entity`: 지역/법인
- `psi_model_26`: `PSI모델('26)`
- `psi_model_25`: `PSI모델('25)`
- `sales_model_26`: `모델_('26매출)`
- `sales_model_25`: `모델_('25매출)`
- `business_unit`: 사업부/지역 한글명
- `smart_category`: Smart/ECO 구분
- `product_group`: 플래그십/A시리즈/Tablet/PC/Wearable/액세서리 등
- `model_code`: 모델 코드
- `source_column`: 원본 Excel 컬럼 주소
- `raw_header`: 원본 1행 header
- `period`: 1분기, 1월, 2분기, 상반기, 3분기 등
- `metric`: 매출, Demand, 물량, GI, Short, Sell-Out, WOS 등
- `comparison`: 전주比, 전년比, 적정比 등. 실제값은 빈 문자열
- `sub_header`: 12행 기준 세부 header
- `metric_key`: 중복 컬럼명 disambiguation용 key
- `value`: numeric value
- `raw_value`: 원본 cell value 문자열

### `psi_column_metadata`

원본 wide column의 메타데이터 테이블이다.

- 중복 header를 `source_column`과 `sub_header`로 구분한다.
- 예: `1분기Demand`는 여러 컬럼이므로 `AA`, `AB` 같은 source column을 함께 보존한다.

### `psi_load_info`

로드 정보 테이블이다.

- source file
- sheet name
- source rows
- source columns
- data start row

## 검증 쿼리

```bash
uv run --with duckdb python3 - <<'PY'
import duckdb
con = duckdb.connect('data/psi.duckdb', read_only=True)
print(con.execute('select count(*) from psi_long').fetchall())
print(con.execute('select count(*) from psi_column_metadata').fetchall())
print(con.execute('select * from psi_load_info').fetchall())
PY
```

기대 결과:

```text
[(2217562,)]
[(854,)]
[('sample_psi/sample_psi.xlsx', '4)법인·모델별 현황 (분기_월)', 3051, 937, 15)]
```

## 자연어 PoC CLI

초기 PoC용으로 rule-based 자연어 질의 CLI를 추가했다.

```bash
uv run --with duckdb python3 scripts/query_psi.py \
  '3분기 Short가 가장 큰 지역 Top 5 보여줘' \
  --db data/psi.duckdb
```

실행 결과 예시:

```text
질문: 3분기 Short가 가장 큰 지역 Top 5 보여줘
해석: period=3분기, metric=Short, threshold=None, limit=5
1. Latin America: 3.66858e+06
2. Middle East: 2.34945e+06
3. Europe: 2.28093e+06
4. Africa: 1.37838e+06
5. SELA: 1.27188e+06
```

다른 예시:

```bash
uv run --with duckdb python3 scripts/query_psi.py \
  '9월 WOS가 13 이상인 법인을 알려줘' \
  --db data/psi.duckdb
```

결과 예시:

```text
1. SEM: 17.6
2. SRI LANKA: 15.3
3. Japan: 15.1
4. SEAU: 15
5. SEAS: 14.4
6. SERC: 13.8
7. SELA: 13.7
8. SECH: 13
9. BANGLADESH: 13
```

## 테스트

```bash
python3 -m unittest discover -s tests -v
```

현재 테스트 범위:

- Excel column address 변환
- PSI metric header parsing
- 중복 metric key disambiguation
- 간단한 한국어 자연어 질의 intent parsing

## 다음 확장 방향

1. `scripts/query_psi.py`의 rule-based parser를 LLM 기반 NL→SQL로 교체 또는 보강
2. FastAPI endpoint 추가
   - `/query`: 자연어 질문 → SQL → 결과 JSON
   - `/schema`: metric dictionary/schema metadata 반환
3. UI 추가
   - Streamlit 또는 Electron/React 기반 챗봇 화면
4. 단위/스케일링 룰 확정
   - 매출 raw number → 백만불 표시
   - 수량 raw number → 천대 표시
5. 모델/지역 계층 정리
   - 지역 group vs 법인 구분
   - product group/model code hierarchy 정규화

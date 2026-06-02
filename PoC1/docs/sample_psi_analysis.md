# sample_psi.xlsx 분석 결과

분석 대상 파일:

- Windows 경로: `E:\ax\PRJs\psi_chatbot\PoC1\sample_psi\sample_psi.xlsx`
- WSL 경로: `/mnt/e/ax/PRJs/psi_chatbot/PoC1/sample_psi/sample_psi.xlsx`
- 파일 크기: 약 33.9MB

분석 일자: 2026-06-01

---

## 1. 파일 개요

샘플 PSI 데이터는 GSCM PSI 리포트형 Excel 파일이다.

- 시트 목록
  - `4)법인·모델별 현황 (분기_월)`: 실제 데이터 존재
  - `Sheet1`: 비어 있음
- 메인 시트 범위: `A1:AJA3051`
- 전체 행: 3,051행
- 실제 데이터 행: 3,036행
- 전체 컬럼: 937개

이 파일은 일반적인 tidy table이 아니라, 사람이 보는 PSI 리포트에 가까운 **wide cross-tab** 구조이다.

---

## 2. 데이터 구조 요약

앞쪽 컬럼은 차원 정보이며, 뒤쪽 수백 개 컬럼은 기간별 PSI 지표가 반복되는 구조다.

### 주요 dimension 컬럼

- A: `Key`
- B: `지역/법인`
- C: `PSI모델('26)`
- D: `PSI모델('25)`
- E: `모델_('26매출)`
- F: `모델_('25매출)`
- G: `시장성장률`
- H: 빈 컬럼
- I: 사업부 / 지역명 한글 표시
- J: Smart / ECO 구분
- K: 제품군 구분
- L: 모델 코드

### Dimension cardinality

- 지역/법인: 66개
- PSI모델('26): 45개
- PSI모델('25): 44개
- 모델 코드: 37개
- Smart 구분:
  - `Smart`
  - `ECO`
- 제품군 구분:
  - `플래그십`
  - `A 시리즈`
  - `Tablet`
  - `PC`
  - `Wearable`
  - `액세서리`

### 주요 지역/법인 예시

- Total
- North America
- SEA
- SECA
- Europe
- SEG
- SEUK
- SEF
- SEI
- SEIB
- Korea
- Latin America
- Middle East
- S.E Asia
- S.W Asia
- Japan
- Africa

---

## 3. 기간 구조

확인된 기간별 컬럼 수는 다음과 같다.

- 1분기: 60개
- 1월: 58개
- 2월: 58개
- 3월: 58개
- 2분기: 66개
- 4월: 66개
- 5월: 66개
- 6월: 66개
- 상반기: 66개
- 3분기: 66개
- 7월: 66개
- 8월: 66개
- 9월: 66개

현재 샘플은 2026년 1월~9월 및 1Q/2Q/3Q/상반기 중심의 PSI 데이터로 보인다.

상단 리포트 기준 정보:

- 전주 Plan: `202622`
- 현 Plan: `202623_P`
- 화면 제목 기준: `W23_Pre`
- 기준일로 보이는 값: `'26.06.01`

---

## 4. 주요 지표군

기간별로 다음 PSI 지표들이 반복된다.

- 매출
- Demand
- 물량 / RTF
- Demand(GI)
- GI
- Short
- Short-Ch_Constraint
- Sell-Out
- Ch.Inventory(EDI+FOTA)
- WOS(EDI+FOTA)
- T.WOS
- 전주比
- 전년比
- 경영比
- 확판比
- W12比
- T06比

자연어 질의에서 사용할 수 있는 기본 용어 매핑은 다음과 같다.

- `숏` → `Short`
- `채널숏` → `Short-Ch_Constraint`
- `재고`, `유통재고` → `Ch.Inventory(EDI+FOTA)`
- `WOS` → `WOS(EDI+FOTA)` 기본
- `셀아웃` → `Sell-Out`
- `물량` → `물량` 또는 `RTF/FP`
- `수요` → `Demand`
- `GI` → `GI`
- `전주 대비` → `전주比`
- `전년 대비` → `전년比`

---

## 5. Total row 기준 주요 값

첫 번째 실제 데이터 row는 `TotalTotal`로, 전체 Total row로 보인다.

### 1분기

- 1분기 매출: `25,631,577,000`
- 1분기 물량: `59,147,977`
- 1분기 Demand: `59,147,977`
- 1분기 Demand(GI): `58,827,095`
- 1분기 GI: `58,827,095`
- 1분기 Short: `0`
- 1분기 Sell-Out: `54,536,085`
- 1분기 Ch.Inventory: `51,625,473`
- 1분기 WOS: `10.76`

### 2분기

- 2분기 매출: `22,285,346,000`
- 2분기 물량: `63,850,469`
- 2분기 Demand: `67,886,237`
- 2분기 Demand(GI): `68,911,187`
- 2분기 GI: `65,062,198`
- 2분기 Short: `3,848,989`
- 2분기 Sell-Out: `56,807,757`
- 2분기 Ch.Inventory: `59,712,325`
- 2분기 WOS: `10.92`

### 상반기

- 상반기 매출: `47,916,923,000`
- 상반기 물량: `122,998,446`
- 상반기 Demand: `127,034,214`
- 상반기 Sell-Out: `111,343,842`

### 3분기

- 3분기 매출: `23,349,280,000`
- 3분기 물량: `56,739,513`
- 3분기 Demand: `69,585,902`
- 3분기 Demand(GI): `69,896,981`
- 3분기 GI: `56,992,999`
- 3분기 Short: `12,903,982`
- 3분기 Sell-Out: `65,245,221`
- 3분기 Ch.Inventory: `53,910,039`
- 3분기 WOS: `9.59`

주의: 엑셀 상단 주석에는 매출 단위가 `(백만불)`, 수량 단위가 `(천대)`로 표시되어 있으나, 실제 저장값은 raw number로 매우 크다. PoC에서는 표시 단위/스케일링 룰을 별도로 확정해야 한다.

---

## 6. 지역별 주요 인사이트 예시

### 1분기 매출 상위 지역/법인

Total 집계 기준:

1. Europe: `5,840,301,000`
2. North America: `5,149,889,000`
3. SEA: `4,341,469,000`
4. Korea: `2,909,822,000`
5. Latin America: `2,902,770,000`
6. S.E Asia: `2,359,199,000`
7. Middle East: `2,312,530,000`
8. S.W Asia: `1,623,966,000`
9. SIEL: `1,402,512,000`
10. SEDA: `968,289,000`

### 3분기 Short 상위 지역/법인

Total 집계 기준:

1. Latin America: `3,668,584`
2. Middle East: `2,349,454`
3. Europe: `2,280,929`
4. Africa: `1,378,379`
5. SELA: `1,271,879`
6. SEDA: `1,260,084`
7. S.E Asia: `1,239,453`
8. SEWA: `816,797`
9. SEMAG: `763,156`
10. S.W Asia: `713,496`

### 9월 WOS 상위 지역/법인

Total 집계 기준:

1. SEM: `17.6`
2. SRI LANKA: `15.3`
3. Japan: `15.1`
4. SEAU: `15.0`
5. SEAS: `14.4`
6. SERC: `13.8`
7. SELA: `13.7`
8. SECH: `13.0`
9. BANGLADESH: `13.0`
10. SEASA: `12.5`

---

## 7. 데이터 품질 및 PoC 구현 시 주의점

### 7.1 Header가 다층 구조임

헤더가 1행 하나로 끝나는 구조가 아니다.

- 1행: 완성형 컬럼명처럼 보이는 값 존재
- 3~7행: Plan, 시기, 구분, 시장, 주차 수 등 메타정보
- 10~12행: 리포트 제목, 기준일, 단위, 세부 항목
- 13~14행: dimension header와 세부 ratio header

따라서 PoC에서 단순히 `read_excel(header=0)`만 사용하면 의미 손실이 크다.

### 7.2 중복 컬럼명 존재

예시:

- `1분기Demand`가 2개
- `1월Demand`가 2개
- `2월Demand`가 2개
- `전년비`가 26개
- `WOS(EDI+FOTA)적정比` 반복

해결 방향:

- Excel column address를 보존한다.
  - 예: `AA`, `AB`, `AS`
- 또는 다층 header를 조합해 고유 컬럼명을 만든다.
  - 예: `period=1분기, metric=Demand, scenario=FP`
  - 예: `period=1분기, metric=Demand, scenario=전주`
  - 예: `period=1분기, metric=전년비, basis=시장`

### 7.3 Wide format이라 자연어 질의에 불리함

현재 구조:

```text
지역/법인 | 모델 | 1월매출 | 1월물량 | 1월GI | ... | 9월WOS
```

PoC에는 아래처럼 long format으로 바꾸는 것이 좋다.

```text
region
subsidiary
psi_model_26
psi_model_25
product_group
model_code
period
metric
scenario
value
unit
source_column
```

예:

```text
Europe | Total | Total | Total | 사업부 | NULL | 1분기 | 매출 | FP | 5840301000 | raw_sales | N
Europe | Total | Total | Total | 사업부 | NULL | 3분기 | Short | FP | 2280929 | qty | ZM
SEM    | Total | Total | Total | 사업부 | NULL | 9월 | WOS | EDI+FOTA | 17.6 | weeks | AIG
```

---

## 8. 자연어 조회 PoC 설계 방향

이 샘플 기준으로 PoC의 핵심은 Excel을 직접 LLM에 넣는 것이 아니라, 먼저 분석 가능한 표준 데이터마트로 변환하는 것이다.

추천 구조:

1. Excel parser
   - 원본 `sample_psi.xlsx` 읽기
   - 병합 셀/다층 헤더/중복 컬럼 처리
   - source column 주소 보존

2. PSI normalizer
   - wide → long 변환
   - 기간, 지표, scenario 분리
   - 단위/스케일링 적용

3. Query engine
   - DuckDB 또는 SQLite 사용 추천
   - 자연어 → SQL 변환
   - 결과를 표/차트/요약으로 반환

4. NL schema dictionary
   - 업무 용어와 컬럼/metric 매핑 관리
   - 예: 숏, 채널숏, 재고, WOS, 셀아웃, 물량, 수요, GI, 전주 대비, 전년 대비

---

## 9. 바로 지원 가능한 자연어 질문 예시

- “1분기 매출 상위 지역 Top 10 보여줘”
- “3분기 Short가 가장 큰 지역은 어디야?”
- “9월 WOS가 13 이상인 법인을 알려줘”
- “Europe의 1분기 매출, 물량, Sell-Out, 재고, WOS를 요약해줘”
- “Latin America에서 3분기 Short가 큰 모델을 찾아줘”
- “상반기 Sell-Out이 가장 큰 제품군은?”
- “2분기 대비 3분기 Short 증가가 큰 지역은?”
- “9월 재고는 높은데 Sell-Out이 낮은 법인을 찾아줘”
- “플래그십 모델의 1분기 매출과 3분기 Short를 비교해줘”
- “Smart와 ECO의 상반기 물량 차이를 보여줘”

---

## 10. 결론

이 샘플 PSI 데이터는 자연어 조회 PoC에 충분히 적합하다.

다만 원본은 사람이 보는 리포트형 Excel이므로, 자연어 조회 PoC의 첫 단계는 다음 전처리여야 한다.

- 다층 header 해석
- 중복 컬럼명 정리
- wide → long 변환
- metric dictionary 구축
- DuckDB/SQLite 적재

권장 다음 작업:

`sample_psi.xlsx`를 읽어서 `psi_long.parquet` 또는 `psi.duckdb`로 변환하는 전처리 파이프라인을 먼저 만들고, 그 위에 자연어 질의 API/챗봇 UI를 붙인다.

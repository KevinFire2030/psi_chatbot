# Codex Prompt — Rebuild GSCM PSI PoC2 for Internal Deployment

이 문서는 사내 Codex 앱 또는 Codex CLI에 그대로 붙여넣어 PoC2를 설계부터 구현까지 재현하도록 만든 **단일 입력 프롬프트**입니다.

사용법:

1. 새 Git repository 또는 기존 PoC repository를 준비한다.
2. 아래 `BEGIN CODEX PROMPT`부터 `END CODEX PROMPT`까지 전체를 복사한다.
3. 사내 Codex 앱에 그대로 입력한다.
4. Codex가 구현을 마치면 `pytest`, backend health check, web UI, Android APK build까지 검증한다.

---

## BEGIN CODEX PROMPT

You are Codex acting as a senior full-stack engineer. Build a production-shaped PoC named **GSCM PSI PoC2** from design through implementation.

The user will paste this prompt into an internal Codex app. Therefore, do not rely on hidden prior context. Infer everything from this prompt and from the repository files you can inspect.

## 0. Goal

Build a natural-language PSI data query PoC for internal GSCM users.

The system has three major surfaces:

1. **Frontend web app**: browser chat UI + Excel upload UI.
2. **Android WebView APK**: native Android wrapper that opens the hosted web frontend.
3. **Backend**: FastAPI service that stores raw Excel uploads, runs a 1-minute ingestion cron job, preprocesses new Excel files into DuckDB, and sends natural-language questions to **Codex CLI** for data analysis.

The target end-to-end flow:

```text
User uploads raw PSI Excel file in web UI
  -> FastAPI saves file under a configured raw upload folder
  -> every 1 minute, ingestion cron checks for new files
  -> if a new file is found, preprocess it into a DuckDB data mart
  -> user asks PSI question in web UI or Android WebView
  -> FastAPI creates a query job
  -> FastAPI calls Codex CLI with a constrained analysis prompt
  -> Codex CLI reads the DuckDB data mart, runs real queries, and returns Korean answer
  -> FastAPI returns final answer to web UI
```

## 1. Mandatory architecture

Use this separation exactly.

```text
repo-root/
  backend/
    app/
      main.py
      config.py
      models.py
      storage.py
      ingest.py
      preprocess.py
      codex_runner.py
      jobs.py
    tests/
    pyproject-compatible code

  frontend/
    web/
      package.json
      src/ or plain Vite app files

  android/
    psi-webview/
      Gradle Android project

  prompts/
    codex_query_system_prompt.md

  data/
    raw_uploads/        # ignored by git
    processed/          # ignored by git; contains DuckDB files
    state/              # ignored by git; contains SQLite job/index DB

  docs/
    architecture.md
    operations.md
```

If the repository already has a different layout, preserve useful existing code but refactor toward this structure.

## 2. Technology choices

Backend:

- Python 3.11+
- FastAPI
- Uvicorn
- DuckDB
- pandas or openpyxl as needed for Excel parsing
- APScheduler or an equivalent in-process scheduler for a 1-minute cron-like ingestion job
- SQLite for upload/job/index state
- `subprocess` for Codex CLI execution
- pytest + httpx/TestClient for tests

Frontend web:

- Prefer Vite + React + TypeScript if there is no existing frontend.
- If repository constraints make plain HTML/JS simpler, plain Vite or static JS is acceptable.
- UI must be app-like and demo-friendly.

Android:

- Native Android WebView project in Java or Kotlin.
- Gradle wrapper included.
- App opens configured web URL.
- JavaScript and DOM storage enabled.
- Back button navigates WebView history before exiting.

## 3. Critical business/domain requirements

The PSI data source is a raw Excel workbook uploaded by business users.

The app must support:

- Uploading `.xlsx` files from the web UI.
- Saving raw files to `data/raw_uploads/` or a configurable folder.
- Detecting new raw files every 1 minute.
- Avoiding duplicate preprocessing by using file fingerprinting:
  - absolute path
  - file size
  - mtime
  - SHA-256 hash
- Preprocessing only new or changed files.
- Creating/refreshing a DuckDB database under `data/processed/`.
- Exposing ingestion status in the UI.
- Natural-language question answering in Korean.

Answer format conventions:

- Start PSI answers with exactly: `W23_Pre plan 기준`
- Amounts should be shown in million dollars: `백만불`
- Quantities should be shown in thousand units: `천대`
- Answers must be concise but include enough basis/filter information to be trusted.
- Do not fabricate results. If the data mart is missing or the query cannot be answered, say why.

## 4. Backend API requirements

Implement FastAPI endpoints.

### Health

`GET /health`

Return:

```json
{
  "status": "ok",
  "version": "0.1.0",
  "raw_upload_dir": "...",
  "processed_dir": "...",
  "active_duckdb": "... or null",
  "codex_available": true,
  "scheduler_running": true
}
```

### Upload raw Excel

`POST /api/uploads`

- Multipart upload field: `file`
- Accept only `.xlsx`
- Reject suspicious names/path traversal
- Save under raw upload folder with timestamp-safe filename
- Record upload in SQLite
- Return upload metadata

Example response:

```json
{
  "upload_id": "...",
  "filename": "...xlsx",
  "stored_path": "data/raw_uploads/20260602_120000_original.xlsx",
  "size_bytes": 12345,
  "status": "saved"
}
```

### List uploads / ingestion state

`GET /api/uploads`

Return recent uploads and ingestion status.

`GET /api/ingestion/status`

Return:

```json
{
  "last_scan_at": "...",
  "last_success_at": "...",
  "active_duckdb": "data/processed/psi_latest.duckdb",
  "files_seen": 3,
  "files_processed": 2,
  "last_error": null
}
```

### Manual ingestion trigger

`POST /api/ingestion/run`

- Runs the same ingestion scan immediately.
- Useful for tests and demos.
- Return scan result.

### Chat/query

`POST /api/chat`

Request:

```json
{
  "message": "3분기 FP 금액기준 전년비 감소가 가장 큰 법인 탑5 알려줘",
  "timeout_seconds": 300
}
```

Behavior:

1. Validate there is an active DuckDB data mart.
2. Create query job row in SQLite.
3. Invoke Codex CLI via `codex_runner.py`.
4. Pass Codex a constrained prompt containing:
   - user question
   - active DuckDB path
   - schema summary or instructions to inspect schema
   - output format rules
   - safety rule: use real DuckDB queries only; never invent values
5. Capture stdout/stderr, timeout, exit code.
6. Return final answer and metadata.

Response:

```json
{
  "request_id": "...",
  "answer": "W23_Pre plan 기준 ...",
  "elapsed_seconds": 12.3,
  "answer_source": "codex_cli",
  "codex_exit_code": 0
}
```

If Codex fails, return a clear 502/504 error with safe diagnostic text. Do not expose secrets.

## 5. Backend ingestion/preprocessing requirements

Implement `backend/app/ingest.py` and `backend/app/preprocess.py`.

The ingestion cron:

- Starts with the FastAPI app lifespan.
- Runs every 60 seconds.
- Can also be triggered manually by API and tests.
- Scans `RAW_UPLOAD_DIR` for `.xlsx` files.
- Calculates SHA-256.
- Checks SQLite index to decide whether a file is new/changed.
- For each new file, calls the preprocessing pipeline.
- Marks success/failure per file.
- Updates `data/processed/psi_latest.duckdb` atomically:
  - write temp DB first
  - validate expected tables exist
  - rename/swap to latest only after success

Preprocessing:

- Prefer reusing existing logic if the repository already has a PoC1 preprocessing script.
- Otherwise implement a robust baseline that reads workbook sheets and normalizes usable data into DuckDB.
- At minimum create:
  - `psi_long` table for normalized queryable facts
  - `ingestion_metadata` table
- Include source columns such as:
  - source_file
  - sheet_name
  - row_index
  - business_unit if available
  - region_entity if available
  - model_code / psi_model if available
  - period
  - metric
  - sub_header if available
  - value
- Make parser tolerant of report-style Excel headers. If exact domain parsing is uncertain, implement clear extension points and tests around discovered sample workbook.

## 6. Codex CLI runner requirements

Implement `backend/app/codex_runner.py`.

The backend calls Codex CLI like this conceptually:

```bash
codex exec --full-auto "<generated constrained prompt>"
```

But make command configurable:

- `CODEX_COMMAND`, default: `codex`
- `CODEX_ARGS`, default: `exec --full-auto`
- `CODEX_TIMEOUT_SECONDS`, default: 300
- `CODEX_WORKDIR`, default: repository root

Security and reliability rules:

- Use `subprocess.run([...], shell=False)`.
- Never concatenate user input into a shell string.
- Pass the prompt as one argument or via a temporary prompt file if needed.
- Capture stdout/stderr.
- Redact obvious secrets from logs.
- Store query job logs in SQLite, but truncate very long logs.
- Tests must mock subprocess, not require real Codex.

Create `prompts/codex_query_system_prompt.md` containing the reusable system prompt for Codex query execution. It must instruct Codex to:

- inspect DuckDB schema
- run real DuckDB SQL using Python or DuckDB CLI
- answer in Korean
- start with `W23_Pre plan 기준`
- use `백만불` and `천대`
- show filters/basis briefly
- say when data is unavailable
- not include internal chain-of-thought

## 7. Frontend web requirements

Implement a demo-friendly app.

Required screens/sections:

1. Header/hero:
   - `GSCM PSI Chatbot`
   - show current active data mart status
2. Upload panel:
   - drag-and-drop or file picker for `.xlsx`
   - upload progress/result
   - recent uploaded files table/list
   - manual `Run ingestion now` button
3. Ingestion status panel:
   - last scan time
   - last success time
   - active DuckDB path/name
   - last error if any
4. Chat panel:
   - question input
   - example question buttons
   - streaming is optional; waiting indicator is required
   - render answer with line breaks
   - show request id/source/elapsed metadata

Example questions:

- `3분기 Short가 가장 큰 지역 Top 5 보여줘`
- `9월 WOS가 13 이상인 법인을 알려줘`
- `3분기 FP 금액기준 전년비 감소가 가장 큰 법인 탑5 알려줘`
- `SEG 3분기 PSI 입력 현황 분석해서 입력이 덜됐거나 추가로 확인이 필요한 부분이 있는지 점검해줘`
- `2분기 SEROM S26F 셀아웃 WOS 알려줘`

Frontend should call backend APIs only; do not implement local deterministic answers in the browser.

## 8. Android WebView APK requirements

Implement under `android/psi-webview/`.

Requirements:

- Package id: `com.possibleconnect.gscmpsi`
- App label: `GSCM PSI Chatbot`
- Default URL configurable in Gradle or Java/Kotlin constant, default `https://psi.possible-connect.com/` or local demo URL as documented.
- Enable JavaScript, DOM storage, cookies.
- Use back button for WebView history.
- Include basic network error page/message.
- Provide debug APK build command:

```bash
cd android/psi-webview
./gradlew assembleDebug
```

- Copy or document APK output path:

```text
android/psi-webview/app/build/outputs/apk/debug/app-debug.apk
```

## 9. Configuration

Use environment variables with safe defaults.

Backend config variables:

```text
APP_ENV=dev
RAW_UPLOAD_DIR=data/raw_uploads
PROCESSED_DATA_DIR=data/processed
STATE_DB_PATH=data/state/poc2.sqlite3
ACTIVE_DUCKDB_PATH=data/processed/psi_latest.duckdb
INGESTION_CRON_SECONDS=60
CODEX_COMMAND=codex
CODEX_ARGS=exec --full-auto
CODEX_TIMEOUT_SECONDS=300
CODEX_WORKDIR=.
MAX_UPLOAD_MB=200
```

Add `.env.example` but never commit real `.env`.

Update `.gitignore` for:

```text
.env
.env.*
data/raw_uploads/
data/processed/
data/state/
*.duckdb
*.duckdb.wal
```

## 10. Testing requirements

Write tests before or alongside implementation.

Backend tests:

- health endpoint returns expected fields
- upload rejects non-xlsx
- upload saves xlsx safely
- ingestion detects new file by hash
- ingestion skips unchanged file
- preprocessing creates DuckDB and expected tables for a tiny synthetic workbook
- manual ingestion endpoint runs scanner
- chat endpoint calls mocked Codex runner and returns answer
- Codex runner uses `subprocess.run` with `shell=False`
- Codex runner timeout/failure maps to clear backend error

Frontend tests if test framework is available:

- upload call flow
- chat call flow
- status rendering

Android:

- At minimum ensure Gradle debug build succeeds.

Verification commands must be documented and run:

```bash
pytest -q
uvicorn backend.app.main:app --host 127.0.0.1 --port 8766
curl http://127.0.0.1:8766/health
```

For frontend, run whatever applies:

```bash
npm install
npm run build
```

For Android:

```bash
cd android/psi-webview
./gradlew assembleDebug
```

## 11. Documentation requirements

Create/update:

- `README.md`: quick start, architecture, upload/cron/query flow, run commands
- `docs/architecture.md`: frontend/backend/android/backend-Codex architecture
- `docs/operations.md`: how to run, how to set Codex CLI, how to troubleshoot ingestion, how to build APK
- `prompts/codex_query_system_prompt.md`: prompt used by backend when calling Codex CLI

README must include a copy-paste quick start:

```bash
# backend
uv sync || pip install -e .
uvicorn backend.app.main:app --host 127.0.0.1 --port 8766

# frontend
cd frontend/web
npm install
npm run dev

# test
pytest -q
```

Adjust commands to the actual project tooling you implement.

## 12. Implementation strategy

Follow this order and commit frequently if git is available:

1. Inspect repository and identify reusable PoC1/PoC2 code.
2. Create backend package and config/state models.
3. Implement upload storage and SQLite state.
4. Implement ingestion scanner and preprocessing pipeline.
5. Implement mocked/testable Codex runner.
6. Implement chat endpoint.
7. Implement web frontend.
8. Implement Android WebView wrapper.
9. Add docs and examples.
10. Run tests/builds and fix failures.

Do not stop after stubs. Produce a working artifact backed by real tests/build output.

## 13. Acceptance criteria

Implementation is complete only when all are true:

- User can upload `.xlsx` in web UI.
- Backend stores the file in raw upload folder.
- 1-minute cron-like scheduler detects new file.
- Manual ingestion endpoint also works.
- New Excel file is converted into DuckDB.
- `/health` reports active data mart and scheduler status.
- User can ask a question in web UI.
- Backend invokes Codex CLI through the configured runner.
- Codex prompt forces real DuckDB inspection/query and Korean answer formatting.
- Web UI displays final answer and metadata.
- Android debug APK builds and opens the web URL.
- Tests pass.
- README and operations docs explain how to run everything from scratch.

## 14. Important constraints

- Do not hardcode secrets.
- Do not commit uploaded Excel files, DuckDB files, SQLite state DB, or `.env`.
- Do not invent PSI numbers in tests or docs; use tiny synthetic fixtures for tests and label examples clearly.
- Do not implement browser-side deterministic fallback. Natural-language answering must go through backend -> Codex CLI.
- If Codex CLI is unavailable during tests, mock it and document how to configure it in real deployment.
- Prefer simple, maintainable code over over-engineered abstractions.

Now implement the project end-to-end. Inspect existing files first, then make changes. When finished, report:

- files created/modified
- how to run backend
- how to run frontend
- how to build Android APK
- test/build results
- known limitations

## END CODEX PROMPT

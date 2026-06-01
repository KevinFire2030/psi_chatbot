from __future__ import annotations


def render_homepage() -> str:
    """Return the single-page PSI chatbot UI HTML."""
    return """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>GSCM PSI Chatbot</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0b1020;
      --panel: rgba(18, 26, 48, 0.88);
      --panel-2: rgba(26, 38, 68, 0.78);
      --text: #edf3ff;
      --muted: #9fb1d1;
      --accent: #5eead4;
      --accent-2: #60a5fa;
      --danger: #fb7185;
      --border: rgba(148, 163, 184, 0.22);
      --shadow: 0 24px 70px rgba(0, 0, 0, 0.35);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(94, 234, 212, 0.18), transparent 30rem),
        radial-gradient(circle at bottom right, rgba(96, 165, 250, 0.22), transparent 30rem),
        var(--bg);
    }
    .shell { max-width: 1180px; margin: 0 auto; padding: 44px 22px; }
    .hero { display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 22px; align-items: stretch; }
    .card {
      border: 1px solid var(--border);
      border-radius: 28px;
      background: var(--panel);
      box-shadow: var(--shadow);
      backdrop-filter: blur(18px);
    }
    .intro { padding: 34px; }
    .badge {
      display: inline-flex; gap: 8px; align-items: center;
      padding: 8px 12px; border-radius: 999px;
      background: rgba(94, 234, 212, 0.12); color: var(--accent);
      font-size: 13px; font-weight: 700;
    }
    h1 { margin: 18px 0 12px; font-size: clamp(34px, 5vw, 58px); line-height: 1.02; letter-spacing: -0.055em; }
    .lead { margin: 0; color: var(--muted); font-size: 17px; line-height: 1.7; }
    .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 28px; }
    .stat { padding: 16px; border-radius: 18px; background: rgba(15, 23, 42, 0.7); border: 1px solid var(--border); }
    .stat strong { display: block; font-size: 20px; }
    .stat span { color: var(--muted); font-size: 12px; }
    .examples { padding: 26px; }
    .examples h2 { margin: 0 0 14px; font-size: 18px; }
    .chip {
      width: 100%; margin: 8px 0; padding: 12px 14px; text-align: left;
      border: 1px solid var(--border); border-radius: 16px;
      background: var(--panel-2); color: var(--text); cursor: pointer;
      transition: border-color .15s, transform .15s, background .15s;
    }
    .chip:hover { border-color: var(--accent); transform: translateY(-1px); background: rgba(45, 60, 96, 0.78); }
    .workspace { margin-top: 22px; padding: 24px; }
    .querybar { display: flex; gap: 12px; }
    input {
      flex: 1; min-width: 0; padding: 17px 18px; border-radius: 18px;
      border: 1px solid var(--border); outline: none;
      background: rgba(15, 23, 42, 0.82); color: var(--text); font-size: 16px;
    }
    input:focus { border-color: var(--accent); box-shadow: 0 0 0 4px rgba(94, 234, 212, 0.12); }
    button.primary {
      padding: 0 24px; border: 0; border-radius: 18px;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      color: #06111f; font-weight: 900; cursor: pointer;
    }
    button.primary:disabled { opacity: .55; cursor: wait; }
    .answer { margin-top: 22px; display: grid; grid-template-columns: 320px 1fr; gap: 18px; }
    .intent, .result { padding: 20px; border-radius: 22px; background: rgba(15, 23, 42, 0.62); border: 1px solid var(--border); min-height: 180px; }
    .intent h3, .result h3 { margin: 0 0 14px; font-size: 15px; color: var(--muted); }
    .kv { display: grid; grid-template-columns: 90px 1fr; gap: 8px; font-size: 14px; }
    .kv b { color: var(--muted); }
    table { width: 100%; border-collapse: collapse; overflow: hidden; }
    th, td { padding: 12px 10px; border-bottom: 1px solid rgba(148, 163, 184, .15); text-align: left; }
    th { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }
    td:last-child { text-align: right; font-variant-numeric: tabular-nums; }
    .empty { color: var(--muted); line-height: 1.7; }
    .error { color: var(--danger); white-space: pre-wrap; }
    footer { color: var(--muted); text-align: center; margin-top: 22px; font-size: 13px; }
    @media (max-width: 860px) {
      .hero, .answer { grid-template-columns: 1fr; }
      .querybar { flex-direction: column; }
      button.primary { padding: 16px 20px; }
      .stats { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="card intro">
        <div class="badge">● PSI Natural Language PoC</div>
        <h1>GSCM PSI Chatbot</h1>
        <p class="lead">GSCM PSI Excel 데이터를 DuckDB long-form 데이터마트로 변환한 뒤, 한국어 자연어 질문으로 지역/법인별 매출, Short, WOS, 재고, Sell-Out을 조회하는 간단한 앱 UI입니다.</p>
        <div class="stats">
          <div class="stat"><strong>2.2M+</strong><span>long-form rows</span></div>
          <div class="stat"><strong>854</strong><span>metric columns</span></div>
          <div class="stat"><strong>937</strong><span>source columns</span></div>
        </div>
      </div>
      <aside class="card examples">
        <h2>예시 질문</h2>
        <button class="chip" data-question="3분기 Short가 가장 큰 지역 Top 5 보여줘">3분기 Short가 가장 큰 지역 Top 5 보여줘</button>
        <button class="chip" data-question="9월 WOS가 13 이상인 법인을 알려줘">9월 WOS가 13 이상인 법인을 알려줘</button>
        <button class="chip" data-question="1분기 매출 상위 10개 지역 보여줘">1분기 매출 상위 10개 지역 보여줘</button>
        <button class="chip" data-question="2분기 Sell-Out 상위 5개 지역">2분기 Sell-Out 상위 5개 지역</button>
      </aside>
    </section>

    <section class="card workspace">
      <form id="queryForm" class="querybar">
        <input id="questionInput" name="question" autocomplete="off" placeholder="예: 3분기 Short가 가장 큰 지역 Top 5 보여줘" />
        <button id="submitButton" class="primary" type="submit">조회</button>
      </form>
      <div class="answer">
        <div class="intent">
          <h3>질문 해석</h3>
          <div id="intentPanel" class="empty">질문을 입력하면 period, metric, threshold, limit 해석 결과가 표시됩니다.</div>
        </div>
        <div class="result">
          <h3>조회 결과</h3>
          <div id="resultPanel" class="empty">결과가 여기에 표시됩니다.</div>
        </div>
      </div>
    </section>
    <footer>FastAPI / DuckDB 기반 PSI Chatbot PoC</footer>
  </main>

  <script>
    const form = document.getElementById('queryForm');
    const input = document.getElementById('questionInput');
    const submitButton = document.getElementById('submitButton');
    const intentPanel = document.getElementById('intentPanel');
    const resultPanel = document.getElementById('resultPanel');

    function formatValue(value) {
      return new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 2 }).format(value);
    }

    function renderIntent(intent) {
      intentPanel.className = 'kv';
      intentPanel.innerHTML = `
        <b>period</b><span>${intent.period}</span>
        <b>metric</b><span>${intent.metric}</span>
        <b>limit</b><span>${intent.limit}</span>
        <b>threshold</b><span>${intent.threshold ?? '-'}</span>
        <b>order</b><span>${intent.order}</span>
      `;
    }

    function renderRows(rows) {
      if (!rows.length) {
        resultPanel.className = 'empty';
        resultPanel.textContent = '조건에 맞는 결과가 없습니다.';
        return;
      }
      resultPanel.className = '';
      resultPanel.innerHTML = `
        <table>
          <thead><tr><th>Rank</th><th>지역/법인</th><th>Value</th></tr></thead>
          <tbody>
            ${rows.map((row, index) => `<tr><td>${index + 1}</td><td>${row.region_entity}</td><td>${formatValue(row.value)}</td></tr>`).join('')}
          </tbody>
        </table>
      `;
    }

    async function ask(question) {
      const trimmed = question.trim();
      if (!trimmed) return;
      submitButton.disabled = true;
      submitButton.textContent = '조회 중...';
      intentPanel.className = 'empty';
      intentPanel.textContent = '질문 해석 중...';
      resultPanel.className = 'empty';
      resultPanel.textContent = 'DuckDB 조회 중...';
      try {
        const response = await fetch('/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: trimmed })
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || '조회 실패');
        renderIntent(payload.intent);
        renderRows(payload.rows);
      } catch (error) {
        intentPanel.className = 'error';
        intentPanel.textContent = error.message;
        resultPanel.className = 'empty';
        resultPanel.textContent = '질문 예시를 참고해서 다시 시도하세요.';
      } finally {
        submitButton.disabled = false;
        submitButton.textContent = '조회';
      }
    }

    form.addEventListener('submit', (event) => {
      event.preventDefault();
      ask(input.value);
    });

    document.querySelectorAll('[data-question]').forEach((button) => {
      button.addEventListener('click', () => {
        input.value = button.dataset.question;
        ask(input.value);
      });
    });
  </script>
</body>
</html>
"""

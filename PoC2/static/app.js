const form = document.querySelector('#chatForm');
const input = document.querySelector('#messageInput');
const sendButton = document.querySelector('#sendButton');
const messages = document.querySelector('#messages');

function appendMessage(role, text, meta = '', isError = false) {
  const article = document.createElement('article');
  article.className = `message ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'user' ? 'U' : 'H';

  const bubble = document.createElement('div');
  bubble.className = `bubble${isError ? ' error' : ''}`;
  bubble.textContent = text;

  if (meta) {
    const metaDiv = document.createElement('div');
    metaDiv.className = 'meta';
    metaDiv.textContent = meta;
    bubble.appendChild(metaDiv);
  }

  article.appendChild(avatar);
  article.appendChild(bubble);
  messages.appendChild(article);
  messages.scrollTop = messages.scrollHeight;
  return article;
}

function setBusy(isBusy) {
  sendButton.disabled = isBusy;
  input.disabled = isBusy;
  sendButton.textContent = isBusy ? 'Hermes 처리 중…' : '전송';
}

async function sendMessage(text) {
  const message = text.trim();
  if (!message) return;

  appendMessage('user', message);
  const loading = appendMessage('bot', 'Hermes 웹훅으로 전달했습니다. Agent 응답을 기다리는 중입니다…', '', false);
  loading.querySelector('.bubble').classList.add('loading');
  setBusy(true);

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, timeout_seconds: 1800 }),
    });
    const data = await res.json();
    loading.remove();

    if (!res.ok) {
      appendMessage('bot', data.detail || '요청 처리 중 오류가 발생했습니다.', '', true);
      return;
    }

    appendMessage(
      'bot',
      data.answer,
      `source=${data.answer_source || 'hermes_webhook'} · request_id=${data.request_id} · session=${data.session_id || '-'} · ${data.elapsed_seconds}s`,
    );
  } catch (err) {
    loading.remove();
    appendMessage('bot', `브라우저 요청 실패: ${err}`, '', true);
  } finally {
    setBusy(false);
    input.focus();
  }
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const text = input.value;
  input.value = '';
  sendMessage(text);
});

document.querySelectorAll('[data-example]').forEach((button) => {
  button.addEventListener('click', () => {
    input.value = button.dataset.example;
    input.focus();
  });
});

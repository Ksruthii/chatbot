



(function(){
  const script = document.currentScript;
  if (!script) return;
  const botId = script.dataset.id;
  const baseUrl = new URL(script.src, window.location.href).origin;
  const state = { open: false, botName: 'Chatbot', businessName: '', loading: false };

  const style = document.createElement('style');
  style.textContent = `
    .eb-launcher{position:fixed;right:20px;bottom:20px;width:58px;height:58px;border-radius:999px;border:none;background:#01696f;color:#fff;box-shadow:0 14px 28px rgba(0,0,0,.18);cursor:pointer;z-index:2147483000}
    .eb-panel{position:fixed;right:20px;bottom:90px;width:min(360px,calc(100vw - 24px));height:520px;background:#fff;border-radius:18px;box-shadow:0 22px 60px rgba(0,0,0,.18);overflow:hidden;display:none;flex-direction:column;z-index:2147483000;border:1px solid rgba(0,0,0,.08);font-family:Inter,Arial,sans-serif}
    .eb-panel.open{display:flex}.eb-head{display:flex;justify-content:space-between;align-items:center;padding:14px 16px;background:#0f1720;color:#fff}.eb-head strong{display:block;font-size:15px}.eb-head span{font-size:12px;opacity:.7}
    .eb-messages{flex:1;overflow-y:auto;padding:14px;background:#f5f7f9;display:grid;align-content:start;gap:10px}.eb-msg{max-width:82%;padding:10px 12px;border-radius:14px;font-size:14px;line-height:1.45;background:#fff;color:#0f1720}.eb-msg.user{margin-left:auto;background:#01696f;color:#fff}
    .eb-form{display:grid;grid-template-columns:1fr auto;gap:10px;padding:14px;border-top:1px solid rgba(0,0,0,.08)}.eb-form input{min-width:0;padding:12px 14px;border:1px solid rgba(0,0,0,.12);border-radius:12px;font-size:14px}.eb-form button,.eb-close{border:none;background:#01696f;color:#fff;border-radius:12px;padding:12px 14px;cursor:pointer}.eb-close{background:transparent;padding:0;font-size:22px;line-height:1}
    @media (max-width:640px){.eb-panel{right:12px;left:12px;bottom:84px;width:auto;height:68vh}.eb-launcher{right:12px;bottom:12px}}
  `;
  document.head.appendChild(style);

  const launcher = document.createElement('button');
  launcher.className = 'eb-launcher';
  launcher.setAttribute('aria-label', 'Open chat');
  launcher.innerHTML = '??';

  const panel = document.createElement('section');
  panel.className = 'eb-panel';
  panel.innerHTML = `
    <div class="eb-head">
      <div><strong>Chat</strong><span>Ask us a question</span></div>
      <button class="eb-close" aria-label="Close chat">×</button>
    </div>
    <div class="eb-messages"></div>
    <form class="eb-form">
      <input type="text" placeholder="Type your question" aria-label="Type your question">
      <button type="submit">Send</button>
    </form>
  `;

  document.body.appendChild(launcher);
  document.body.appendChild(panel);

  const messages = panel.querySelector('.eb-messages');
  const form = panel.querySelector('.eb-form');
  const input = form.querySelector('input');
  const closeBtn = panel.querySelector('.eb-close');
  const headTitle = panel.querySelector('.eb-head strong');
  const headSubtitle = panel.querySelector('.eb-head span');

  function pushMessage(text, who){
    const item = document.createElement('div');
    item.className = `eb-msg ${who || ''}`.trim();
    item.textContent = text;
    messages.appendChild(item);
    messages.scrollTop = messages.scrollHeight;
  }

  async function loadBot(){
    try {
      const res = await fetch(`${baseUrl}/api/bot/${botId}`);
      const data = await res.json();
      state.botName = data.name || 'Chat';
      state.businessName = data.business_name || '';
      headTitle.textContent = state.botName;
      headSubtitle.textContent = state.businessName;
      pushMessage(`Hi, I'm ${state.botName}. How can I help today?`, 'bot');
    } catch (_e) {
      pushMessage('This chatbot is currently unavailable.', 'bot');
    }
  }

  async function sendMessage(message){
    pushMessage(message, 'user');
    try {
      const res = await fetch(`${baseUrl}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chatbot_id: botId, message })
      });
      const data = await res.json();
      pushMessage(data.reply || 'Sorry, something went wrong.', 'bot');
    } catch (_e) {
      pushMessage('Unable to reach support right now. Please try again.', 'bot');
    }
  }

  launcher.addEventListener('click', () => {
    state.open = !state.open;
    panel.classList.toggle('open', state.open);
  });
  closeBtn.addEventListener('click', () => { state.open = false; panel.classList.remove('open'); });
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const value = input.value.trim();
    if (!value) return;
    input.value = '';
    sendMessage(value);
  });

  loadBot();
})();

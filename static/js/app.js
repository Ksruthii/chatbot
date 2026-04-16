


const state = { bots: [], selectedBotId: null };

const els = {
  botsList: document.getElementById('bots-list'),
  botsEmpty: document.getElementById('bots-empty'),
  botCount: document.getElementById('bot-count'),
  totalChats: document.getElementById('total-chats'),
  previewTitle: document.getElementById('preview-title'),
  previewSubtitle: document.getElementById('preview-subtitle'),
  previewMessages: document.getElementById('preview-messages'),
  previewForm: document.getElementById('preview-form'),
  previewInput: document.getElementById('preview-input'),
  modal: document.getElementById('create-modal'),
  openModal: document.getElementById('open-create-modal'),
  closeModal: document.getElementById('close-create-modal'),
  createForm: document.getElementById('create-bot-form'),
  faqList: document.getElementById('faq-list'),
  addFaq: document.getElementById('add-faq')
};

function openModal(){ els.modal.classList.remove('hidden'); els.modal.setAttribute('aria-hidden','false'); }
function closeModal(){ els.modal.classList.add('hidden'); els.modal.setAttribute('aria-hidden','true'); }

function createFaqRow(question='', answer='') {
  const row = document.createElement('div');
  row.className = 'faq-item';
  row.innerHTML = `
    <label>Question<input type="text" name="faq_question" value="${question.replace(/"/g,'&quot;')}"></label>
    <label>Answer<input type="text" name="faq_answer" value="${answer.replace(/"/g,'&quot;')}"></label>
    <button type="button" class="remove-faq">Remove</button>
  `;
  row.querySelector('.remove-faq').addEventListener('click', () => row.remove());
  return row;
}

function addMessage(text, sender='bot') {
  const item = document.createElement('div');
  item.className = `message ${sender}`;
  item.textContent = text;
  els.previewMessages.appendChild(item);
  els.previewMessages.scrollTop = els.previewMessages.scrollHeight;
}

function setSelectedBot(id) {
  state.selectedBotId = id;
  const bot = state.bots.find(b => b.id === id);
  if (!bot) return;
  els.previewTitle.textContent = bot.name;
  els.previewSubtitle.textContent = bot.business_name;
  els.previewMessages.innerHTML = '';
  addMessage(`Hi, I'm ${bot.name}. Ask me anything about ${bot.business_name}.`);
}

function renderBots() {
  els.botCount.textContent = state.bots.length;
  els.totalChats.textContent = state.bots.reduce((sum, bot) => sum + (bot.chat_count || 0), 0);
  els.botsList.innerHTML = '';
  els.botsEmpty.classList.toggle('hidden', state.bots.length > 0);

  state.bots.forEach(bot => {
    const card = document.createElement('article');
    card.className = 'bot-card';
    card.innerHTML = `
      <h3>${bot.name}</h3>
      <div class="bot-meta">
        <span>${bot.business_name}</span>
        <span>${bot.faq_data.length} FAQs</span>
        <span>${bot.chat_count || 0} chats</span>
      </div>
      <div class="card-actions">
        <button class="btn btn-secondary" data-preview="${bot.id}">Preview</button>
        <button class="btn btn-ghost" data-copy="${bot.id}">Copy embed</button>
      </div>
      <pre class="embed-box">${bot.embed_code.replace('{{BASE_URL}}', window.APP_CONFIG.baseUrl)}</pre>
    `;
    card.querySelector('[data-preview]').addEventListener('click', () => setSelectedBot(bot.id));
    card.querySelector('[data-copy]').addEventListener('click', async () => {
      const code = bot.embed_code.replace('{{BASE_URL}}', window.APP_CONFIG.baseUrl);
      await navigator.clipboard.writeText(code);
      card.querySelector('[data-copy]').textContent = 'Copied';
      setTimeout(() => card.querySelector('[data-copy]').textContent = 'Copy embed', 1200);
    });
    els.botsList.appendChild(card);
  });

  if (state.bots.length && !state.selectedBotId) setSelectedBot(state.bots[0].id);
}

async function loadBots() {
  const res = await fetch('/get-bots');
  const data = await res.json();
  state.bots = data.bots || [];
  renderBots();
}

async function submitCreateBot(event) {
  event.preventDefault();
  const formData = new FormData(els.createForm);
  const questions = formData.getAll('faq_question');
  const answers = formData.getAll('faq_answer');
  const faq_entries = questions.map((question, i) => ({ question, answer: answers[i] || '' })).filter(item => item.question && item.answer);
  const payload = { name: formData.get('name'), business_name: formData.get('business_name'), faq_entries };
  const res = await fetch('/create-bot', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  const data = await res.json();
  if (!res.ok) {
    alert(data.error || 'Could not create chatbot');
    return;
  }
  els.createForm.reset();
  els.faqList.innerHTML = '';
  els.faqList.appendChild(createFaqRow());
  closeModal();
  await loadBots();
  setSelectedBot(data.bot.id);
}

async function submitPreview(event) {
  event.preventDefault();
  if (!state.selectedBotId) return;
  const message = els.previewInput.value.trim();
  if (!message) return;
  addMessage(message, 'user');
  els.previewInput.value = '';
  const res = await fetch('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ chatbot_id: state.selectedBotId, message }) });
  const data = await res.json();
  addMessage(data.reply || 'Sorry, something went wrong.', 'bot');
  await loadBots();
}

els.openModal?.addEventListener('click', openModal);
els.closeModal?.addEventListener('click', closeModal);
els.addFaq?.addEventListener('click', () => els.faqList.appendChild(createFaqRow()));
els.createForm?.addEventListener('submit', submitCreateBot);
els.previewForm?.addEventListener('submit', submitPreview);
els.modal?.addEventListener('click', (e) => { if (e.target === els.modal) closeModal(); });

if (els.faqList) els.faqList.appendChild(createFaqRow());
loadBots();


/**
 * app.js
 * Lógica de interface: renderização de mensagens, sidebar e eventos da tela.
 * Depende de config.js (APP_CONFIG) e api.js (NimbAPI), carregados antes deste arquivo.
 */

// ---- Referências DOM ----
const input = document.getElementById('messageInput');
const btn = document.getElementById('sendBtn');
const area = document.getElementById('responseArea');
const empty = document.getElementById('emptyState');
const typing = document.getElementById('typingIndicator');
const suggs = document.getElementById('suggestions');
const recentList = document.getElementById('recentList');
const previousList = document.getElementById('previousList');
const userAvatar = document.getElementById('userAvatar');
const userName = document.getElementById('userName');
const userRole = document.getElementById('userRole');
const chaosValue = document.getElementById('chaosValue');

// ---- Estado da tela ----
let conversationId = null;

function now() {
  return new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

// ---- Mensagens do chat ----
function addMessage(text, role) {
  empty.style.display = 'none';
  const msg = document.createElement('div');
  msg.className = `message ${role}`;

  const avatar = document.createElement('div');
  avatar.className = `avatar ${role === 'user' ? 'user-av' : 'ai'}`;
  avatar.textContent = role === 'user' ? 'EU' : 'Nimb';
  avatar.setAttribute('aria-hidden', 'true');

  const right = document.createElement('div');

  const bubble = document.createElement('div');
  bubble.className = `bubble ${role === 'user' ? 'user' : 'ai'}`;
  bubble.textContent = text;

  const ts = document.createElement('div');
  ts.className = 'timestamp';
  ts.textContent = now();

  right.appendChild(bubble);
  right.appendChild(ts);
  msg.appendChild(avatar);
  msg.appendChild(right);

  area.insertBefore(msg, typing);
  area.scrollTop = area.scrollHeight;
}

function addErrorMessage(text) {
  empty.style.display = 'none';
  const msg = document.createElement('div');
  msg.className = 'message error';
  const bubble = document.createElement('div');
  bubble.className = 'bubble ai';
  bubble.textContent = text;
  msg.appendChild(bubble);
  area.insertBefore(msg, typing);
  area.scrollTop = area.scrollHeight;
}

async function sendMessage() {
  const text = input.value.trim();
  if (!text) return;

  suggs.style.display = 'none';
  addMessage(text, 'user');
  input.value = '';
  input.style.height = 'auto';

  btn.classList.add('loading');
  typing.classList.add('visible');
  area.scrollTop = area.scrollHeight;

  try {
    const data = await NimbAPI.sendMessage(text, conversationId);
    conversationId = data.conversation_id || conversationId;
    addMessage(data.reply, 'ai');
    if (typeof data.chaos_level === 'number') {
      updateChaosMeter(data.chaos_level);
    }
  } catch (err) {
    console.error('Falha ao enviar mensagem:', err);
    addErrorMessage('Não foi possível falar com o servidor agora. Tente novamente em instantes.');
  } finally {
    typing.classList.remove('visible');
    btn.classList.remove('loading');
  }
}

function useSuggestion(el) {
  input.value = el.dataset.suggestion || el.textContent.replace('✦ ', '');
  input.focus();
  autoResize();
}

function autoResize() {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 120) + 'px';
}

// ---- Sidebar: histórico de conversas ----
function renderConversationList(container, items) {
  container.innerHTML = '';
  if (!items || items.length === 0) {
    const el = document.createElement('div');
    el.className = 'sidebar-item placeholder';
    el.textContent = 'Nenhuma conversa ainda';
    container.appendChild(el);
    return;
  }
  items.forEach(item => {
    const el = document.createElement('div');
    el.className = 'sidebar-item';
    el.dataset.id = item.id;
    const dot = document.createElement('span');
    dot.className = 'sidebar-dot';
    dot.style.background = 'var(--purple-400)';
    el.appendChild(dot);
    el.appendChild(document.createTextNode(item.title));
    container.appendChild(el);
  });
}

async function loadConversations() {
  try {
    const data = await NimbAPI.getConversations();
    renderConversationList(recentList, data.recent);
    renderConversationList(previousList, data.previous);
  } catch (err) {
    console.error('Falha ao carregar histórico:', err);
  }
}

// ---- Sidebar: usuário ----
async function loadUser() {
  try {
    const user = await NimbAPI.getUser();
    userName.textContent = user.name || 'Usuário';
    userRole.textContent = user.role || '';
    userAvatar.textContent = (user.name || '?').trim().charAt(0).toUpperCase();
  } catch (err) {
    console.error('Falha ao carregar usuário:', err);
    userName.textContent = 'Não foi possível carregar';
  }
}

// ---- Topbar: medidor de Caos (v2) ----
// Chamado quando o backend passar a enviar chaos_level nas respostas do chat.
function updateChaosMeter(percent) {
  chaosValue.textContent = `${Math.round(percent)}%`;
}

// ---- Inicialização ----
function init() {
  loadUser();
  loadConversations();

  suggs.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => useSuggestion(chip));
  });

  btn.addEventListener('click', sendMessage);
  input.addEventListener('input', autoResize);
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
}

document.addEventListener('DOMContentLoaded', init);

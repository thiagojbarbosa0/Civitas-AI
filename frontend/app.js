'use strict';
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];
const state = { page: 'overview', history: [], overview: null, services: [], pending: false, controller: null, serviceSeq: 0 };
const labels = { overview: 'Visão geral', assistant: 'Assistente IA', knowledge: 'Base de conhecimento', evaluation: 'Avaliações', architecture: 'Arquitetura' };
const icons = ['◈', '◫', '◎', '✧'];

async function api(path, opts) {
  const response = await fetch(path, { cache: 'no-store', ...opts });
  let payload;
  try { payload = await response.json(); } catch { payload = {}; }
  if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : `Falha HTTP ${response.status}`);
  return payload;
}
function node(tag, className, text) {
  const n = document.createElement(tag); if (className) n.className = className;
  if (text !== undefined) n.textContent = text; return n;
}
function empty(el) { el.replaceChildren(); }
function toast(msg, error = false) { const t = $('#toast'); t.textContent = msg; t.className = `toast visible ${error ? 'error' : ''}`; window.setTimeout(() => t.classList.remove('visible'), 3800); }
function go(page) {
  if (!labels[page]) return;
  state.page = page;
  $$('.page').forEach(n => n.classList.toggle('active', n.id === `page-${page}`));
  $$('.nav-item[data-page]').forEach(n => n.classList.toggle('active', n.dataset.page === page));
  $('#crumb').textContent = labels[page]; $('#sidebar').classList.remove('mobile-open');
  history.replaceState(null, '', `#${page}`);
  if (page === 'knowledge') loadServices();
  if (page === 'overview') refreshOverview();
}
function makePrompt(text, type = 'row') {
  const b = node('button', type === 'row' ? 'suggestion' : 'prompt-chip'); b.type = 'button';
  if (type === 'row') {
    b.append(node('span', 'suggestion-icon', icons[Math.floor(Math.random() * icons.length)]), node('span', 'suggestion-text', text), node('span', 'suggestion-arrow', '↗'));
  } else b.textContent = '✧  ' + text;
  b.addEventListener('click', () => { go('assistant'); $('#chat-input').value = text; submitChat(); });
  return b;
}
async function refreshOverview() {
  try {
    const x = await api('/api/v1/overview'); state.overview = x;
    $('#stat-docs').textContent = x.services.toString().padStart(2, '0');
    $('#stat-queries').textContent = String(x.metrics.queries).padStart(2, '0');
    $('#stat-latency').textContent = x.metrics.average_latency_ms || '0';
    $('#model-name').textContent = x.model;
    $('#model-desc').textContent = x.mode === 'demo' ? 'Modo determinístico sem chave de API' : `${x.provider.toUpperCase()} · LangChain`;
    $('#mode-tag').textContent = x.mode.toUpperCase();
    $('#composer-label').textContent = `Retrieval ${x.retrieval.toUpperCase()} · ${x.mode.toUpperCase()}`;
    empty($('#overview-prompts'));
    const chips = $('#chat-prompts');
    if (chips) empty(chips);
    x.examples.forEach((ex, i) => {
      $('#overview-prompts').append(makePrompt(ex));
      if (chips && i < 3) chips.append(makePrompt(ex, 'chip'));
    });
    $('#top-status').textContent = 'API online';
  } catch (e) { $('#top-status').textContent = 'API indisponível'; toast(e.message, true); }
}
function messageBubble(role, text) {
  const wrap = node('div', `message ${role}`);
  const avatar = node('div', 'message-avatar', role === 'user' ? 'U' : '✧');
  const body = node('div', 'message-body');
  const label = node('div', 'message-name', role === 'user' ? 'Você' : 'Civitas AI');
  const content = node('div', 'message-content');
  // Formata **negrito** sem innerHTML: conteúdo do LLM continua texto não confiável.
  const raw = String(text); const pattern = /\*\*([^*\n]+)\*\*/g;
  let cursor = 0; let match;
  while ((match = pattern.exec(raw)) !== null) {
    if (match.index > cursor) content.append(document.createTextNode(raw.slice(cursor, match.index)));
    content.append(node('strong', '', match[1]));
    cursor = pattern.lastIndex;
  }
  if (cursor < raw.length) content.append(document.createTextNode(raw.slice(cursor)));
  body.append(label, content); wrap.append(avatar, body); return wrap;
}
async function submitChat() {
  if (state.pending) return;
  const input = $('#chat-input'); const msg = input.value.trim();
  if (msg.length < 2) return;
  state.pending = true;
  const controller = new AbortController(); state.controller = controller;
  $('#send-chat').disabled = true; $('#send-chat').textContent = 'Processando…';
  $('#chat-messages').querySelector('.welcome')?.remove();
  const container = $('#chat-messages'); container.append(messageBubble('user', msg));
  input.value = '';
  const loading = node('div', 'typing', '✧  Roteando → recuperando evidências → analisando…');
  container.append(loading); container.scrollTop = container.scrollHeight;
  try {
    const data = await api('/api/v1/chat', { method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ message: msg, history: state.history.slice(-6) }), signal: controller.signal });
    if (controller.signal.aborted) return;
    state.history.push({role:'user', content:msg}, {role:'assistant', content:data.answer});
    container.append(messageBubble('assistant', data.answer));
    drawSources(data.sources || []); drawTrace(data.trace || [], data.tools_used || []);
  } catch(e) { if (!controller.signal.aborted) { container.append(messageBubble('assistant', `Não consegui processar sua consulta: ${e.message}`)); toast(e.message, true); } }
  finally { loading.remove(); if (state.controller === controller) {
    container.scrollTop = container.scrollHeight; state.pending = false; state.controller = null;
    $('#send-chat').disabled = false; $('#send-chat').textContent = 'Enviar ↗'; refreshOverview();
  } }
}
function drawSources(sources) {
  const box = $('#source-list'); empty(box);
  if (!sources.length) { box.append(node('div', 'empty-side', 'Nenhuma evidência recuperada.')); return; }
  sources.forEach((s, i) => {
    const card = node('button', 'source-card');
    const row = node('div', 'source-top'); row.append(node('span', 'doc-code', s.id), node('span', 'source-score', `Top ${i + 1}`));
    card.append(row, node('strong', '', s.title), node('small', '', s.category));
    card.addEventListener('click', async () => { go('knowledge'); await openDetail(s.id); });
    box.append(card);
  });
}
function drawTrace(trace, tools) {
  const box = $('#trace-list'); empty(box);
  trace.forEach((step, i) => {
    const item = node('div', 'trace-item');
    item.append(node('span', 'trace-number', String(i + 1)), node('div', 'trace-text'));
    item.lastChild.append(node('strong', '', step.agent), node('small', '', step.detail));
    box.append(item);
  });
  if (tools.length) box.append(node('div', 'tools-used', `Ferramentas: ${tools.join(', ')}`));
}
async function loadServices(q = '') {
  const seq = ++state.serviceSeq;
  try {
    const result = await api(`/api/v1/services?q=${encodeURIComponent(q)}`);
    if (seq !== state.serviceSeq) return;
    state.services = result.items; $('#knowledge-count').textContent = `${result.total} ${result.total === 1 ? 'documento disponível' : 'documentos disponíveis'}`;
    const tbody = $('#service-tbody'); empty(tbody);
    if (!result.items.length) { const tr = node('tr'); const td = node('td', 'blank-row', 'Nenhum documento encontrado.'); td.colSpan=4; tr.append(td); tbody.append(tr); }
    result.items.forEach(d => {
      const tr = node('tr');
      const id = node('td'); id.append(node('span', 'doc-code', d.id));
      const title = node('td'); title.append(node('strong', 'table-title', d.title), node('small', 'table-description', d.summary));
      const cat = node('td'); cat.append(node('span', 'category-chip', d.category));
      const action = node('td'); const b = node('button', 'table-action', 'Ver detalhes ↗'); b.addEventListener('click', () => openDetail(d.id)); action.append(b);
      tr.append(id, title, cat, action); tbody.append(tr);
    });
  } catch(e) { toast(e.message, true); }
}
async function openDetail(id) {
  try {
    const d = await api(`/api/v1/services/${encodeURIComponent(id)}`);
    const panel = $('#detail-panel'); panel.hidden = false;
    $('#detail-title').textContent = `${d.id} · ${d.title}`; $('#detail-summary').textContent = d.summary;
    for (const [target, items] of [['#detail-reqs', d.requirements], ['#detail-steps', d.steps]]) {
      empty($(target)); (items || []).forEach(i => $(target).append(node('li','',i)));
    }
    $('#detail-meta').textContent = `Prazo: ${d.deadline}  ·  Custo: ${d.fee}  ·  Canal: ${d.channel}  ·  Nota: ${d.notes}`;
    panel.scrollIntoView({behavior:'smooth', block:'start'});
  } catch(e) { toast(e.message, true); }
}
async function runEvaluation() {
  $('#run-eval').disabled = true; $('#run-eval').textContent = 'Avaliando…'; $('#eval-state').textContent = 'EM EXECUÇÃO';
  try {
    const data = await api('/api/v1/evaluate', {method:'POST'});
    $('#eval-top1').textContent = `${Math.round(data.hit_at_1 * 100)}%`;
    $('#eval-top3').textContent = `${Math.round(data.hit_at_3 * 100)}%`;
    $('#eval-total').textContent = data.n;
    $('#eval-abstention').textContent = `${Math.round(data.abstention_rate * 100)}%`;
    $('#eval-state').textContent = 'CONCLUÍDO';
    const tbody = $('#eval-results'); empty(tbody);
    data.cases.forEach(d => {
      const tr = node('tr'); const q=node('td','eval-question',d.question); const id=node('td'); id.append(node('span','doc-code',d.expected_id));
      const rank=node('td','ranking',d.retrieved.join(' · ') || '—'); const result=node('td'); result.append(node('span', d.hit_at_1 ? 'result-pass' : (d.hit_at_3 ? 'result-warn' : 'result-fail'), d.hit_at_1 ? '✓ Top 1' : (d.hit_at_3 ? '◈ Top 3' : '✕ Falha')));
      tr.append(q,id,rank,result);tbody.append(tr);
    });
    refreshOverview();
  } catch(e) { toast(e.message, true); $('#eval-state').textContent='ERRO'; }
  finally { $('#run-eval').disabled = false; $('#run-eval').textContent = '▶  Executar avaliação'; }
}
async function ingest(e) {
  e.preventDefault(); const feedback = $('#ingest-feedback'); feedback.textContent = 'Indexando…';
  const doc = {id:$('#doc-id').value, title:$('#doc-title').value, category:$('#doc-category').value,
    summary:$('#doc-summary').value};
  try {
    const x = await api('/api/v1/documents', {method:'POST', headers:{'Content-Type':'application/json',
      'Authorization':`Bearer ${$('#admin-token').value}`}, body:JSON.stringify(doc)});
    feedback.textContent = `${x.id} indexado com sucesso.`; $('#admin-token').value=''; $('#ingest-form').reset(); loadServices(); refreshOverview();
  } catch(e) { feedback.textContent = `Não foi possível indexar: ${e.message}`; }
}
function wire() {
  $$('.nav-item[data-page]').forEach(b => b.addEventListener('click', () => go(b.dataset.page)));
  $$('[data-go]').forEach(b => b.addEventListener('click', () => go(b.dataset.go)));
  $('#mobile-menu').addEventListener('click', () => $('#sidebar').classList.toggle('mobile-open'));
  $('#chat-form').addEventListener('submit', e => { e.preventDefault(); submitChat(); });
  $('#chat-input').addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) {e.preventDefault(); submitChat();} });
  $('#clear-chat').addEventListener('click', () => {
    state.controller?.abort(); state.controller = null; state.pending = false;
    $('#send-chat').disabled = false; $('#send-chat').textContent = 'Enviar ↗';
    state.history=[]; empty($('#chat-messages')); const w = node('div','welcome');
    w.append(node('div','welcome-symbol','✳'), node('h2','', 'Nova conversa'),
      node('p','', 'Digite sua próxima pergunta para começar.'), node('div','prompt-chips'));
    w.lastChild.id = 'chat-prompts';
    $('#chat-messages').append(w); drawSources([]); drawTrace([],[]); refreshOverview(); });
  $('#close-detail').addEventListener('click', () => {$('#detail-panel').hidden=true;});
  let searchTimeout;
  $('#search-services').addEventListener('input', e => { const value = e.target.value;
    clearTimeout(searchTimeout); searchTimeout = setTimeout(() => loadServices(value), 180); });
  $('#run-eval').addEventListener('click',runEvaluation);
  $('#ingest-form').addEventListener('submit', ingest);
  window.addEventListener('hashchange',()=>go(location.hash.slice(1) || 'overview'));
  window.addEventListener('keydown', e => { if (e.key === 'Escape') $('#sidebar').classList.remove('mobile-open'); });
}
wire(); go(labels[location.hash.slice(1)] ? location.hash.slice(1) : 'overview');
refreshOverview();

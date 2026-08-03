const ICONS = {
  inbox: '<path d="M4 5.5h16l-1.5 12h-13z"/><path d="M4.8 14h4l1.3 2h3.8l1.3-2h4"/>',
  calendar: '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M8 3v4m8-4v4M4 10h16"/>',
  reply: '<path d="m10 8-5 4 5 4v-3h3.5c3 0 4.7 1.3 5.5 4-.1-5-2.3-7-5.5-7H10z"/>',
  sparkles: '<path d="m12 3 1.1 3.4L16.5 7.5l-3.4 1.1L12 12l-1.1-3.4-3.4-1.1 3.4-1.1zM18 13l.7 2.3L21 16l-2.3.7L18 19l-.7-2.3L15 16l2.3-.7zM6 13l.7 2.3L9 16l-2.3.7L6 19l-.7-2.3L3 16l2.3-.7z"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 12 9 5 9-5m-18 4 9 5 9-5"/>',
  sliders: '<path d="M4 6h7m4 0h5M4 12h3m4 0h9M4 18h9m4 0h3"/><circle cx="13" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="15" cy="18" r="2"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H3v-4h.1a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.6V3h4v.1a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1z"/>',
  shield: '<path d="M12 3 20 6v5c0 5-3.4 8.4-8 10-4.6-1.6-8-5-8-10V6z"/><path d="m8.5 12 2.2 2.2 4.8-5"/>',
  chevron: '<path d="m9 18 6-6-6-6"/>', search: '<circle cx="11" cy="11" r="7"/><path d="m16.5 16.5 4 4"/>',
  moon: '<path d="M20 15.5A8.5 8.5 0 0 1 8.5 4 8.5 8.5 0 1 0 20 15.5z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>', close: '<path d="m6 6 12 12M18 6 6 18"/>',
  arrow: '<path d="M5 12h14m-5-5 5 5-5 5"/>', lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  alert: '<path d="M12 3 2.5 20h19z"/><path d="M12 9v4m0 3h.01"/>',
  task: '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="m8 12 2.2 2.2L16 8.5"/>',
  open: '<path d="M14 4h6v6m0-6-9 9"/><path d="M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>',
  edit: '<path d="M4 20h4l11-11-4-4L4 16zM13.5 6.5l4 4"/>', trash: '<path d="M4 7h16M9 7V4h6v3m3 0-1 14H7L6 7m4 4v6m4-6v6"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10h.01"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m4 7 8 6 8-6"/>',
  more: '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
  plus: '<path d="M12 5v14M5 12h14"/>', download: '<path d="M12 3v12m-4-4 4 4 4-4M4 19h16"/>',
};

const esc = (value = '') => String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ICONS.info}</svg>`;
const hydrateIcons = (root = document) => root.querySelectorAll('[data-icon]').forEach(el => { el.innerHTML = icon(el.dataset.icon); });

const state = {
  view: 'now', cards: [], counts: {}, settings: {}, connectors: [], model: {}, selectedId: null,
  priority: '', source: '', search: '', selectedDetail: null, refreshTimer: null,
};

const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];

async function api(path, options = {}) {
  const response = await fetch(`/api/v1${path}`, {
    credentials: 'same-origin',
    headers: {'Content-Type': 'application/json', ...(options.headers || {})},
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

function sourceMeta(source) {
  return {
    gmail: ['G', 'Gmail'], line_notification: ['L', 'LINE'], messenger_notification: ['M', 'Messenger'],
    windows_notification: ['W', 'Windows'], line_official_webhook: ['L', 'LINE OA'], messenger_page_webhook: ['M', 'Page'],
  }[source] || ['S', source || 'SignalDesk'];
}

function priorityLabel(priority) {
  return {urgent:'緊急', high:'重要', normal:'一般', low:'低優先', noise:'雜訊', unknown:'待確認'}[priority] || priority;
}

function completenessLabel(value) {
  return {full:'完整郵件', thread_delta:'對話增量', notification_preview:'通知預覽', metadata_only:'只有來源資訊', mixed:'混合內容'}[value] || value;
}

function timeAgo(value) {
  if (!value) return '';
  const date = new Date(value), diff = Date.now() - date.getTime(), minutes = Math.max(0, Math.floor(diff / 60000));
  if (minutes < 1) return '剛剛';
  if (minutes < 60) return `${minutes} 分`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)} 小時`;
  if (minutes < 10080) return `${Math.floor(minutes / 1440)} 天`;
  return new Intl.DateTimeFormat('zh-TW', {month:'numeric', day:'numeric'}).format(date);
}

function dateTime(value) {
  if (!value) return '尚未設定';
  return new Intl.DateTimeFormat('zh-TW', {month:'short', day:'numeric', weekday:'short', hour:'2-digit', minute:'2-digit'}).format(new Date(value));
}

function toast(message, type = 'success') {
  const item = document.createElement('div');
  item.className = 'toast';
  item.innerHTML = `${icon(type === 'error' ? 'alert' : 'check')}<span>${esc(message)}</span>`;
  $('#toastRegion').append(item);
  setTimeout(() => item.remove(), 3200);
}

async function bootstrap() {
  try {
    const data = await api('/bootstrap');
    Object.assign(state, {cards: data.cards, counts: data.counts, settings: data.settings, connectors: data.connectors, model: data.model});
    applyTheme();
    $('#focusToggle').checked = Boolean(state.settings.focus_mode);
    $('#modelStatus').textContent = state.model.backend === 'rule' ? '安全規則模式' : state.model.id;
    renderCounts();
    renderCards();
    renderGlance();
    if (!state.settings.onboarding_complete) $('#onboarding').hidden = false;
    connectStream();
  } catch (error) {
    toast(`無法載入 SignalDesk：${error.message}`, 'error');
  }
}

function renderCounts() {
  $('#navNowCount').textContent = state.counts.open || 0;
  $('#navReplyCount').textContent = state.counts.reply || 0;
  $('#orbCount').textContent = state.counts.important || 0;
  $('#orbCount').hidden = !(state.counts.important > 0);
}

function titleForView(view) {
  return {now:['INBOX CENTER','現在'], today:['DUE & RECENT','今天'], reply:['WAITING ON YOU','需要回覆'], done:['ARCHIVE','已完成']}[view] || ['INBOX CENTER','現在'];
}

async function loadCards({keepSelection = false} = {}) {
  const params = new URLSearchParams({view: state.view, search: state.search, source: state.source, priority: state.priority});
  const data = await api(`/cards?${params}`);
  state.cards = data.items; state.counts = data.counts;
  if (!keepSelection || !state.cards.some(c => c.card_id === state.selectedId)) state.selectedId = null;
  renderCounts(); renderCards(); renderGlance();
}

function renderCards() {
  const [eyebrow, title] = titleForView(state.view);
  $('#viewEyebrow').textContent = eyebrow; $('#viewTitle').textContent = title; $('#viewCount').textContent = state.cards.length;
  $('#workspace').classList.remove('special'); $('#listPane').hidden = false;
  const list = $('#cardList');
  if (!state.cards.length) {
    list.innerHTML = `<div class="list-empty"><div class="empty-orbit">${icon('check')}</div><strong>這裡很安靜</strong><p>${state.search ? '沒有符合搜尋的訊息。' : '目前沒有需要處理的卡片。'}</p><button class="button secondary" id="emptySeed">載入示範資料</button></div>`;
    $('#emptySeed')?.addEventListener('click', seedDemo);
    if (!state.selectedId) renderEmptyDetail();
    return;
  }
  list.innerHTML = state.cards.map(card => {
    const [letter] = sourceMeta(card.source);
    const badges = [
      card.requires_reply === 'yes' ? `<span class="mini-badge reply">${icon('reply')}需回覆</span>` : '',
      card.deadline_text ? `<span class="mini-badge due">${icon('clock')}${esc(card.deadline_text)}</span>` : '',
      card.uncertainty_flags?.length ? `<span class="mini-badge">${icon('info')}預覽限制</span>` : '',
    ].join('');
    return `<button class="message-card ${card.card_id === state.selectedId ? 'selected' : ''}" data-card-id="${esc(card.card_id)}" role="option" aria-selected="${card.card_id === state.selectedId}">
      <span class="source-icon ${esc(card.source)}">${letter}</span>
      <span class="card-main"><span class="sender-row"><span class="priority-dot ${esc(card.priority)}"></span><strong>${esc(card.sender || card.title || '未知來源')}</strong></span><span class="card-summary">${esc(card.summary)}</span><span class="mini-badges">${badges}</span></span>
      <time class="card-time">${timeAgo(card.updated_at || card.created_at)}</time>
    </button>`;
  }).join('');
  list.querySelectorAll('[data-card-id]').forEach(button => button.addEventListener('click', () => selectCard(button.dataset.cardId)));
}

function renderEmptyDetail() {
  $('#detailPane').classList.remove('mobile-visible');
  $('#detailPane').innerHTML = `<div class="empty-detail"><div class="empty-orbit">${icon('sparkles')}</div><h2>選擇一則訊息</h2><p>查看摘要、原文證據、待辦與安全的下一步。</p></div>`;
}

async function selectCard(cardId) {
  state.selectedId = cardId;
  renderCards();
  $('#detailPane').innerHTML = `<div class="empty-detail"><div class="empty-orbit">${icon('sparkles')}</div><p>正在整理完整資訊…</p></div>`;
  try {
    state.selectedDetail = await api(`/cards/${encodeURIComponent(cardId)}`);
    renderDetail(state.selectedDetail);
    $('#detailPane').classList.add('mobile-visible');
    $('#detailPane').focus();
  } catch (error) { toast(error.message, 'error'); }
}

function actionButton(action) {
  const map = {
    open_source: ['open','開啟來源','primary'], draft_reply: ['edit','建立草稿','secondary'],
    create_reminder: ['bell','建立提醒','secondary'], snooze: ['clock','稍後提醒','secondary'],
    mark_done: ['check','標示完成','ghost'], needs_review: ['info','需要確認','ghost'],
  };
  const [ic, label, cls] = map[action] || ['more', action, 'ghost'];
  if (action === 'needs_review') return '';
  return `<button class="button ${cls}" data-action="${action}">${icon(ic)}${label}</button>`;
}

function renderDetail(card) {
  const [, sourceName] = sourceMeta(card.source), event = card.events?.at(-1) || {};
  const limitations = card.uncertainty_flags?.length ? `<div class="content-block limitation">${icon('alert')}<div><strong>這是通知預覽，可能缺少上下文</strong><small>SignalDesk 只使用 Windows 實際顯示的文字，沒有讀取完整 LINE／Messenger 對話，也不會猜測圖片或貼圖內容。</small></div></div>` : '';
  const actions = (card.actions || []).map(actionButton).join('');
  const items = card.action_items?.length ? card.action_items.map(item => `<div class="fact-card"><div class="fact-head">${icon('task')}待辦事項</div><p>${esc(item.text)}</p><span class="evidence">原文：「${esc(item.supporting_span)}」</span></div>`).join('') : `<div class="fact-card"><div class="fact-head">${icon('task')}待辦事項</div><p>沒有擷取到具體、可驗證的待辦。</p></div>`;
  const deadlines = card.deadlines?.length ? card.deadlines.map(deadline => `<div class="fact-card"><div class="fact-head">${icon('clock')}期限</div><p><strong>${esc(deadline.original_text)}</strong><br>${deadline.normalized_at ? dateTime(deadline.normalized_at) : '時間語意不明，請自行選擇'}</p><span class="evidence">原文證據已驗證</span></div>`).join('') : `<div class="fact-card"><div class="fact-head">${icon('clock')}期限</div><p>原文沒有明確期限。</p></div>`;
  const originals = (card.events || []).map((item, index) => `<details class="original-event" ${card.events.length === 1 ? 'open' : ''}><summary><span>${esc(item.sender)} · ${index + 1}/${card.events.length}</span><time>${dateTime(item.received_at)}</time></summary><pre>${esc(item.content || '（通知未提供可讀內容）')}</pre></details>`).join('');
  const reasonLabels = {direct_question:'直接提問', explicit_request:'明確要求', explicit_deadline:'包含期限', reply_needed:'需要回覆', deadline_detected:'偵測到期限', vip_sender:'VIP 寄件者', security_alert:'安全警示', source_limitation:'來源內容有限', shadow_mode:'Shadow Mode', would_surface_now:'原建議立即顯示', focus_mode:'專注模式', quiet_hours:'安靜時段', content_missing:'缺少內容', preview_only:'只有預覽'};
  const reasons = (card.why_shown || []).map(reason => `<span class="why-chip">${esc(reasonLabels[reason] || reason.replaceAll('_',' '))}</span>`).join('');
  const traces = (card.traces || []).map(trace => `<div class="trace-line"><strong>${esc(trace.stage)}</strong><span>${esc(trace.status)} · ${esc(card.model_backend || '')}</span><time>${timeAgo(trace.created_at)}</time></div>`).join('');
  $('#detailPane').innerHTML = `<div class="detail-content">
    <div class="detail-meta"><span class="source-label">${sourceName}</span><span class="priority-label ${esc(card.priority)}">${priorityLabel(card.priority)}</span><span class="completeness-label">${completenessLabel(card.content_completeness)}</span><time class="detail-time">${dateTime(card.updated_at)}</time></div>
    <p class="detail-sender">${esc(card.sender || '未知寄件者')}</p><h1 class="detail-title">${esc(card.title || card.summary)}</h1>
    <div class="detail-actions">${actions}<button class="button ghost" data-action="feedback">${icon('more')}更多</button></div>
    <div class="content-block highlight"><div class="block-label">${icon('sparkles')}SIGNALDESK 摘要</div><p class="summary-text">${esc(card.summary)}</p></div>
    ${limitations}
    <div class="block-grid">${items}${deadlines}</div>
    <div class="content-block"><div class="block-label">${icon('info')}為什麼顯示</div><div class="why-chips">${reasons || '<span class="why-chip">一般收件匣</span>'}</div></div>
    <div class="content-block"><div class="block-label">${icon('mail')}來源內容</div>${originals}</div>
    <details class="developer-trace"><summary>Developer trace · ${esc(card.model_backend || 'rule')}</summary>${traces || '<div class="trace-line">沒有 trace</div>'}</details>
  </div>`;
  $('#detailPane').querySelectorAll('[data-action]').forEach(button => button.addEventListener('click', () => handleAction(button.dataset.action, card)));
  $('#detailPane').querySelector('.detail-content')?.addEventListener('click', e => { if (e.target.matches('.detail-content::before')) $('#detailPane').classList.remove('mobile-visible'); });
}

async function handleAction(action, card) {
  if (action === 'open_source') return performAction(card, 'open');
  if (action === 'mark_done') return performAction(card, 'mark_done');
  if (action === 'snooze') return snoozeModal(card);
  if (action === 'create_reminder') return reminderModal(card);
  if (action === 'draft_reply') return draftModal(card);
  if (action === 'feedback') return feedbackModal(card);
}

async function performAction(card, action, value = null) {
  try {
    const result = await api(`/cards/${card.card_id}/actions`, {method:'POST', body:JSON.stringify({action, value})});
    if (action === 'open') {
      if (result.safe_to_open) window.open(result.source_url, '_blank', 'noopener,noreferrer');
      else toast('來源沒有提供安全的開啟連結', 'error');
    } else toast({mark_done:'已標示完成', snooze:'已稍後提醒', create_reminder:'提醒已建立', draft_reply:'草稿已儲存在本機', mark_important:'已加入重要寄件者', mark_not_important:'已建立靜音規則'}[action] || '已更新');
    closeModal();
    await loadCards({keepSelection: action === 'create_reminder' || action === 'draft_reply'});
    if (state.selectedId) await selectCard(state.selectedId);
    return result;
  } catch (error) { toast(error.message, 'error'); }
}

function showModal(title, body, buttons) {
  $('#modalTitle').textContent = title; $('#modalBody').innerHTML = body; $('#modalActions').innerHTML = '';
  buttons.forEach(button => {
    const element = document.createElement('button'); element.className = `button ${button.className || 'secondary'}`; element.textContent = button.label;
    element.addEventListener('click', button.onClick); $('#modalActions').append(element);
  });
  $('#modalBackdrop').hidden = false; $('#modalClose').focus();
}
function closeModal() { $('#modalBackdrop').hidden = true; }

function snoozeModal(card) {
  const nextHour = new Date(Date.now()+3600000); nextHour.setSeconds(0,0);
  showModal('稍後提醒', `<p>卡片會暫時離開「現在」，到指定時間後重新出現。</p><label for="snoozeAt">提醒時間</label><input id="snoozeAt" type="datetime-local" value="${nextHour.toISOString().slice(0,16)}">`, [
    {label:'取消', onClick:closeModal}, {label:'稍後提醒', className:'primary', onClick:() => performAction(card,'snooze',{at:$('#snoozeAt').value})},
  ]);
}

function reminderModal(card) {
  const defaultAt = card.deadlines?.[0]?.normalized_at || new Date(Date.now()+3600000).toISOString();
  showModal('建立本機提醒', `<p>提醒只會儲存在 SignalDesk，並連回這張卡片；不會修改外部行事曆。</p><label for="reminderAt">提醒時間</label><input id="reminderAt" type="datetime-local" value="${new Date(defaultAt).toISOString().slice(0,16)}"><label for="reminderNote">備註（選填）</label><input id="reminderNote" maxlength="300" placeholder="例如：先整理圖表">`, [
    {label:'取消', onClick:closeModal}, {label:'建立提醒', className:'primary', onClick:() => performAction(card,'create_reminder',{at:$('#reminderAt').value,note:$('#reminderNote').value})},
  ]);
}

function draftModal(card) {
  const recipient = card.events?.at(-1)?.sender || card.sender || '';
  const body = '您好，\n\n謝謝您的訊息，我已收到。我確認內容後會再回覆您。\n\n謝謝。';
  showModal('建立 Gmail 回覆草稿', `<p><strong>收件者：</strong>${esc(recipient)}</p><div class="boundary-note">${icon('shield')}<div><strong>只建立本機預覽</strong><small>SignalDesk 永遠不會自動送出訊息。</small></div></div><label for="draftBody">草稿內容</label><textarea id="draftBody">${esc(body)}</textarea>`, [
    {label:'取消', onClick:closeModal}, {label:'儲存草稿', className:'primary', onClick:() => performAction(card,'draft_reply',{body:$('#draftBody').value})},
  ]);
}

function feedbackModal(card) {
  showModal('調整這類訊息', `<p>明確回饋會立即建立本機規則。單次開啟或忽略不會偷偷變成永久規則。</p>`, [
    {label:'總是重視此寄件者', className:'primary', onClick:() => performAction(card,'mark_important')},
    {label:'不要打斷此寄件者', onClick:() => performAction(card,'mark_not_important')},
  ]);
}

async function changeView(view) {
  state.view = view; state.selectedId = null; state.selectedDetail = null;
  $$('.nav-item').forEach(item => item.classList.toggle('active', item.dataset.view === view));
  $('#appShell').classList.remove('menu-open');
  if (['digest','sources','rules','settings'].includes(view)) {
    $('#workspace').classList.add('special'); $('#listPane').hidden = true; $('#detailPane').classList.remove('mobile-visible');
    if (view === 'digest') await renderDigest();
    if (view === 'sources') renderSources();
    if (view === 'rules') await renderRules();
    if (view === 'settings') renderSettings();
  } else {
    $('#workspace').classList.remove('special'); $('#listPane').hidden = false; renderEmptyDetail(); await loadCards();
  }
}

function specialHeader(eyebrow, title, lead, action = '') {
  return `<div class="full-page-head"><div><p class="eyebrow">${eyebrow}</p><h1>${title}</h1><p class="lead">${lead}</p></div>${action}</div>`;
}

async function renderDigest() {
  const data = await api('/digest');
  const section = (title, ic, items) => `<section class="digest-section"><div class="section-head">${icon(ic)}<h2>${title}</h2></div>${items.length ? items.map(card => `<div class="digest-item" data-digest-card="${esc(card.card_id)}"><div><strong>${esc(card.sender || card.title)}</strong><span>${esc(card.summary)}</span></div><time>${timeAgo(card.updated_at)}</time></div>`).join('') : '<p class="lead">沒有項目。</p>'}</section>`;
  $('#detailPane').innerHTML = `<div class="full-page">${specialHeader('DAILY DIGEST','每日摘要','把值得處理的訊息聚成安靜、可行動的一頁。',`<span class="source-label">${dateTime(data.generated_at)}</span>`)}<div class="digest-grid"><div class="digest-summary">
    <div class="metric-card"><strong>${data.counts.urgent}</strong><span>重要與緊急</span></div><div class="metric-card"><strong>${data.counts.due_today}</strong><span>今天到期</span></div><div class="metric-card"><strong>${data.counts.needs_reply}</strong><span>需要回覆</span></div><div class="metric-card"><strong>${data.counts.for_information}</strong><span>僅供參考</span></div>
  </div>${section('優先處理','alert',data.urgent)}${section('今天到期','calendar',data.due_today)}${section('需要回覆','reply',data.needs_reply)}${section('僅供參考','inbox',data.for_information)}</div></div>`;
  $('#detailPane').querySelectorAll('[data-digest-card]').forEach(item => item.addEventListener('click', async () => { await changeView('now'); await selectCard(item.dataset.digestCard); }));
}

function renderSources() {
  const label = id => id.startsWith('gmail') ? ['G','Gmail'] : id.includes('windows') ? ['W','Windows 通知'] : ['S',id];
  const cards = state.connectors.map(connector => { const [letter, name] = label(connector.connector_id); return `<div class="source-card"><div class="source-card-top"><span class="source-icon ${esc(connector.source)}">${letter}</span><div><strong>${esc(name)}</strong><small>${esc(connector.connector_id)}</small></div><span class="health-badge ${esc(connector.status)}">${esc(connector.status)}</span></div><p>${esc(connector.detail || '')}</p><div class="capability-list">${(connector.capabilities || []).map(cap => `<span>${esc(cap)}</span>`).join('')}</div><button class="button secondary source-help" data-connector="${esc(connector.connector_id)}" style="margin-top:14px">設定方式</button></div>`; }).join('');
  $('#detailPane').innerHTML = `<div class="full-page">${specialHeader('CONNECTORS','訊息來源','Connector 只取得權限允許的內容；個人 LINE 與 Messenger 永遠只處理 Windows 通知預覽。')}<div class="source-grid">${cards}</div></div>`;
  $$('.source-help').forEach(button => button.addEventListener('click', () => connectorHelp(button.dataset.connector)));
}

function connectorHelp(id) {
  const gmail = id.startsWith('gmail');
  showModal(gmail ? '連接 Gmail' : '連接 Windows 通知', gmail ? `<p>將 Google Desktop OAuth 的 <code>credentials.json</code> 放在專案根目錄，安裝 <code>.[gmail]</code> extra，再由 connector 執行官方 installed-app flow。Token 只存 Windows Credential Manager／OS keyring。</p><div class="boundary-note">${icon('shield')}<div><strong>最小權限</strong><small>預設只要求 Gmail readonly；草稿 scope 需另外啟用。</small></div></div>` : `<p>Windows 11 native shell 需取得 UserNotificationListener 權限，再把 allowlist 內的 toast payload 送到本機 bridge endpoint。</p><div class="boundary-note">${icon('info')}<div><strong>內容限制</strong><small>若使用者關閉通知預覽，SignalDesk 也不會取得訊息內容。</small></div></div>`, gmail ? [{label:'取消', onClick:closeModal},{label:'開始 OAuth', className:'primary', onClick:beginGmailConnect}] : [{label:'了解', className:'primary', onClick:closeModal}]);
}

async function beginGmailConnect() {
  try {
    $('#modalActions').innerHTML = '<span class="source-label">等待瀏覽器授權…</span>';
    const result = await api('/connectors/gmail/connect', {method:'POST'});
    closeModal(); toast(`Gmail 已連接，同步 ${result.synced} 封郵件`);
    const boot = await api('/bootstrap'); state.connectors=boot.connectors; state.counts=boot.counts;
    renderSources(); renderCounts();
  } catch (error) { toast(error.message,'error'); closeModal(); }
}

async function renderRules() {
  const data = await api('/rules');
  const kindLabel = {vip_sender:'重要寄件者',mute_sender:'靜音寄件者',mute_category:'靜音類別',priority_sender:'提高優先'};
  const list = data.items.length ? data.items.map(rule => `<div class="rule-item"><span class="rule-icon">${icon(rule.kind.startsWith('mute') ? 'moon' : 'sparkles')}</span><div><strong>${esc(rule.pattern)}</strong><small>${esc(kindLabel[rule.kind] || rule.kind)} · 僅儲存在本機</small></div><button class="icon-button subtle delete-rule" data-rule="${esc(rule.rule_id)}" aria-label="刪除規則">${icon('trash')}</button></div>`).join('') : '<div class="list-empty"><strong>尚未建立規則</strong><p>明確選擇後，規則才會永久保存。</p></div>';
  $('#detailPane').innerHTML = `<div class="full-page">${specialHeader('PERSONALIZATION','規則','用可檢查、可撤回的規則控制哪些訊息值得打斷你。')}<div class="rules-grid"><form class="rule-form" id="ruleForm"><label>規則類型<select name="kind"><option value="vip_sender">重要寄件者</option><option value="mute_sender">靜音寄件者</option><option value="mute_category">靜音類別</option><option value="priority_sender">提高寄件者優先級</option></select></label><label>寄件者或類別<input name="pattern" required maxlength="500" placeholder="例如 professor@example.edu"></label><button class="button primary" type="submit">${icon('plus')}新增規則</button></form><div class="rule-list">${list}</div></div></div>`;
  $('#ruleForm').addEventListener('submit', async e => { e.preventDefault(); const form = new FormData(e.currentTarget); await api('/rules',{method:'POST',body:JSON.stringify({kind:form.get('kind'),pattern:form.get('pattern')})}); toast('規則已新增'); renderRules(); });
  $$('.delete-rule').forEach(button => button.addEventListener('click', async () => { await api(`/rules/${button.dataset.rule}`,{method:'DELETE'}); toast('規則已刪除'); renderRules(); }));
}

function settingSwitch(key, title, description, checked) {
  return `<div class="setting-row"><div><strong>${title}</strong><small>${description}</small></div><label class="switch"><input type="checkbox" data-setting="${key}" ${checked ? 'checked' : ''}><span></span></label></div>`;
}

function renderSettings() {
  const s = state.settings;
  $('#detailPane').innerHTML = `<div class="full-page">${specialHeader('PREFERENCES','設定','控制干擾、資料保留、模型常駐與本機隱私。')}<div class="settings-grid">
    <section class="settings-section"><h2>注意力與通知</h2><p>這些設定會進入 deterministic interruption policy。</p>${settingSwitch('focus_mode','專注模式','只有高置信度重要訊息能立即顯示',s.focus_mode)}${settingSwitch('shadow_mode','Shadow Mode','只記錄建議，不主動浮出提醒',s.shadow_mode)}<div class="setting-row"><div><strong>安靜時段</strong><small>一般訊息會改進摘要</small></div><span><input type="time" data-setting="quiet_start" value="${esc(s.quiet_start)}"> — <input type="time" data-setting="quiet_end" value="${esc(s.quiet_end)}"></span></div></section>
    <section class="settings-section"><h2>本機模型</h2><p>模型失效時，事件仍會保存並使用安全規則基線。</p><div class="setting-row"><div><strong>模型後端</strong><small>${esc(state.model.id || '')}</small></div><span class="health-badge">${esc(state.model.backend || 'rule')}</span></div><div class="setting-row"><div><strong>GPU 常駐</strong><small>暫停時事件會留在 queue</small></div><select data-setting="model_residency"><option value="always_on" ${s.model_residency==='always_on'?'selected':''}>Always on</option><option value="auto_sleep" ${s.model_residency==='auto_sleep'?'selected':''}>Auto sleep</option><option value="paused" ${s.model_residency==='paused'?'selected':''}>Paused</option></select></div></section>
    <section class="settings-section"><h2>外觀與協助工具</h2><p>支援系統主題、鍵盤操作、螢幕閱讀器與 reduced motion。</p><div class="setting-row"><div><strong>主題</strong><small>跟隨系統或固定顯示</small></div><select data-setting="theme"><option value="system" ${s.theme==='system'?'selected':''}>跟隨系統</option><option value="light" ${s.theme==='light'?'selected':''}>淺色</option><option value="dark" ${s.theme==='dark'?'selected':''}>深色</option></select></div></section>
    <section class="settings-section"><h2>資料與隱私</h2><p>匯出預設不含 raw message；刪除會清掉訊息、卡片、草稿與提醒。</p><div class="setting-row"><div><strong>匿名匯出</strong><small>設定、規則與最小化回饋</small></div><button class="button secondary" id="exportData">${icon('download')}匯出</button></div><div class="setting-row"><div><strong>刪除私人資料</strong><small>此操作無法復原</small></div><button class="button danger" id="deleteData">刪除…</button></div></section>
  </div></div>`;
  $$('[data-setting]').forEach(control => control.addEventListener('change', async () => { const value = control.type === 'checkbox' ? control.checked : control.value; await updateSetting(control.dataset.setting, value); }));
  $('#exportData').addEventListener('click', exportData); $('#deleteData').addEventListener('click', deleteDataModal);
}

async function updateSetting(key, value) {
  try { state.settings = await api('/settings',{method:'PATCH',body:JSON.stringify({[key]:value})}); if (key === 'theme') applyTheme(); if (key === 'focus_mode') $('#focusToggle').checked = value; toast('設定已儲存'); } catch (error) { toast(error.message,'error'); }
}

async function exportData() {
  const data = await api('/privacy/export'); const url = URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
  const link = document.createElement('a'); link.href=url; link.download=`signaldesk-export-${new Date().toISOString().slice(0,10)}.json`; link.click(); URL.revokeObjectURL(url); toast('匿名匯出已下載');
}

function deleteDataModal() {
  showModal('刪除所有私人資料', `<p>這會刪除訊息事件、摘要、卡片、草稿、提醒與 feedback。設定與規則會保留。</p><label for="deletePhrase">輸入 DELETE MY SIGNALDESK DATA 以確認</label><input id="deletePhrase" autocomplete="off">`, [
    {label:'取消',onClick:closeModal},{label:'永久刪除',className:'danger',onClick:async()=>{try{await api('/privacy/delete',{method:'POST',body:JSON.stringify({confirmation:$('#deletePhrase').value})});closeModal();toast('私人資料已刪除');await changeView('now');}catch(error){toast(error.message,'error');}}},
  ]);
}

function renderGlance() {
  const cards = state.cards.filter(c => ['urgent','high'].includes(c.priority)).slice(0,3);
  $('#glanceCards').innerHTML = cards.length ? cards.map(card => { const [letter] = sourceMeta(card.source); return `<div class="glance-card" data-glance-card="${esc(card.card_id)}"><span class="source-icon ${esc(card.source)}">${letter}</span><div><strong>${esc(card.sender || card.title)}</strong><small>${esc(card.summary)}</small></div><time>${timeAgo(card.updated_at)}</time></div>`; }).join('') : '<div class="list-empty" style="padding:24px"><strong>目前沒有重要訊息</strong></div>';
  $$('[data-glance-card]').forEach(item => item.addEventListener('click', async () => { $('#glancePanel').hidden=true; $('#orb').setAttribute('aria-expanded','false'); await changeView('now'); await selectCard(item.dataset.glanceCard); }));
}

async function seedDemo() {
  try { await api('/demo/seed',{method:'POST'}); state.settings.onboarding_complete=true; $('#onboarding').hidden=true; toast('示範資料已載入'); await changeView('now'); } catch(error) { toast(error.message,'error'); }
}

const onboardingSteps = [
  ['少一點打斷，<br>多一點真正重要的事。','SignalDesk 在本機整理 Gmail 與 Windows 通知預覽，只在值得你注意時出現。','開始設定'],
  ['內容留在本機，<br>權限保持最小。','Gmail 使用官方 OAuth；個人 LINE 與 Messenger 只讀取 Windows 實際顯示的通知預覽。','下一步'],
  ['先觀察七天，<br>再決定怎麼提醒。','Shadow Mode 預設開啟。SignalDesk 會先記錄建議，等你驗證後才主動打斷。','下一步'],
  ['準備好了。<br>你的注意力由你決定。','隨時可在設定中暫停模型、調整安靜時段、匯出規則或刪除私人資料。','進入 SignalDesk'],
];
let onboardingIndex = 0;
async function nextOnboarding() {
  if (onboardingIndex < onboardingSteps.length - 1) { onboardingIndex++; renderOnboarding(); return; }
  state.settings = await api('/settings',{method:'PATCH',body:JSON.stringify({onboarding_complete:true})}); $('#onboarding').hidden=true; toast('設定完成，歡迎使用 SignalDesk');
}
function renderOnboarding() {
  const [title,body,button] = onboardingSteps[onboardingIndex]; $('#onboardingTitle').innerHTML=title; $('#onboardingBody').textContent=body; $('#nextOnboarding').innerHTML=`${button} ${icon('arrow')}`;
  $$('.step-dots i').forEach((dot,index)=>dot.classList.toggle('active',index===onboardingIndex));
}

function applyTheme() {
  const requested = state.settings.theme || 'system';
  const theme = requested === 'system' ? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : requested;
  document.documentElement.dataset.theme = theme; $('#themeToggle').innerHTML = icon(theme === 'dark' ? 'sun' : 'moon');
}

function connectStream() {
  const stream = new EventSource('/api/v1/events/stream', {withCredentials:true});
  ['card_updated','settings_updated','connector_health','data_deleted'].forEach(name => stream.addEventListener(name, () => { clearTimeout(state.refreshTimer); state.refreshTimer=setTimeout(async()=>{const data=await api('/bootstrap');Object.assign(state,{counts:data.counts,settings:data.settings,connectors:data.connectors});renderCounts();if(!['digest','sources','rules','settings'].includes(state.view))await loadCards({keepSelection:true});},350); }));
  stream.addEventListener('reminder_due', event => { const data=JSON.parse(event.data); toast(`提醒：${data.payload?.summary || '有一則訊息需要處理'}`); });
  stream.onerror = () => console.debug('SignalDesk live stream reconnecting');
}

function bindEvents() {
  hydrateIcons();
  $$('.nav-item').forEach(item => item.addEventListener('click', () => changeView(item.dataset.view)));
  $$('[data-go]').forEach(item => item.addEventListener('click', () => changeView(item.dataset.go)));
  $('#mobileMenu').addEventListener('click', () => $('#appShell').classList.toggle('menu-open'));
  $('#globalSearch').addEventListener('input', e => { state.search=e.target.value; clearTimeout(state.refreshTimer); state.refreshTimer=setTimeout(()=>{ if (!['digest','sources','rules','settings'].includes(state.view)) loadCards(); },250); });
  document.addEventListener('keydown', e => { if ((e.ctrlKey||e.metaKey) && e.key.toLowerCase()==='k') {e.preventDefault();$('#globalSearch').focus();} if(e.key==='Escape'){closeModal();$('#glancePanel').hidden=true;} });
  $$('.filter-button').forEach(button => button.addEventListener('click', () => { state.priority=button.dataset.priority; $$('.filter-button').forEach(b=>b.classList.toggle('active',b===button)); loadCards(); }));
  $('#sourceFilter').addEventListener('change', e => {state.source=e.target.value;loadCards();});
  $('#focusToggle').addEventListener('change', e => updateSetting('focus_mode',e.target.checked));
  $('#themeToggle').addEventListener('click', () => updateSetting('theme',document.documentElement.dataset.theme==='dark'?'light':'dark'));
  $('#orb').addEventListener('click', () => {const panel=$('#glancePanel');panel.hidden=!panel.hidden;$('#orb').setAttribute('aria-expanded',String(!panel.hidden));});
  $('#closeGlance').addEventListener('click',()=>{$('#glancePanel').hidden=true;$('#orb').setAttribute('aria-expanded','false');});
  $('#openCenter').addEventListener('click',()=>{$('#glancePanel').hidden=true;changeView('now');});
  $('#modalClose').addEventListener('click',closeModal); $('#modalBackdrop').addEventListener('click',e=>{if(e.target===e.currentTarget)closeModal();});
  $('#seedDemo').addEventListener('click',seedDemo); $('#nextOnboarding').addEventListener('click',nextOnboarding);
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{if(state.settings.theme==='system')applyTheme();});
}

bindEvents();
bootstrap();

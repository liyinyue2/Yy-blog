/* 我的空间（space.html）—— 个人区单页应用。
   登录复用 JWT 双令牌；各面板数据全部来自既有 API，零重复接口。 */
(() => {
  const $ = id => document.getElementById(id);
  const escapeHtml = v => String(v ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  const apiError = d => (typeof d?.error === 'string' && d.error) || (typeof d?.detail === 'string' && d.detail) || '操作失败';
  const fmtSize = n => { n = +n || 0; return n >= 1048576 ? (n / 1048576).toFixed(1) + ' MB' : n >= 1024 ? (n / 1024).toFixed(1) + ' KB' : n + ' B'; };
  const fmtDur = s => { s = Math.round(+s || 0); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };
  const todayStr = () => new Date().toISOString().slice(0, 10);

  let access = sessionStorage.getItem('admin-access') || '';
  let refresh = sessionStorage.getItem('admin-refresh') || '';

  const api = async (path, options = {}) => {
    const doFetch = () => fetch(path, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...(access ? { Authorization: `Bearer ${access}` } : {}), ...(options.headers || {}) }
    }).then(async res => ({ ok: res.ok, status: res.status, data: await res.json().catch(() => ({})) }));
    let res = await doFetch();
    if (res.status === 401 && refresh && !path.startsWith('/api/auth/')) {
      const r = await fetch('/api/auth/refresh', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh })
      }).then(x => x.json()).catch(() => ({}));
      if (r.access_token) {
        access = r.access_token; refresh = r.refresh_token;
        sessionStorage.setItem('admin-access', access);
        sessionStorage.setItem('admin-refresh', refresh);
        res = await doFetch();
      }
    }
    return res;
  };
  const authedFetch = async (path, options = {}) => {
    const doFetch = () => fetch(path, { ...options, headers: { ...(access ? { Authorization: `Bearer ${access}` } : {}), ...(options.headers || {}) } });
    let res = await doFetch();
    if (res.status === 401 && refresh && !path.startsWith('/api/auth/')) {
      const r = await fetch('/api/auth/refresh', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh })
      }).then(x => x.json()).catch(() => ({}));
      if (r.access_token) {
        access = r.access_token; refresh = r.refresh_token;
        sessionStorage.setItem('admin-access', access);
        sessionStorage.setItem('admin-refresh', refresh);
        res = await doFetch();
      }
    }
    return res;
  };

  /* ---------- 登录门 ---------- */
  const gate = $('space-gate'), shell = $('space-shell');
  const doLogin = async () => {
    const username = $('g-user').value.trim(), password = $('g-pass').value;
    if (!username || !password) { $('g-note').textContent = '请输入用户名和密码。'; return; }
    const res = await fetch('/api/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    }).then(r => r.json()).catch(() => ({}));
    if (res.access_token) {
      access = res.access_token; refresh = res.refresh_token;
      sessionStorage.setItem('admin-access', access);
      sessionStorage.setItem('admin-refresh', refresh);
      gate.classList.add('hidden'); shell.classList.remove('hidden');
      boot();
    } else {
      $('g-note').textContent = apiError(res);
    }
  };
  $('g-submit').addEventListener('click', doLogin);
  $('g-pass').addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); });
  $('space-logout').addEventListener('click', () => {
    sessionStorage.removeItem('admin-access'); sessionStorage.removeItem('admin-refresh');
    location.reload();
  });

  /* ---------- 面板路由 ---------- */
  const PANELS = ['overview', 'notes', 'cloud', 'tools', 'music', 'ai'];
  const loaded = {};
  const showPanel = name => {
    if (!PANELS.includes(name)) name = 'overview';
    document.querySelectorAll('.space-content [data-panel]').forEach(s =>
      s.classList.toggle('hidden', s.dataset.panel !== name));
    document.querySelectorAll('.rail-btn').forEach(b =>
      b.classList.toggle('active', b.dataset.nav === name));
    if (!loaded[name]) { loaded[name] = true; loadPanel(name); }
  };
  document.querySelectorAll('.rail-btn').forEach(b =>
    b.addEventListener('click', () => { location.hash = b.dataset.nav; }));
  window.addEventListener('hashchange', () => showPanel(location.hash.slice(1)));

  const loadPanel = name => {
    if (name === 'overview') loadOverview();
    else if (name === 'notes') loadNotes();
    else if (name === 'cloud') loadCloud();
    else if (name === 'music') loadMusic();
    // tools / ai 无需远程数据
  };

  /* ---------- 概览 ---------- */
  const renderTodos = (items) => {
    const box = $('ov-todo-list');
    const PRIO = { 1: 'prio-1', 2: 'prio-2' };
    box.innerHTML = items.length ? items.map(t => {
      const overdue = t.due && t.due < todayStr() && !t.done;
      return `<div class="todo-row${t.done ? ' done' : ''}">
        ${t.priority ? `<span class="prio-dot ${PRIO[t.priority] || ''}" title="${t.priority === 2 ? '紧急' : '重要'}"></span>` : ''}
        <input type="checkbox" data-td-check="${t.id}" ${t.done ? 'checked' : ''} />
        <span class="todo-text">${escapeHtml(t.content)}</span>
        ${t.due ? `<span class="todo-due${overdue ? ' overdue' : ''}">${overdue ? '已逾期 ' : ''}${escapeHtml(t.due)}</span>` : ''}
        <button class="icon-btn danger" type="button" data-td-del="${t.id}" aria-label="删除"><svg class="ic"><use href="/icons.svg#i-trash"/></svg></button>
      </div>`;
    }).join('') : '<p class="tool-note">没有待办，享受当下。</p>';
  };
  const TODOS_CACHE = { items: [] };
  const loadTodos = async () => {
    const res = await api('/api/workspace/todos?limit=50');
    if (!res.ok) return;
    TODOS_CACHE.items = res.data.items || [];
    renderTodos(TODOS_CACHE.items);
  };
  const addTodo = async () => {
    const content = $('ov-todo-input').value.trim();
    if (!content) return;
    const res = await api('/api/workspace/todos', {
      method: 'POST',
      body: JSON.stringify({ content, priority: +$('ov-todo-priority').value || 0, due: $('ov-todo-due').value || '' })
    });
    if (res.ok) { $('ov-todo-input').value = ''; loadTodos(); }
  };
  $('ov-todo-add').addEventListener('click', addTodo);
  $('ov-todo-input').addEventListener('keydown', e => { if (e.key === 'Enter') addTodo(); });
  $('ov-todo-list').addEventListener('click', async e => {
    const chk = e.target.closest('[data-td-check]');
    const del = e.target.closest('[data-td-del]');
    if (chk) {
      const t = TODOS_CACHE.items.find(x => x.id === +chk.dataset.tdCheck);
      if (!t) return;
      await api('/api/workspace/todos/' + t.id, {
        method: 'PUT',
        body: JSON.stringify({ content: t.content, done: chk.checked, due: t.due || '', priority: t.priority || 0 })
      });
      loadTodos();
    }
    if (del) {
      await api('/api/workspace/todos/' + del.dataset.tdDel, { method: 'DELETE' });
      loadTodos();
    }
  });

  const loadOverview = async () => {
    const h = new Date().getHours();
    $('ov-greeting').textContent = (h < 6 ? '夜深了' : h < 12 ? '早上好' : h < 14 ? '中午好' : h < 18 ? '下午好' : '晚上好') + '，YY。';
    $('ov-date').textContent = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' });
    const [stats, notes, files, tracks, pomodoro] = await Promise.all([
      api('/api/stats'), api('/api/workspace/notes?limit=1'),
      api('/api/cloud/files?limit=1'), api('/api/admin/music/tracks?limit=1'),
      api('/api/space/pomodoro?limit=1')
    ]);
    if (!stats.ok) return;
    const tiles = [
      ['文章', stats.data.articles], ['留言', stats.data.messages],
      ['总阅读', stats.data.views],
      ['笔记', notes.ok ? notes.data.total : '—'],
      ['文件', files.ok ? (Array.isArray(files.data) ? files.data.length : '—') : '—'],
      ['曲目', tracks.ok ? (Array.isArray(tracks.data) ? tracks.data.length : '—') : '—']
    ];
    if (pomodoro.ok && pomodoro.data.today) tiles.push(['今日番茄', pomodoro.data.today]);
    $('ov-stats').innerHTML = tiles.map(([label, n]) =>
      `<div class="stat-tile"><b>${n}</b><span>${label}</span></div>`).join('');
    loadTodos();
    if (notes.ok && notes.data.items?.length) {
      $('ov-notes').innerHTML = notes.data.items.slice(0, 3).map(n => `
        <div class="note-item" data-open-note="${n.id}">
          <b>${escapeHtml(n.title || '(无标题)')}</b><span>${escapeHtml(n.updated_at)}</span>
        </div>`).join('');
    } else {
      $('ov-notes').innerHTML = '<p class="tool-note">还没有笔记。</p>';
    }
  };
  $('ov-notes').addEventListener('click', e => {
    const item = e.target.closest('[data-open-note]');
    if (!item) return;
    location.hash = 'notes';
    showPanel('notes');
    setTimeout(() => openNote(+item.dataset.openNote), 60);
  });

  /* ---------- 知识笔记 ---------- */
  let notesCache = [];
  let editingNoteId = null;
  const renderNotesList = (filter = '') => {
    const list = filter ? notesCache.filter(n =>
      (n.title || '').includes(filter) || (n.content || '').includes(filter)) : notesCache;
    $('notes-list').innerHTML = list.length ? list.map(n => `
      <div class="note-item${editingNoteId === n.id ? ' active' : ''}" data-note-id="${n.id}">
        <b>${escapeHtml(n.title || '(无标题)')}</b><span>${escapeHtml(n.updated_at)}</span>
      </div>`).join('') : '<p class="tool-note">没有笔记。右侧写第一篇。</p>';
  };
  const loadNotes = async () => {
    const res = await api('/api/workspace/notes?limit=100');
    if (!res.ok) return;
    notesCache = res.data.items || [];
    renderNotesList();
    if (!editingNoteId && notesCache.length) openNote(notesCache[0].id);
  };
  const openNote = id => {
    const n = notesCache.find(x => x.id === id);
    if (!n) return;
    editingNoteId = id;
    $('ne-title').value = n.title || '';
    $('ne-content').value = stripHtml(n.content || '');
    $('ne-note').textContent = '';
    renderNotesList();
  };
  const stripHtml = html => {
    const d = document.createElement('div');
    d.innerHTML = html;
    return d.textContent || '';
  };
  $('notes-list').addEventListener('click', e => {
    const item = e.target.closest('[data-note-id]');
    if (item) openNote(+item.dataset.noteId);
  });
  $('ne-save').addEventListener('click', async () => {
    const payload = { title: $('ne-title').value.trim(), content: $('ne-content').value };
    const res = editingNoteId
      ? await api('/api/workspace/notes/' + editingNoteId, { method: 'PUT', body: JSON.stringify(payload) })
      : await api('/api/workspace/notes', { method: 'POST', body: JSON.stringify(payload) });
    $('ne-note').textContent = res.ok ? '已保存。' : apiError(res.data);
    if (res.ok) { editingNoteId = res.data.id || editingNoteId; loadNotes(); }
  });
  $('ne-new').addEventListener('click', () => {
    editingNoteId = null;
    $('ne-title').value = ''; $('ne-content').value = '';
    renderNotesList(); $('ne-title').focus();
  });
  $('ne-delete').addEventListener('click', async () => {
    if (!editingNoteId) { $('ne-note').textContent = '当前没有选中的笔记。'; return; }
    if (!confirm('确定删除这篇笔记？此操作不可恢复。')) return;
    const res = await api('/api/workspace/notes/' + editingNoteId, { method: 'DELETE' });
    if (res.ok) { editingNoteId = null; $('ne-title').value = ''; $('ne-content').value = ''; loadNotes(); }
  });

  /* ---------- 云盘 ---------- */
  let cloudCache = [];
  let cloudQuery = '';
  const renderCloud = () => {
    const q = cloudQuery.toLowerCase();
    const list = q ? cloudCache.filter(f => f.original_name.toLowerCase().includes(q)) : cloudCache;
    $('cl-list').innerHTML = list.length ? list.map(f => `
      <div class="file-row">
        <button class="icon-btn star-btn${f.is_starred ? ' active' : ''}" type="button" data-f-star="${f.id}" aria-label="收藏"><svg class="ic"><use href="/icons.svg#i-star"/></svg></button>
        <span class="file-name">${escapeHtml(f.original_name)}</span>
        <span class="file-meta">${fmtSize(f.size)} · ${escapeHtml(f.created_at)}</span>
        <button class="icon-btn" type="button" data-f-dl="${f.id}" aria-label="下载"><svg class="ic"><use href="/icons.svg#i-download"/></svg></button>
        <button class="icon-btn" type="button" data-f-preview="${f.id}" aria-label="预览"><svg class="ic"><use href="/icons.svg#i-search"/></svg></button>
        <button class="icon-btn danger" type="button" data-f-del="${f.id}" aria-label="删除"><svg class="ic"><use href="/icons.svg#i-trash"/></svg></button>
      </div>`).join('') : '<p class="tool-note">没有匹配的文件。</p>';
  };
  const loadCloud = async () => {
    const res = await api('/api/cloud/files?limit=100');
    if (!res.ok) return;
    cloudCache = Array.isArray(res.data) ? res.data : [];
    renderCloud();
  };
  $('cl-upload').addEventListener('click', () => $('cl-file').click());
  $('cl-file').addEventListener('change', async () => {
    const file = $('cl-file').files[0];
    if (!file) return;
    if (file.size > 20 * 1024 * 1024) { $('cl-note').textContent = '文件超过 20MB 限制。'; return; }
    $('cl-upload').disabled = true;
    $('cl-note').textContent = `正在上传「${file.name}」…`;
    try {
      const fd = new FormData(); fd.append('file', file);
      const res = await authedFetch('/api/admin/cloud/upload', { method: 'POST', body: fd });
      const data = await res.json().catch(() => ({}));
      $('cl-note').textContent = res.ok ? '上传成功。' : apiError(data);
      if (res.ok) loadCloud();
    } finally { $('cl-upload').disabled = false; $('cl-file').value = ''; }
  });
  $('cl-search').addEventListener('input', () => { cloudQuery = $('cl-search').value.trim(); renderCloud(); });
  $('cl-list').addEventListener('click', async e => {
    const dl = e.target.closest('[data-f-dl]');
    const del = e.target.closest('[data-f-del]');
    const star = e.target.closest('[data-f-star]');
    const prev = e.target.closest('[data-f-preview]');
    if (dl) {
      try {
        const r = await authedFetch('/api/cloud/download/' + dl.dataset.fDl);
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const blob = await r.blob();
        const dispo = r.headers.get('content-disposition') || '';
        let name = 'download';
        const m = dispo.match(/filename\*=UTF-8''([^;]+)/);
        if (m) name = decodeURIComponent(m[1]);
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = name; a.click();
        URL.revokeObjectURL(url);
      } catch (err) { $('cl-note').textContent = '下载失败：' + err.message; }
    }
    if (del) {
      if (!confirm('确定删除这个文件？此操作不可恢复。')) return;
      await api('/api/admin/cloud/files/' + del.dataset.fDel, { method: 'DELETE' });
      loadCloud();
    }
    if (star) {
      const f = cloudCache.find(x => x.id === +star.dataset.fStar);
      if (!f) return;
      const res = await api('/api/admin/cloud/files/' + f.id, {
        method: 'PATCH', body: JSON.stringify({ is_starred: !f.is_starred })
      });
      if (res.ok) { f.is_starred = res.data.is_starred ? 1 : 0; renderCloud(); }
    }
    if (prev) previewFile(+prev.dataset.fPreview);
  });
  const previewFile = async id => {
    const f = cloudCache.find(x => x.id === id);
    if (!f) return;
    const ext = (f.original_name || '').toLowerCase().rsplit('.', 1).pop();
    const imgExts = ['png', 'jpg', 'jpeg', 'webp', 'gif'];
    const textExts = ['txt', 'md'];
    let html;
    try {
      const r = await authedFetch('/api/cloud/download/' + id);
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const blob = await r.blob();
      if (imgExts.includes(ext)) {
        const url = URL.createObjectURL(blob);
        html = `<img src="${url}" alt="${escapeHtml(f.original_name)}" style="max-width:100%;max-height:60vh;border-radius:12px;" />`;
      } else if (textExts.includes(ext)) {
        const text = (await blob.text()).slice(0, 5000);
        html = `<pre style="white-space:pre-wrap;font-size:13px;line-height:1.7;margin:0;">${escapeHtml(text)}</pre>`;
      } else {
        html = `<p class="tool-note">该类型（${escapeHtml(ext || '未知')}）暂不支持预览，请下载查看。</p>`;
      }
    } catch (err) { html = `<p class="tool-note">预览失败：${escapeHtml(err.message)}</p>`; }
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;z-index:80;background:rgba(0,0,0,.45);display:flex;align-items:center;justify-content:center;padding:24px;';
    const panel = document.createElement('div');
    panel.className = 'glass-card';
    panel.style.cssText = 'max-width:720px;width:100%;max-height:80vh;overflow:auto;background:var(--glass-fallback,#fff);';
    panel.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;"><b>${escapeHtml(f.original_name)}</b><button class="glass-button" type="button">关闭</button></div>${html}`;
    overlay.appendChild(panel);
    overlay.addEventListener('click', e => { if (e.target === overlay || e.target.closest('button')) overlay.remove(); });
    document.body.appendChild(overlay);
  };

  /* ---------- 效率工具 ---------- */
  // 番茄钟：localStorage 保活 + 完成后服务端落库
  const POMO_KEY = 'space-pomodoro';
  const RING_LEN = 2 * Math.PI * 66;
  let pomo = { label: '', minutes: 25, remain: 25 * 60, running: false, endAt: 0, saved: false };
  try { pomo = { ...pomo, ...(JSON.parse(localStorage.getItem(POMO_KEY) || '{}')) }; } catch { /* 忽略损坏数据 */ }
  let pomoTimer = null;
  const pomoPaint = () => {
    const m = Math.floor(pomo.remain / 60), s = pomo.remain % 60;
    $('pomo-display').textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    const total = pomo.minutes * 60;
    const ratio = total > 0 ? pomo.remain / total : 0;
    $('pomo-arc').style.strokeDashoffset = String(RING_LEN * (1 - ratio));
    $('pomo-state').textContent = pomo.running ? '专注中…' : (pomo.remain < total ? '已暂停' : '准备开始');
    $('pomo-start').textContent = pomo.running ? '暂停' : (pomo.remain < total ? '继续' : '开始');
  };
  const pomoPersist = () => {
    try { localStorage.setItem(POMO_KEY, JSON.stringify(pomo)); } catch { /* 忽略 */ }
  };
  const pomoTick = () => {
    if (!pomo.running) return;
    pomo.remain = Math.max(0, Math.round((pomo.endAt - Date.now()) / 1000));
    pomoPaint(); pomoPersist();
    if (pomo.remain <= 0) pomoFinish(true);
  };
  const pomoStart = async () => {
    if (pomo.running) {              // 暂停
      pomo.running = false;
      clearInterval(pomoTimer);
      pomoPaint(); pomoPersist();
      return;
    }
    if (pomo.remain <= 0) { pomoReset(); }
    pomo.running = true;
    pomo.endAt = Date.now() + pomo.remain * 1000;
    pomo.saved = false;
    $('pomo-note').textContent = '';
    clearInterval(pomoTimer);
    pomoTimer = setInterval(pomoTick, 500);
    pomoPaint(); pomoPersist();
  };
  const pomoReset = () => {
    pomo.running = false;
    clearInterval(pomoTimer);
    pomo.minutes = +$('pomo-minutes').value || 25;
    pomo.remain = pomo.minutes * 60;
    pomoPaint(); pomoPersist();
  };
  const pomoFinish = async (completed) => {
    pomo.running = false;
    clearInterval(pomoTimer);
    if (completed && !pomo.saved) {
      pomo.saved = true;
      const res = await api('/api/space/pomodoro', {
        method: 'POST',
        body: JSON.stringify({ label: pomo.label || $('pomo-label').value.trim(), minutes: pomo.minutes, completed: true })
      });
      $('pomo-note').textContent = res.ok ? `专注完成！休息一下。` : '专注完成（服务端记录失败）。';
      loadPomodoroToday();
    }
    pomo.minutes = +$('pomo-minutes').value || 25;
    pomo.remain = pomo.minutes * 60;
    pomoPaint(); pomoPersist();
  };
  const loadPomodoroToday = async () => {
    const res = await api('/api/space/pomodoro?limit=5');
    if (!res.ok) return;
    $('pomo-today').textContent = `今日已完成 ${res.data.today} 个番茄（累计 ${res.data.total} 个）。`;
  };
  $('pomo-start').addEventListener('click', pomoStart);
  $('pomo-reset').addEventListener('click', pomoReset);
  $('pomo-minutes').addEventListener('change', () => { if (!pomo.running) pomoReset(); });
  document.addEventListener('visibilitychange', () => { if (!document.hidden && pomo.running) pomoTick(); });
  pomo.minutes = pomo.minutes || +$('pomo-minutes').value;
  if (pomo.running) {
    pomo.endAt = pomo.endAt || Date.now();
    pomoTimer = setInterval(pomoTick, 500);
  }
  pomoPaint(); loadPomodoroToday();

  // JSON 工具
  $('json-format').addEventListener('click', () => {
    try {
      const obj = JSON.parse($('json-in').value);
      $('json-out').textContent = JSON.stringify(obj, null, 2);
      $('json-note').textContent = 'JSON 合法，已格式化。';
    } catch (err) {
      $('json-out').textContent = '';
      $('json-note').textContent = '解析失败：' + err.message;
    }
  });
  $('json-minify').addEventListener('click', () => {
    try {
      const obj = JSON.parse($('json-in').value);
      $('json-out').textContent = JSON.stringify(obj);
      $('json-note').textContent = 'JSON 合法，已压缩。';
    } catch (err) {
      $('json-out').textContent = '';
      $('json-note').textContent = '解析失败：' + err.message;
    }
  });
  $('json-copy').addEventListener('click', () => {
    const text = $('json-out').textContent;
    if (text) navigator.clipboard?.writeText(text);
  });

  // 文本工具
  const textOut = fn => {
    const v = $('text-in').value;
    const r = fn(v);
    $('text-out').textContent = r.text ?? r;
    if (r.note) $('text-out').textContent = `${r.note}\n----------\n${r.text ?? ''}`;
  };
  $('text-count').addEventListener('click', () => {
    const v = $('text-in').value;
    const chars = [...v].length;
    const cjk = (v.match(/[\u4e00-\u9fff]/g) || []).length;
    const words = (v.match(/[A-Za-z0-9_'-]+/g) || []).length;
    const lines = v ? v.split(/\n/).length : 0;
    $('text-out').textContent = `字符 ${chars} ｜ 汉字 ${cjk} ｜ 英文单词 ${words} ｜ 行数 ${lines}`;
  });
  $('text-upper').addEventListener('click', () => textOut(v => v.toUpperCase()));
  $('text-lower').addEventListener('click', () => textOut(v => v.toLowerCase()));
  $('text-trim').addEventListener('click', () => textOut(v => v.split(/\n/).filter(l => l.trim()).join('\n')));
  $('text-b64e').addEventListener('click', () => textOut(v => {
    try { return { text: btoa(unescape(encodeURIComponent(v))), note: 'Base64 编码' }; }
    catch { return { text: '', note: '编码失败' }; }
  }));
  $('text-b64d').addEventListener('click', () => textOut(v => {
    try { return { text: decodeURIComponent(escape(atob(v.trim()))), note: 'Base64 解码' }; }
    catch { return { text: '', note: '不是合法的 Base64' }; }
  }));

  // 网络信息
  $('net-check').addEventListener('click', async () => {
    $('net-out').textContent = '查询中…';
    const res = await api('/api/space/netinfo');
    if (!res.ok) { $('net-out').textContent = '查询失败。'; return; }
    const ua = res.data.headers['user-agent'] || '';
    $('net-out').textContent =
      `出口 IP：${res.data.ip}\n服务器时间：${res.data.time}\n浏览器：${ua}`;
  });

  /* ---------- 音乐库 + 播放条 ---------- */
  let tracksCache = [];
  let playIndex = -1;
  const audio = $('np-audio');
  const loadMusic = async () => {
    const res = await api('/api/admin/music/tracks?limit=200');
    if (!res.ok) return;
    tracksCache = res.data;
    renderTracks();
  };
  const renderTracks = () => {
    $('music-list').innerHTML = tracksCache.length ? tracksCache.map((t, i) => `
      <div class="track-row${i === playIndex ? ' playing' : ''}">
        <button class="icon-btn" type="button" data-t-play="${i}" aria-label="播放"><svg class="ic"><use href="/icons.svg#i-play"/></svg></button>
        <span class="track-title">${escapeHtml(t.title || '(未知标题)')}</span>
        <span class="track-meta">${escapeHtml(t.artist || '—')}${t.album ? ' · ' + escapeHtml(t.album) : ''} · ${fmtDur(t.duration)}</span>
        ${t.visibility === 'private' ? '<span class="badge">私密</span>' : ''}
      </div>`).join('') : '<p class="tool-note">音乐库还是空的。去后台上传第一首。</p>';
  };
  const playTrack = i => {
    if (!tracksCache.length) return;
    playIndex = (i + tracksCache.length) % tracksCache.length;
    const t = tracksCache[playIndex];
    audio.src = `/api/public/music/stream/${t.id}`;
    audio.play().catch(() => {});
    $('np-title').textContent = `${t.title || '未知标题'}${t.artist ? ' — ' + t.artist : ''}`;
    $('space-player').classList.remove('hidden');
    renderTracks();
  };
  $('music-list').addEventListener('click', e => {
    const btn = e.target.closest('[data-t-play]');
    if (btn) playTrack(+btn.dataset.tPlay);
  });
  $('np-toggle').addEventListener('click', () => {
    if (!audio.src) { if (tracksCache.length) playTrack(0); return; }
    if (audio.paused) audio.play().catch(() => {});
    else audio.pause();
  });
  $('np-prev').addEventListener('click', () => playTrack(playIndex - 1));
  $('np-next').addEventListener('click', () => playTrack(playIndex + 1));
  audio.addEventListener('play', () => { $('np-toggle-use').setAttribute('href', '/icons.svg#i-pause'); });
  audio.addEventListener('pause', () => { $('np-toggle-use').setAttribute('href', '/icons.svg#i-play'); });
  audio.addEventListener('ended', () => playTrack(playIndex + 1));
  audio.addEventListener('timeupdate', () => {
    if (audio.duration) {
      $('np-seek').value = String((audio.currentTime / audio.duration) * 100);
      $('np-cur').textContent = fmtDur(audio.currentTime);
      $('np-dur').textContent = fmtDur(audio.duration);
    }
  });
  $('np-seek').addEventListener('input', () => {
    if (audio.duration) audio.currentTime = (+$('np-seek').value / 100) * audio.duration;
  });

  /* ---------- 全局搜索 ---------- */
  const searchInput = $('space-search-input');
  const searchBox = $('space-search-results');
  let searchTimer;
  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(async () => {
      const q = searchInput.value.trim();
      if (!q) { searchBox.classList.add('hidden'); return; }
      const res = await api('/api/space/search?q=' + encodeURIComponent(q));
      if (!res.ok) return;
      const { groups } = res.data;
      searchBox.innerHTML = groups.length ? groups.map(g => `
        <div class="sr-group">
          <div class="sr-label">${escapeHtml(g.label)}</div>
          ${g.items.map(it => {
            if (g.type === 'article') return `<a href="${escapeHtml(it.url)}">${escapeHtml(it.title)}</a>`;
            if (g.type === 'project') return `<a href="${escapeHtml(it.url)}">${escapeHtml(it.name)}</a>`;
            if (g.type === 'note') return `<span class="sr-item" data-sr-note="${it.id}">${escapeHtml(it.title)} · ${escapeHtml(it.excerpt || '')}</span>`;
            if (g.type === 'file') return `<span class="sr-item" data-sr-file="${it.id}">${escapeHtml(it.name)} · ${fmtSize(it.size)}</span>`;
            if (g.type === 'track') return `<span class="sr-item" data-sr-track="${it.id}">${escapeHtml(it.title)}${it.artist ? ' — ' + escapeHtml(it.artist) : ''}</span>`;
            if (g.type === 'todo') return `<span class="sr-item">${it.done ? '☑' : '☐'} ${escapeHtml(it.content)}</span>`;
            return '';
          }).join('')}
        </div>`).join('') : '<p class="tool-note">没有匹配结果。</p>';
      searchBox.classList.remove('hidden');
    }, 250);
  });
  document.addEventListener('click', e => {
    if (!searchBox.contains(e.target) && e.target !== searchInput) searchBox.classList.add('hidden');
  });
  searchBox.addEventListener('click', e => {
    const note = e.target.closest('[data-sr-note]');
    if (note) { location.hash = 'notes'; showPanel('notes'); openNote(+note.dataset.srNote); searchBox.classList.add('hidden'); }
    const file = e.target.closest('[data-sr-file]');
    if (file) { location.hash = 'cloud'; showPanel('cloud'); searchBox.classList.add('hidden'); }
    const track = e.target.closest('[data-sr-track]');
    if (track) {
      const idx = tracksCache.findIndex(t => t.id === +track.dataset.srTrack);
      if (idx >= 0) { location.hash = 'music'; showPanel('music'); playTrack(idx); }
      searchBox.classList.add('hidden');
    }
  });

  /* ---------- 启动 ---------- */
  const boot = () => {
    $('space-user').textContent = 'admin';
    showPanel(location.hash.slice(1) || 'overview');
  };
  if (access && refresh) { gate.classList.add('hidden'); shell.classList.remove('hidden'); boot(); }
})();

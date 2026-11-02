(() => {
  const $ = id => document.getElementById(id);
  const escapeHtml = value => String(value ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  const apiError = (data, fallback) => {
    if (typeof data?.error === 'string' && data.error) return data.error;
    if (typeof data?.detail === 'string' && data.detail) return data.detail;
    if (typeof data?.message === 'string' && data.message) return data.message;
    return fallback;
  };
  let access = sessionStorage.getItem('admin-access') || '';
  let refresh = sessionStorage.getItem('admin-refresh') || '';
  let editingSlug = null;
  let editingCategory = null;
  const fmtSize = n => { n = +n || 0; return n >= 1048576 ? (n / 1048576).toFixed(1) + ' MB' : n >= 1024 ? (n / 1024).toFixed(1) + ' KB' : n + ' B'; };
  const fmtDur = s => { s = Math.round(+s || 0); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };
  // 不带 Content-Type 的鉴权请求（multipart 上传 / blob 下载用；浏览器自动设表单边界）
  const authedFetch = async (path, options = {}) => {
    const doFetch = () => fetch(path, {
      ...options,
      headers: { ...(access ? { Authorization: `Bearer ${access}` } : {}), ...(options.headers || {}) }
    });
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

  const api = async (path, options = {}) => {
    const doFetch = () => fetch(path, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...(access ? { Authorization: `Bearer ${access}` } : {}), ...(options.headers || {}) }
    }).then(async res => ({ ok: res.ok, status: res.status, data: await res.json().catch(() => ({})) }));
    let res = await doFetch();
    // access 过期 → 用 refresh 静默续期一次后重试
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

  /* ---------- JWT 登录 ---------- */
  const gate = $('token-gate'), panel = $('admin-panel');
  const doLogin = async () => {
    const username = $('user-input').value.trim();
    const password = $('pass-input').value;
    if (!username || !password) { $('token-note').textContent = '请输入用户名和密码。'; return; }
    const res = await fetch('/api/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    }).then(r => r.json()).catch(() => ({}));
    if (res.access_token) {
      access = res.access_token; refresh = res.refresh_token;
      sessionStorage.setItem('admin-access', access);
      sessionStorage.setItem('admin-refresh', refresh);
      gate.classList.add('hidden'); panel.classList.remove('hidden'); loadAll();
    } else {
      $('token-note').textContent = apiError(res, '登录失败，请重试。');
    }
  };
  $('token-submit').addEventListener('click', doLogin);
  $('pass-input').addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); });

  /* ---------- 面板路由（hash，刷新保持当前面板） ---------- */
  const PANELS = ['workspace', 'cloud', 'music', 'articles', 'categories', 'tags',
                  'messages', 'subscribers', 'settings', 'audit', 'admins'];
  const showPanel = name => {
    if (!PANELS.includes(name)) name = 'workspace';
    document.querySelectorAll('[data-panel]').forEach(s =>
      s.classList.toggle('hidden', s.dataset.panel !== name));
    document.querySelectorAll('[data-panel-link]').forEach(a =>
      a.classList.toggle('active', a.dataset.panelLink === name));
  };
  window.addEventListener('hashchange', () => showPanel(location.hash.slice(1)));
  showPanel(location.hash.slice(1) || 'workspace');

  /* ---------- 数据加载 ---------- */
  const loadAll = async () => {
    const [stats, articles, categories, messages, subscribers, settings] = await Promise.all([
      api('/api/stats'), api('/api/admin/articles'), api('/api/categories'),
      api('/api/admin/messages'), api('/api/admin/subscribers'), api('/api/settings')
    ]);
    if (!stats.ok || !articles.ok) { sessionStorage.removeItem('admin-access'); sessionStorage.removeItem('admin-refresh'); location.reload(); return; }
    const s = stats.data;
    $('admin-stats').innerHTML = [
      ['文章', s.articles], ['分类', s.categories],
      ['留言', s.messages], ['订阅者', s.subscribers], ['总阅读', s.views]
    ].map(([label, n]) => `<div class="stat-card"><b>${n}</b><span>${label}</span></div>`).join('');
    window._categories = categories.data;

    // 文章
    $('f-category').innerHTML = categories.data.map(c => `<option value="${escapeHtml(c.slug)}">${escapeHtml(c.name)}（${c.article_count} 篇）</option>`).join('');
    $('article-rows').innerHTML = articles.data.length ? articles.data.map(a => `
      <tr>
        <td>${escapeHtml(a.title)}<div class="muted">/post-${escapeHtml(a.slug)}.html</div></td>
        <td>${escapeHtml(a.category_name)}</td><td>${escapeHtml(a.date)}</td><td>${a.views}</td>
        <td class="actions">
          <button type="button" data-edit="${escapeHtml(a.slug)}">编辑</button>
          <button type="button" class="danger" data-delete="${escapeHtml(a.slug)}">删除</button>
        </td>
      </tr>`).join('') : '<tr><td colspan="5" class="muted">还没有文章</td></tr>';

    // 分类
    $('category-rows').innerHTML = categories.data.map(c => `
      <tr>
        <td>${escapeHtml(c.name)}</td><td class="muted">${escapeHtml(c.slug)}</td>
        <td class="muted">${escapeHtml(c.description || '')}</td><td>${c.article_count}</td>
        <td class="actions">
          <button type="button" data-edit-cat="${escapeHtml(c.slug)}">编辑</button>
          <button type="button" class="danger" data-del-cat="${escapeHtml(c.slug)}">删除</button>
        </td>
      </tr>`).join('');

    // 留言
    $('message-list-admin').innerHTML = messages.data.length ? messages.data.map(m => `
      <div class="msg-item${m.visible ? '' : ' is-hidden-msg'}">
        <div class="head"><b>${escapeHtml(m.name)}</b><span class="meta">${escapeHtml(m.created_at)}${m.contact ? ' · ' + escapeHtml(m.contact) : ''}</span></div>
        <p>${escapeHtml(m.content)}</p>
        <div class="reply-box">
          <input type="text" data-reply-input="${m.id}" placeholder="写下回复…" value="${escapeHtml(m.reply || '')}" />
          <button type="button" data-send-reply="${m.id}">回复</button>
        </div>
        <div class="ops">
          <button type="button" data-toggle-msg="${m.id}" data-visible="${m.visible}">${m.visible ? '隐藏' : '取消隐藏'}</button>
          <button type="button" class="danger" data-del-msg="${m.id}">删除</button>
          ${m.visible ? '' : '<span class="badge">已隐藏</span>'}
        </div>
      </div>`).join('') : '<p class="list-empty">还没有留言。</p>';

    // 订阅者
    $('subscriber-rows').innerHTML = subscribers.data.length
      ? subscribers.data.map(u => `<tr><td>${u.id}</td><td>${escapeHtml(u.email)}</td><td class="muted">${escapeHtml(u.created_at)}</td></tr>`).join('')
      : '<tr><td colspan="3" class="muted">还没有订阅者</td></tr>';

    // 设置
    for (const [key, value] of Object.entries(settings)) {
      const el = $('s-' + key);
      if (el && document.activeElement !== el) el.value = value;
    }

    // 工作台 / 音乐 / 网盘
    loadWorkspace(); loadMusic(); loadCloud();
  };

  /* ---------- Word / PDF 导入 ---------- */
  $('import-btn').addEventListener('click', () => $('f-import').click());
  $('f-import').addEventListener('change', async () => {
    const file = $('f-import').files[0];
    if (!file) return;
    const note = $('import-note');
    if (file.size > 15 * 1024 * 1024) { note.textContent = '文件超过 15MB 限制。'; return; }
    $('import-btn').disabled = true;
    note.textContent = `正在解析「${file.name}」…`;
    try {
      const dataUrl = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(new Error('读取文件失败'));
        reader.readAsDataURL(file);
      });
      const res = await api('/api/admin/convert', {
        method: 'POST',
        body: JSON.stringify({ filename: file.name, data: dataUrl.split(',')[1] || '' })
      });
      if (res.ok) {
        $('f-title').value = res.data.title;
        $('f-slug').value = '';
        $('f-content').value = res.data.content;
        if (!$('f-date').value.trim()) $('f-date').value = new Date().toISOString().slice(0, 10);
        note.textContent = `导入成功：约 ${res.data.chars} 字，已填入标题、日期与正文。选好分类后点「保存文章」即可发布（slug 会自动生成）。`;
        editingSlug = null;
        $('f-content').scrollIntoView({ behavior: 'smooth', block: 'center' });
      } else {
        note.textContent = apiError(res.data, '导入失败，请检查文件格式。');
      }
    } catch (err) {
      note.textContent = '导入失败：' + (err.message || '未知错误');
    } finally {
      $('import-btn').disabled = false;
      $('f-import').value = '';
    }
  });

  /* ---------- 文章 ---------- */
  $('article-rows').addEventListener('click', async e => {
    const editBtn = e.target.closest('[data-edit]');
    const delBtn = e.target.closest('[data-delete]');
    if (editBtn) {
      const detail = await api('/api/articles/' + encodeURIComponent(editBtn.dataset.edit));
      if (!detail.ok) return;
      const a = detail.data;
      editingSlug = a.slug;
      $('f-slug').value = a.slug; $('f-title').value = a.title;
      $('f-category').value = a.category_slug; $('f-date').value = a.published_at;
      $('f-summary').value = a.summary; $('f-content').value = a.content;
      $('editor-note').textContent = `正在编辑：${a.title}`;
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    if (delBtn) {
      if (!confirm(`确定删除文章「${delBtn.dataset.delete}」？此操作不可恢复。`)) return;
      const res = await api('/api/admin/articles/' + encodeURIComponent(delBtn.dataset.delete), { method: 'DELETE' });
      $('editor-note').textContent = apiError(res.data, res.ok ? '' : '删除失败');
      if (editingSlug === delBtn.dataset.delete) $('f-reset').click();
      loadAll();
    }
  });

  $('f-save').addEventListener('click', async () => {
    const btn = $('f-save');
    btn.disabled = true;
    try {
      const payload = {
        slug: $('f-slug').value.trim(), title: $('f-title').value.trim(),
        category: $('f-category').value, date: $('f-date').value.trim(),
        summary: $('f-summary').value.trim(), content: $('f-content').value
      };
      const res = editingSlug
        ? await api('/api/admin/articles/' + encodeURIComponent(editingSlug), { method: 'PUT', body: JSON.stringify(payload) })
        : await api('/api/admin/articles', { method: 'POST', body: JSON.stringify(payload) });
      $('editor-note').classList.toggle('is-error', !res.ok);
      if (res.ok) {
        const wasNew = !editingSlug;
        $('editor-note').innerHTML = `${escapeHtml(res.data.message)}　<a href="${escapeHtml(res.data.url)}" target="_blank">查看文章 ↗</a>`;
        if (wasNew) $('f-reset').click();
        loadAll();
      } else {
        $('editor-note').textContent = apiError(res.data, '保存失败，请重试。');
      }
    } finally {
      btn.disabled = false;
    }
  });

  $('f-reset').addEventListener('click', () => {
    editingSlug = null;
    ['f-slug', 'f-title', 'f-date', 'f-summary', 'f-content'].forEach(id => { $(id).value = ''; });
    $('editor-note').textContent = '新建模式：填写后点击保存文章。';
  });

  /* ---------- 分类 ---------- */
  $('category-rows').addEventListener('click', async e => {
    const editBtn = e.target.closest('[data-edit-cat]');
    const delBtn = e.target.closest('[data-del-cat]');
    if (editBtn) {
      const c = window._categories.find(x => x.slug === editBtn.dataset.editCat);
      editingCategory = c.slug;
      $('c-slug').value = c.slug; $('c-slug').disabled = true;
      $('c-name').value = c.name; $('c-desc').value = c.description || '';
      $('c-save').textContent = '保存修改';
      $('c-note').textContent = `正在编辑分类：${c.name}`;
    }
    if (delBtn) {
      if (!confirm(`确定删除分类「${delBtn.dataset.delCat}」？`)) return;
      const res = await api('/api/admin/categories/' + encodeURIComponent(delBtn.dataset.delCat), { method: 'DELETE' });
      $('c-note').textContent = apiError(res.data, res.ok ? '' : '删除失败');
      loadAll();
    }
  });

  $('c-save').addEventListener('click', async () => {
    const payload = { name: $('c-name').value.trim(), description: $('c-desc').value.trim() };
    let res;
    if (editingCategory) {
      res = await api('/api/admin/categories/' + encodeURIComponent(editingCategory), { method: 'PUT', body: JSON.stringify(payload) });
    } else {
      payload.slug = $('c-slug').value.trim();
      res = await api('/api/admin/categories', { method: 'POST', body: JSON.stringify(payload) });
    }
    $('c-note').textContent = apiError(res.data, res.ok ? '' : '保存失败');
    if (res.ok) {
      editingCategory = null;
      $('c-slug').disabled = false; $('c-slug').value = ''; $('c-name').value = ''; $('c-desc').value = '';
      $('c-save').textContent = '创建分类';
      loadAll();
    }
  });

  /* ---------- 留言 ---------- */
  $('message-list-admin').addEventListener('click', async e => {
    const replyBtn = e.target.closest('[data-send-reply]');
    const toggleBtn = e.target.closest('[data-toggle-msg]');
    const delBtn = e.target.closest('[data-del-msg]');
    if (replyBtn) {
      const id = replyBtn.dataset.sendReply;
      const input = document.querySelector(`[data-reply-input="${id}"]`);
      const res = await api('/api/admin/messages/' + id, { method: 'PUT', body: JSON.stringify({ reply: input.value }) });
      if (res.ok) loadAll();
    }
    if (toggleBtn) {
      const res = await api('/api/admin/messages/' + toggleBtn.dataset.toggleMsg, {
        method: 'PUT', body: JSON.stringify({ visible: toggleBtn.dataset.visible !== '1' })
      });
      if (res.ok) loadAll();
    }
    if (delBtn) {
      if (!confirm('确定删除这条留言？此操作不可恢复。')) return;
      await api('/api/admin/messages/' + delBtn.dataset.delMsg, { method: 'DELETE' });
      loadAll();
    }
  });

  /* ---------- 站点设置 ---------- */
  $('s-save').addEventListener('click', async () => {
    const keys = ['site_name', 'hero_muted', 'hero_main', 'hero_subline', 'about_intro', 'about_content',
                  'social_github', 'social_wechat', 'social_qq', 'social_douyin'];
    const payload = Object.fromEntries(keys.map(k => [k, $('s-' + k).value]));
    const res = await api('/api/admin/settings', { method: 'PUT', body: JSON.stringify(payload) });
    $('s-note').textContent = apiError(res.data, res.ok ? '' : '保存失败');
  });

  /* ---------- 工作台：笔记 / 待办 / 书签 ---------- */
  let editingNote = null;
  const loadWorkspace = async () => {
    const [notes, todos, bookmarks] = await Promise.all([
      api('/api/workspace/notes?limit=50'), api('/api/workspace/todos?limit=50'), api('/api/workspace/bookmarks?limit=50')
    ]);
    if (!notes.ok || !todos.ok || !bookmarks.ok) return;
    $('note-list').innerHTML = notes.data.items.length ? notes.data.items.map(n => `
      <div class="ws-item">
        <div class="head"><b>${escapeHtml(n.title || '(无标题)')}</b><span class="meta">${escapeHtml(n.updated_at)}</span></div>
        <p>${escapeHtml(n.content)}</p>
        <div class="ops">
          <button type="button" data-edit-note="${n.id}">编辑</button>
          <button type="button" class="danger" data-del-note="${n.id}">删除</button>
        </div>
      </div>`).join('') : '<p class="admin-note">还没有笔记。</p>';
    $('todo-list').innerHTML = todos.data.items.length ? todos.data.items.map(t => `
      <div class="todo-item${t.done ? ' done' : ''}">
        <input type="checkbox" data-todo-check="${t.id}" ${t.done ? 'checked' : ''} />
        <span>${escapeHtml(t.content)}</span>
        <span class="del"><button type="button" data-del-todo="${t.id}">删除</button></span>
      </div>`).join('') : '<p class="admin-note">没有待办。</p>';
    $('bookmark-list').innerHTML = bookmarks.data.items.length ? bookmarks.data.items.map(b => `
      <div class="ws-item">
        <div class="head"><b><a href="${escapeHtml(b.url)}" target="_blank" rel="noopener">${escapeHtml(b.title)}</a></b><span class="meta">${escapeHtml(b.created_at)}</span></div>
        <div class="ops"><button type="button" class="danger" data-del-bm="${b.id}">删除</button></div>
      </div>`).join('') : '<p class="admin-note">没有书签。</p>';
  };

  const resetNoteForm = () => {
    editingNote = null;
    $('n-title').value = ''; $('n-content').value = '';
    $('n-save').textContent = '保存笔记';
  };
  $('n-save').addEventListener('click', async () => {
    const payload = { title: $('n-title').value, content: $('n-content').value };
    const res = editingNote
      ? await api('/api/workspace/notes/' + editingNote, { method: 'PUT', body: JSON.stringify(payload) })
      : await api('/api/workspace/notes', { method: 'POST', body: JSON.stringify(payload) });
    $('n-note').textContent = res.ok ? '已保存。' : apiError(res.data, '保存失败');
    if (res.ok) { resetNoteForm(); loadWorkspace(); }
  });
  $('note-list').addEventListener('click', async e => {
    const editBtn = e.target.closest('[data-edit-note]');
    const delBtn = e.target.closest('[data-del-note]');
    if (editBtn) {
      const notes = await api('/api/workspace/notes?limit=50');
      const n = (notes.data.items || []).find(x => x.id === +editBtn.dataset.editNote);
      if (!n) return;
      editingNote = n.id;
      $('n-title').value = n.title; $('n-content').value = n.content;
      $('n-save').textContent = '更新笔记';
      $('n-title').scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    if (delBtn) {
      if (!confirm('确定删除这条笔记？此操作不可恢复。')) return;
      await api('/api/workspace/notes/' + delBtn.dataset.delNote, { method: 'DELETE' });
      if (editingNote === +delBtn.dataset.delNote) resetNoteForm();
      loadWorkspace();
    }
  });

  const addTodo = async () => {
    const content = $('t-input').value.trim();
    if (!content) return;
    const res = await api('/api/workspace/todos', { method: 'POST', body: JSON.stringify({ content }) });
    if (res.ok) { $('t-input').value = ''; loadWorkspace(); }
  };
  $('t-add').addEventListener('click', addTodo);
  $('t-input').addEventListener('keydown', e => { if (e.key === 'Enter') addTodo(); });
  $('todo-list').addEventListener('click', async e => {
    const chk = e.target.closest('[data-todo-check]');
    const delBtn = e.target.closest('[data-del-todo]');
    if (chk) {
      const content = chk.closest('.todo-item').querySelector('span').textContent;
      await api('/api/workspace/todos/' + chk.dataset.todoCheck, {
        method: 'PUT', body: JSON.stringify({ content, done: chk.checked })
      });
      loadWorkspace();
    }
    if (delBtn) {
      await api('/api/workspace/todos/' + delBtn.dataset.delTodo, { method: 'DELETE' });
      loadWorkspace();
    }
  });

  $('b-add').addEventListener('click', async () => {
    const title = $('b-title').value.trim(), url = $('b-url').value.trim();
    if (!title || !url) { $('b-note').textContent = '标题和网址都要填。'; return; }
    const res = await api('/api/workspace/bookmarks', { method: 'POST', body: JSON.stringify({ title, url }) });
    $('b-note').textContent = res.ok ? '已添加。' : apiError(res.data, '添加失败');
    if (res.ok) { $('b-title').value = ''; $('b-url').value = ''; loadWorkspace(); }
  });
  $('bookmark-list').addEventListener('click', async e => {
    const delBtn = e.target.closest('[data-del-bm]');
    if (delBtn) {
      await api('/api/workspace/bookmarks/' + delBtn.dataset.delBm, { method: 'DELETE' });
      loadWorkspace();
    }
  });

  /* ---------- 音乐管理 ---------- */
  const loadMusic = async () => {
    const res = await api('/api/admin/music/tracks?limit=500');
    if (!res.ok) return;
    const tbody = $('track-rows');
    tbody.textContent = '';
    if (!res.data.length) {
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.colSpan = 8;
      td.className = 'muted';
      td.textContent = '还没有曲目';
      tr.appendChild(td);
      tbody.appendChild(tr);
      return;
    }
    // 全部曲目字段经 textContent 渲染，防 XSS
    res.data.forEach(t => {
      const tr = document.createElement('tr');

      const tdAudio = document.createElement('td');
      const audio = document.createElement('audio');
      audio.controls = true;
      audio.preload = 'none';
      audio.src = `/api/public/music/stream/${t.id}`;
      audio.style.cssText = 'height:32px;max-width:170px;';
      tdAudio.appendChild(audio);

      const tdTitle = document.createElement('td');
      tdTitle.textContent = t.title || '(未知标题)';
      const sub = document.createElement('div');
      sub.className = 'muted';
      sub.textContent = '#' + t.id;
      tdTitle.appendChild(sub);

      const tdArtist = document.createElement('td');
      tdArtist.textContent = t.artist || '—';
      const tdAlbum = document.createElement('td');
      tdAlbum.textContent = t.album || '—';
      const tdDur = document.createElement('td');
      tdDur.textContent = fmtDur(t.duration);
      const tdTime = document.createElement('td');
      tdTime.className = 'muted';
      tdTime.textContent = t.created_at || '';

      const tdVis = document.createElement('td');
      const sel = document.createElement('select');
      sel.className = 'vis-select';
      sel.dataset.visTrack = t.id;
      sel.dataset.prev = t.visibility;
      sel.setAttribute('aria-label', '可见性');
      [['public', '公开'], ['private', '私密']].forEach(([val, label]) => {
        const opt = document.createElement('option');
        opt.value = val;
        opt.textContent = label;
        if (t.visibility === val) opt.selected = true;
        sel.appendChild(opt);
      });
      tdVis.appendChild(sel);

      const tdOps = document.createElement('td');
      tdOps.className = 'actions';
      const delBtn = document.createElement('button');
      delBtn.type = 'button';
      delBtn.className = 'danger';
      delBtn.dataset.delTrack = t.id;
      delBtn.textContent = '删除';
      tdOps.appendChild(delBtn);

      tr.append(tdAudio, tdTitle, tdArtist, tdAlbum, tdDur, tdTime, tdVis, tdOps);
      tbody.appendChild(tr);
    });
  };
  $('m-btn').addEventListener('click', () => $('m-file').click());
  $('m-file').addEventListener('change', async () => {
    const file = $('m-file').files[0];
    if (!file) return;
    $('m-btn').disabled = true;
    $('m-note').textContent = `正在上传「${file.name}」…`;
    try {
      const fd = new FormData(); fd.append('file', file);
      const res = await authedFetch('/api/admin/music/upload', { method: 'POST', body: fd });
      const data = await res.json().catch(() => ({}));
      $('m-note').textContent = res.ok ? '上传成功。' : apiError(data, '上传失败');
      if (res.ok) loadMusic();
    } finally { $('m-btn').disabled = false; $('m-file').value = ''; }
  });
  $('track-rows').addEventListener('click', async e => {
    const delBtn = e.target.closest('[data-del-track]');
    if (delBtn) {
      if (!confirm('确定删除这首曲目？此操作不可恢复。')) return;
      await api('/api/admin/music/' + delBtn.dataset.delTrack, { method: 'DELETE' });
      loadMusic();
    }
  });
  // 可见性切换：成功只更新该行状态，失败回退选择，均不整页刷新
  $('track-rows').addEventListener('change', async e => {
    const sel = e.target.closest('[data-vis-track]');
    if (!sel) return;
    const res = await api('/api/admin/music/' + sel.dataset.visTrack, {
      method: 'PATCH', body: JSON.stringify({ visibility: sel.value })
    });
    if (res.ok) {
      sel.dataset.prev = sel.value;
      $('m-note').textContent = `曲目 #${sel.dataset.visTrack} 可见性已更新。`;
    } else {
      sel.value = sel.dataset.prev;
      $('m-note').textContent = apiError(res.data, '可见性更新失败');
    }
  });

  /* ---------- 网盘 ---------- */
  const loadCloud = async () => {
    const res = await api('/api/cloud/files?limit=100');
    if (!res.ok) return;
    $('cloud-rows').innerHTML = res.data.length ? res.data.map(f => `
      <tr>
        <td>${escapeHtml(f.original_name)}</td>
        <td>${fmtSize(f.size)}</td><td class="muted">${escapeHtml(f.mime || '—')}</td>
        <td class="muted">${escapeHtml(f.created_at)}</td>
        <td class="actions">
          <button type="button" data-dl-file="${f.id}">下载</button>
          <button type="button" class="danger" data-del-file="${f.id}">删除</button>
        </td>
      </tr>`).join('') : '<tr><td colspan="5" class="muted">网盘还是空的</td></tr>';
  };
  $('c-btn').addEventListener('click', () => $('c-file').click());
  $('c-file').addEventListener('change', async () => {
    const file = $('c-file').files[0];
    if (!file) return;
    if (file.size > 20 * 1024 * 1024) { $('cl-note').textContent = '文件超过 20MB 限制。'; return; }
    $('c-btn').disabled = true;
    $('cl-note').textContent = `正在上传「${file.name}」…`;
    try {
      const fd = new FormData(); fd.append('file', file);
      const res = await authedFetch('/api/admin/cloud/upload', { method: 'POST', body: fd });
      const data = await res.json().catch(() => ({}));
      $('cl-note').textContent = res.ok ? '上传成功。' : apiError(data, '上传失败');
      if (res.ok) loadCloud();
    } finally { $('c-btn').disabled = false; $('c-file').value = ''; }
  });
  $('cloud-rows').addEventListener('click', async e => {
    const dlBtn = e.target.closest('[data-dl-file]');
    const delBtn = e.target.closest('[data-del-file]');
    if (dlBtn) {
      // 下载接口需鉴权：blob 方式取回，再用临时链接触发浏览器保存
      try {
        const r = await authedFetch('/api/cloud/download/' + dlBtn.dataset.dlFile);
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const blob = await r.blob();
        const dispo = r.headers.get('content-disposition') || '';
        let name = 'download';
        const star = dispo.match(/filename\*=UTF-8''([^;]+)/);
        const plain = dispo.match(/filename="([^"]+)"/);
        if (star) name = decodeURIComponent(star[1]);
        else if (plain) name = plain[1];
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = name; a.click();
        URL.revokeObjectURL(url);
      } catch (err) { $('cl-note').textContent = '下载失败：' + err.message; }
    }
    if (delBtn) {
      if (!confirm('确定删除这个文件？此操作不可恢复。')) return;
      await api('/api/admin/cloud/files/' + delBtn.dataset.delFile, { method: 'DELETE' });
      loadCloud();
    }
  });

  // 已有会话则免登录直接进入（放在末尾：避免 const 箭头函数 TDZ 在脚本初始化期被调用）
  if (access && refresh) { gate.classList.add('hidden'); panel.classList.remove('hidden'); loadAll(); }
})();

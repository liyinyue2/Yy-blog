(() => {
  const $ = id => document.getElementById(id);
  const escapeHtml = value => String(value ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  let token = sessionStorage.getItem('admin-token') || '';
  let editingSlug = null;
  let editingCategory = null;

  const api = (path, options = {}) => fetch(path, {
    ...options,
    headers: { 'Content-Type': 'application/json', 'X-Admin-Token': token, ...(options.headers || {}) }
  }).then(async res => ({ ok: res.ok, status: res.status, data: await res.json().catch(() => ({})) }));

  /* ---------- 令牌 ---------- */
  const gate = $('token-gate'), panel = $('admin-panel');
  const tryToken = async () => {
    token = token || $('token-input').value.trim();
    const res = await api('/api/admin/articles');
    if (res.ok) { sessionStorage.setItem('admin-token', token); gate.classList.add('hidden'); panel.classList.remove('hidden'); loadAll(); }
    else { $('token-note').textContent = '令牌不正确，请重试。'; token = ''; }
  };
  $('token-submit').addEventListener('click', tryToken);
  $('token-input').addEventListener('keydown', e => { if (e.key === 'Enter') tryToken(); });
  if (token) { $('token-input').value = token; tryToken(); }

  /* ---------- 选项卡 ---------- */
  $('admin-tabs').addEventListener('click', e => {
    const btn = e.target.closest('[data-tab]');
    if (!btn) return;
    document.querySelectorAll('#admin-tabs button').forEach(b => b.classList.toggle('is-active', b === btn));
    ['articles', 'categories', 'messages', 'subscribers', 'settings'].forEach(t =>
      $('tab-' + t).classList.toggle('hidden', t !== btn.dataset.tab));
  });

  /* ---------- 数据加载 ---------- */
  const loadAll = async () => {
    const [stats, articles, categories, messages, subscribers, settings] = await Promise.all([
      api('/api/stats'), api('/api/admin/articles'), api('/api/categories'),
      api('/api/admin/messages'), api('/api/admin/subscribers'), api('/api/settings')
    ]);
    if (!stats.ok || !articles.ok) { sessionStorage.removeItem('admin-token'); location.reload(); return; }
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
        note.textContent = res.data.error || '导入失败，请检查文件格式。';
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
      $('editor-note').textContent = res.data.message || res.data.error || '';
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
        $('editor-note').textContent = res.data.error || '保存失败，请重试。';
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
      const res = await api('/api/admin/categories/' + delBtn.dataset.delCat, { method: 'DELETE' });
      $('c-note').textContent = res.data.message || res.data.error || '';
      loadAll();
    }
  });

  $('c-save').addEventListener('click', async () => {
    const payload = { name: $('c-name').value.trim(), description: $('c-desc').value.trim() };
    let res;
    if (editingCategory) {
      res = await api('/api/admin/categories/' + editingCategory, { method: 'PUT', body: JSON.stringify(payload) });
    } else {
      payload.slug = $('c-slug').value.trim();
      res = await api('/api/admin/categories', { method: 'POST', body: JSON.stringify(payload) });
    }
    $('c-note').textContent = res.data.message || res.data.error || '';
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
    $('s-note').textContent = res.data.message || res.data.error || '';
  });
})();

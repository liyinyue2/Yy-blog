
    (() => {
      const toggle = document.querySelector('.menu-toggle');
      const menu = document.getElementById('mobile-menu');
      const currentPath = window.location.pathname.replace(/index\.html$/, '') || '/';
      document.querySelectorAll('.links a, .mobile-menu a').forEach(link => {
        const linkPath = new URL(link.href, window.location.origin).pathname.replace(/index\.html$/, '') || '/';
        link.classList.toggle('is-current', linkPath === currentPath);
      });
      if (toggle && menu) {
        toggle.addEventListener('click', () => {
          const open = menu.classList.toggle('is-open');
          toggle.setAttribute('aria-expanded', String(open));
          toggle.setAttribute('aria-label', open ? '关闭菜单' : '打开菜单');
        });
        menu.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
          menu.classList.remove('is-open');
          toggle.setAttribute('aria-expanded', 'false');
          toggle.setAttribute('aria-label', '打开菜单');
        }));
      }
      const revealItems = document.querySelectorAll('.reveal');
      if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver(entries => entries.forEach(entry => {
          if (entry.isIntersecting) { entry.target.classList.add('is-visible'); observer.unobserve(entry.target); }
        }), { threshold: .12 });
        revealItems.forEach(item => observer.observe(item));
      } else {
        revealItems.forEach(item => item.classList.add('is-visible'));
      }

      /* ---------- 订阅 ---------- */
      const form = document.getElementById('subscribe-form');
      const formNote = document.getElementById('form-note');
      form?.addEventListener('submit', async event => {
        event.preventDefault();
        const email = new FormData(form).get('email');
        if (!email) return;
        formNote.textContent = '正在提交…';
        try {
          const res = await fetch('/api/subscribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
          });
          const data = await res.json();
          const err = (typeof data.error === 'string' && data.error) || (typeof data.detail === 'string' && data.detail);
          if (res.ok) {
            form.reset();
            formNote.textContent = data.message || '已订阅，下一封更新会寄到你的邮箱。';
          } else {
            formNote.textContent = err || '订阅失败，请稍后再试。';
          }
        } catch {
          formNote.textContent = '网络异常，请稍后再试。';
        }
      });

      const toast = document.getElementById('toast');
      let toastTimer;
      const notify = message => {
        if (!toast) return; toast.textContent = message;
        toast.classList.add('is-visible');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => toast.classList.remove('is-visible'), 2800);
      };

      /* ---------- 数据库驱动的动态渲染 ---------- */
      const escapeHtml = value => String(value ?? '')
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

      // 文章列表页（分类筛选）
      const articleList = document.getElementById('article-list');
      if (articleList) {
        const filters = document.getElementById('article-filters');
        const searchInput = document.getElementById('article-search');
        let activeCategory = decodeURIComponent((window.location.hash || '').replace('#', '')) || 'all';
        const renderCards = list => {
          articleList.innerHTML = list.length ? list.map(a => `
            <article class="article-card" data-category="${escapeHtml(a.category_slug)}">
              <div>
                <div class="article-meta"><span class="article-tag">${escapeHtml(a.category_name)}</span><time>${escapeHtml(a.date)}</time></div>
                <h3>${escapeHtml(a.title)}</h3>
                <p>${escapeHtml(a.summary)}</p>
              </div>
              <a class="read-link" href="/post-${escapeHtml(a.slug)}.html">阅读全文 <span>↗</span></a>
            </article>`).join('')
            : '<p class="list-empty">没有符合条件的文章，换个筛选条件试试。</p>';
        };
        const syncUrl = () => {
          history.replaceState(null, '', activeCategory === 'all' ? '/articles.html' : '/articles.html#' + activeCategory);
        };
        const applyFilter = () => {
          document.querySelectorAll('#article-filters .topic-chip').forEach(chip =>
            chip.classList.toggle('is-active', chip.dataset.filter === activeCategory));
          document.querySelectorAll('#article-list .article-card').forEach(card =>
            card.classList.toggle('is-hidden', activeCategory !== 'all' && card.dataset.category !== activeCategory));
        };
        (async () => {
          try {
            const [articles, categories] = await Promise.all([
              fetch('/api/articles').then(r => r.json()),
              fetch('/api/categories').then(r => r.json())
            ]);
            renderCards(articles);
            filters.innerHTML = ['all', ...categories].map(c => c === 'all' || c.article_count
              ? `<button class="topic-chip" type="button" data-filter="${c === 'all' ? 'all' : escapeHtml(c.slug)}">${c === 'all' ? '全部' : escapeHtml(c.name)}</button>`
              : '').join('');
            filters.querySelectorAll('.topic-chip').forEach(chip => chip.addEventListener('click', () => {
              activeCategory = chip.dataset.filter;
              syncUrl(); applyFilter();
            }));
            applyFilter();
          } catch {
            articleList.innerHTML = '<p class="list-empty">文章加载失败，请稍后刷新重试。</p>';
          }
        })();

        // 搜索（防抖 300ms，搜索时清空分类筛选）
        if (searchInput) {
          let timer;
          searchInput.addEventListener('input', () => {
            clearTimeout(timer);
            timer = setTimeout(async () => {
              const q = searchInput.value.trim();
              activeCategory = 'all';
              syncUrl();
              try {
                const list = await fetch('/api/articles' + (q ? '?q=' + encodeURIComponent(q) : '')).then(r => r.json());
                renderCards(list);
                applyFilter();
              } catch { /* 保持现有内容 */ }
            }, 300);
          });
        }
      }

      /* ---------- 站点设置应用 ---------- */
      const SOCIAL_LABELS = { wechat: '微信', qq: 'QQ', douyin: '抖音', github: 'GitHub' };
      const SOCIAL_FIELDS = ['wechat', 'qq', 'douyin', 'github'];
      const copyValue = (value, key) => {
        const done = () => notify(`${SOCIAL_LABELS[key]}：${value} 已复制到剪贴板`);
        if (navigator.clipboard?.writeText) navigator.clipboard.writeText(value).then(done, done);
        else done();
      };
      const isLink = value => /^https?:\/\//i.test(value);
      fetch('/api/settings').then(r => r.json()).then(settings => {
        document.querySelectorAll('[data-setting]').forEach(el => {
          const key = el.dataset.setting;
          if (settings[key]) el.textContent = settings[key];
        });
        document.querySelectorAll('[data-setting-html]').forEach(el => {
          const key = el.dataset.settingHtml;
          if (settings[key]) el.innerHTML = settings[key];
        });
        const brand = document.querySelector('.brand');
        if (brand && settings.site_name) brand.setAttribute('aria-label', settings.site_name + ' 首页');

        // 首页社交链接：填了链接则跳转，填了账号则点击复制
        document.querySelectorAll('[data-social]').forEach(el => {
          const key = el.dataset.social;
          const value = (settings['social_' + key] || '').trim();
          if (!value) { el.remove(); return; }
          if (isLink(value)) {
            el.setAttribute('href', value);
            el.setAttribute('target', '_blank');
            el.setAttribute('rel', 'noopener');
          } else {
            el.addEventListener('click', event => { event.preventDefault(); copyValue(value, key); });
          }
        });

        // 关于页「找到我」
        const aboutSocial = document.getElementById('about-social');
        if (aboutSocial) {
          const entries = SOCIAL_FIELDS.filter(k => (settings['social_' + k] || '').trim());
          aboutSocial.innerHTML = entries.length ? entries.map(k => {
            const v = settings['social_' + k].trim();
            const href = isLink(v) ? escapeHtml(v) : '#';
            return `<a class="about-social-item" href="${href}" data-v="${escapeHtml(v)}" data-k="${k}"><b>${SOCIAL_LABELS[k]}</b><span>${escapeHtml(v)}</span><span class="about-social-arrow">↗</span></a>`;
          }).join('') : '<p class="list-empty">暂时没有留下社交账号。</p>';
          aboutSocial.querySelectorAll('.about-social-item').forEach(item => {
            const v = item.dataset.v;
            if (isLink(v)) { item.target = '_blank'; item.rel = 'noopener'; }
            else item.addEventListener('click', e => { e.preventDefault(); copyValue(v, item.dataset.k); });
          });
        }
      }).catch(() => {});

      /* ---------- 留言板 ---------- */
      const messageList = document.getElementById('message-list');
      if (messageList) {
        const loadMessages = () => fetch('/api/messages').then(r => r.json()).then(list => {
          messageList.innerHTML = list.length ? list.map(m => `
            <div class="message-card">
              <div class="message-card-head"><b>${escapeHtml(m.name)}</b><time>${escapeHtml((m.created_at || '').replace('T', ' ').slice(0, 16))}</time></div>
              <p>${escapeHtml(m.content)}</p>
              ${m.reply ? `<div class="message-reply"><b>博主回复</b>${escapeHtml(m.reply)}</div>` : ''}
            </div>`).join('')
            : '<p class="list-empty">还没有留言，来做第一个说话的人吧。</p>';
        }).catch(() => { messageList.innerHTML = '<p class="list-empty">留言加载失败，请稍后刷新重试。</p>'; });
        loadMessages();

        const messageForm = document.getElementById('message-form');
        const messageNote = document.getElementById('message-note');
        messageForm?.addEventListener('submit', async event => {
          event.preventDefault();
          const data = Object.fromEntries(new FormData(messageForm).entries());
          if (!data.content?.trim()) return;
          messageNote.textContent = '正在发送…';
          try {
            const res = await fetch('/api/messages', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(data)
            });
            const result = await res.json();
            const err = (typeof result.error === 'string' && result.error) || (typeof result.detail === 'string' && result.detail);
            messageNote.textContent = res.ok ? (result.message || '留言成功！') : (err || '留言失败，请稍后再试。');
            if (res.ok) { messageForm.reset(); loadMessages(); }
          } catch {
            messageNote.textContent = '网络异常，请稍后再试。';
          }
        });
      }
    })();

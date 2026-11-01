
    (() => {
      const toggle = document.querySelector('.menu-toggle');
      const menu = document.getElementById('mobile-menu');
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

      const cards = [...document.querySelectorAll('.article-card')];
      document.querySelectorAll('.topic-chip').forEach(chip => chip.addEventListener('click', () => {
        const filter = chip.dataset.filter;
        document.querySelectorAll('.topic-chip').forEach(item => item.classList.toggle('is-active', item === chip));
        cards.forEach(card => card.classList.toggle('is-hidden', filter !== 'all' && card.dataset.category !== filter));
      }));

      const reader = document.getElementById('reader');
      const readerTitle = document.getElementById('reader-title');
      const readerCategory = document.getElementById('reader-category');
      const closeReader = () => {
        if (!reader) return;
        reader.classList.remove('is-open');
        reader.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
      };
      document.querySelectorAll('.article-open').forEach(link => link.addEventListener('click', event => {
        event.preventDefault();
        readerTitle.textContent = link.dataset.title;
        readerCategory.textContent = `K's Blog / ${link.dataset.category}`;
        reader.classList.add('is-open');
        reader.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
      }));
      reader?.querySelector('.reader-close')?.addEventListener('click', closeReader);
      reader?.addEventListener('click', event => { if (event.target === reader) closeReader(); });
      document.addEventListener('keydown', event => { if (event.key === 'Escape') closeReader(); });

      const form = document.getElementById('subscribe-form');
      const formNote = document.getElementById('form-note');
      form?.addEventListener('submit', event => {
        event.preventDefault();
        const email = new FormData(form).get('email');
        if (!email) return;
        form.reset();
        formNote.textContent = '已订阅，下一封更新会寄到你的邮箱。';
      });

      const toast = document.getElementById('toast');
      let toastTimer;
      const notify = message => {
        if (!toast) return; toast.textContent = message;
        toast.classList.add('is-visible');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => toast.classList.remove('is-visible'), 2800);
      };
      document.querySelector('.sign-in')?.addEventListener('click', event => {
        event.preventDefault();
        notify('登录功能正在准备中，先订阅获取更新。');
      });
    })();

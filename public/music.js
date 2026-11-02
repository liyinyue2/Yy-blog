/* 音乐播放页：原生 JS，零依赖。所有用户可控字符串一律走 textContent 渲染。 */
(() => {
  const listEl = document.getElementById('track-list');
  if (!listEl) return;

  const COVER_FALLBACK = '/y-mark.svg';
  const audio = new Audio();
  audio.preload = 'metadata';
  audio.volume = 0.8;

  const el = id => document.getElementById(id);
  const coverEl = el('p-cover');
  const titleEl = el('p-title');
  const artistEl = el('p-artist');
  const btnPlay = el('btn-play');
  const btnPrev = el('btn-prev');
  const btnNext = el('btn-next');
  const iconPlay = el('icon-play');
  const iconPause = el('icon-pause');
  const progressTrack = el('progress-track');
  const progressFill = el('progress-fill');
  const timeCur = el('time-cur');
  const timeTotal = el('time-total');
  const volumeInput = el('volume');

  let tracks = [];
  let current = -1;
  let seeking = false;

  const fmt = sec => {
    if (!Number.isFinite(sec) || sec < 0) return '0:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${String(s).padStart(2, '0')}`;
  };

  const setPlayIcon = playing => {
    iconPlay.style.display = playing ? 'none' : '';
    iconPause.style.display = playing ? '' : 'none';
    btnPlay.setAttribute('aria-label', playing ? '暂停' : '播放');
  };

  const setCover = (img, track) => {
    img.onerror = () => { img.onerror = null; img.src = COVER_FALLBACK; };
    img.src = track && track.cover_url ? track.cover_url : COVER_FALLBACK;
  };

  const highlightRow = () => {
    listEl.querySelectorAll('.track-row').forEach((row, i) => {
      row.classList.toggle('is-playing', i === current);
    });
  };

  const updateButtons = () => {
    const has = tracks.length > 0;
    btnPlay.disabled = !has;
    btnPrev.disabled = !has;
    btnNext.disabled = !has;
  };

  const playIndex = i => {
    if (!tracks.length) return;
    current = ((i % tracks.length) + tracks.length) % tracks.length;
    const track = tracks[current];
    audio.src = `/api/public/music/stream/${track.id}`;
    titleEl.textContent = track.title || '未命名曲目';
    artistEl.textContent = track.artist || '未知艺术家';
    setCover(coverEl, track);
    timeTotal.textContent = fmt(track.duration);
    highlightRow();
    updateButtons();
    audio.play().then(() => setPlayIcon(true)).catch(() => setPlayIcon(false));
  };

  /* ---------- 曲目列表渲染（textContent，防 XSS） ---------- */
  const renderList = list => {
    listEl.textContent = '';
    if (!list.length) {
      const empty = document.createElement('p');
      empty.className = 'list-empty';
      empty.textContent = '还没有公开曲目，敬请期待。';
      listEl.appendChild(empty);
      return;
    }
    list.forEach((track, i) => {
      const row = document.createElement('div');
      row.className = 'track-row';
      row.setAttribute('role', 'button');
      row.tabIndex = 0;

      const no = document.createElement('span');
      no.className = 'track-no';
      no.textContent = String(i + 1).padStart(2, '0');

      const cover = document.createElement('img');
      cover.className = 'track-cover';
      cover.alt = '';
      setCover(cover, track);

      const title = document.createElement('span');
      title.className = 'track-title';
      title.textContent = track.title || '未命名曲目';

      const artist = document.createElement('span');
      artist.className = 'track-artist';
      artist.textContent = track.artist || '未知艺术家';

      const duration = document.createElement('span');
      duration.className = 'track-duration';
      duration.textContent = fmt(track.duration);

      row.append(no, cover, title, artist, duration);
      row.addEventListener('click', () => playIndex(i));
      row.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); playIndex(i); }
      });
      listEl.appendChild(row);
    });
  };

  fetch('/api/public/music/tracks?limit=100')
    .then(r => r.json())
    .then(list => {
      tracks = Array.isArray(list) ? list : [];
      renderList(tracks);
      updateButtons();
    })
    .catch(() => {
      listEl.textContent = '';
      const fail = document.createElement('p');
      fail.className = 'list-empty';
      fail.textContent = '曲目加载失败，请稍后刷新重试。';
      listEl.appendChild(fail);
    });

  /* ---------- 播放控制 ---------- */
  btnPlay.addEventListener('click', () => {
    if (current < 0) { playIndex(0); return; }
    if (audio.paused) { audio.play().then(() => setPlayIcon(true)).catch(() => {}); }
    else { audio.pause(); }
  });
  btnPrev.addEventListener('click', () => playIndex(current < 0 ? 0 : current - 1));
  btnNext.addEventListener('click', () => playIndex(current < 0 ? 0 : current + 1));
  audio.addEventListener('pause', () => setPlayIcon(false));
  audio.addEventListener('play', () => setPlayIcon(true));
  audio.addEventListener('ended', () => playIndex(current + 1));  // 播完自动下一首，列表循环
  audio.addEventListener('error', () => {
    if (current >= 0) setPlayIcon(false);
  });

  audio.addEventListener('loadedmetadata', () => {
    timeTotal.textContent = fmt(audio.duration);
  });
  audio.addEventListener('timeupdate', () => {
    if (seeking) return;
    timeCur.textContent = fmt(audio.currentTime);
    if (Number.isFinite(audio.duration) && audio.duration > 0) {
      const pct = (audio.currentTime / audio.duration) * 100;
      progressFill.style.width = pct + '%';
      progressTrack.setAttribute('aria-valuenow', String(Math.round(pct)));
    }
  });

  /* ---------- 进度条拖动（seek 由浏览器自动发 Range 请求，依赖后端 206） ---------- */
  const seekTo = clientX => {
    if (current < 0 || !Number.isFinite(audio.duration) || audio.duration <= 0) return;
    const rect = progressTrack.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    progressFill.style.width = (ratio * 100) + '%';
    timeCur.textContent = fmt(ratio * audio.duration);
    audio.currentTime = ratio * audio.duration;
  };
  progressTrack.addEventListener('pointerdown', e => {
    seeking = true;
    progressTrack.setPointerCapture(e.pointerId);
    seekTo(e.clientX);
  });
  progressTrack.addEventListener('pointermove', e => { if (seeking) seekTo(e.clientX); });
  progressTrack.addEventListener('pointerup', () => { seeking = false; });
  progressTrack.addEventListener('pointercancel', () => { seeking = false; });
  progressTrack.addEventListener('keydown', e => {
    if (current < 0 || !Number.isFinite(audio.duration)) return;
    if (e.key === 'ArrowLeft') { audio.currentTime = Math.max(0, audio.currentTime - 5); e.preventDefault(); }
    if (e.key === 'ArrowRight') { audio.currentTime = Math.min(audio.duration, audio.currentTime + 5); e.preventDefault(); }
  });

  /* ---------- 音量 ---------- */
  volumeInput.addEventListener('input', () => {
    audio.volume = Math.min(1, Math.max(0, volumeInput.value / 100));
  });
})();

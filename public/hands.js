
    (() => {
      'use strict';

      const SOURCE_URL = '/kindred-hands.webp';
      const SRC = {
        LA: [0, .06, .47, .40],
        RA: [.53, .06, .47, .40],
        LB: [0, .55, .47, .40],
        RB: [.53, .55, .47, .40]
      };
      const LEVELS = [0, .26, .52, .78, 1];
      const LOOP = 20;
      const hero = document.querySelector('.hero');
      const canvas = document.getElementById('dots');
      const ctx = canvas.getContext('2d');

      let W = 0, H = 0, DPR = 1;
      let step = 5, rowStep = 10.25, cols = 1, rows = 1, R = 2.3;
      let portrait = false;
      let seeds = new Float32Array(1);
      let fA, fB, aCtx, bCtx;
      let tiles = {};
      let fieldsReady = false;
      let firstTime = performance.now();

      const fract = n => n - Math.floor(n);
      const clamp = (n, min, max) => Math.min(max, Math.max(min, n));
      const hash = (a, b) => fract(Math.sin(a * 127.1 + b * 311.7) * 43758.5453);
      const smooth = (a, b, x) => {
        const u = clamp((x - a) / (b - a), 0, 1);
        return u * u * (3 - 2 * u);
      };
      const mixAt = (t, on, off, duration) => smooth(on, on + duration, t) * (1 - smooth(off, off + duration, t));

      function makeField() {
        const field = document.createElement('canvas');
        field.width = cols;
        field.height = rows;
        return field;
      }

      function resize() {
        W = hero.clientWidth;
        H = hero.clientHeight;
        DPR = Math.min(2, window.devicePixelRatio || 1);
        canvas.width = Math.round(W * DPR);
        canvas.height = Math.round(H * DPR);
        ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
        ctx.imageSmoothingEnabled = false;

        portrait = H > W;
        step = Math.max(5, W / 205);
        rowStep = step * 2.05;
        cols = Math.ceil(W / step);
        rows = Math.ceil(H / rowStep);
        R = step * .46;
        seeds = new Float32Array(cols * rows);
        for (let j = 0; j < rows; j++) {
          for (let i = 0; i < cols; i++) {
            seeds[j * cols + i] = .55 * hash(i, j) + .45 * hash(j * 3.1, 7.7);
          }
        }

        fA = makeField();
        fB = makeField();
        aCtx = fA.getContext('2d', { willReadFrequently: true });
        bCtx = fB.getContext('2d', { willReadFrequently: true });
      }

      function sliceTiles(image) {
        const iw = image.naturalWidth;
        const ih = image.naturalHeight;
        Object.entries(SRC).forEach(([name, rect]) => {
          const [rx, ry, rw, rh] = rect;
          const sx = Math.round(rx * iw);
          const sy = Math.round(ry * ih);
          const sw = Math.round(rw * iw);
          const sh = Math.round(rh * ih);
          const tile = document.createElement('canvas');
          tile.width = 420;
          tile.height = Math.max(1, Math.round(420 * sh / sw));
          const tileCtx = tile.getContext('2d');
          tileCtx.fillStyle = '#fff';
          tileCtx.fillRect(0, 0, tile.width, tile.height);
          tileCtx.imageSmoothingEnabled = true;
          tileCtx.imageSmoothingQuality = 'high';
          tileCtx.drawImage(image, sx, sy, sw, sh, 0, 0, tile.width, tile.height);
          tiles[name] = tile;
        });
        fieldsReady = true;
      }

      function drawHand(fieldCtx, tileName, left, seconds) {
        const a = 2 * Math.PI * seconds / LOOP;
        const phase = left ? 0 : Math.PI;
        const hw = W * (portrait ? .66 : .53);
        const hh = hw * ((.40 * 1520) / (.47 * 2688));
        const cy = H * (portrait ? .66 : .54);
        const reach = (.035 * Math.sin(a + phase) + .012 * Math.sin(2 * a + 1.3 + phase)) * W;
        const x = left ? reach - W * .045 : W - hw + W * .045 - reach;
        const scale = 1 + .07 * Math.sin(a + .9 + phase);
        const rotation = (left ? 1 : -1) * .045 * Math.sin(a + 2.1 + phase);
        const pivotX = left ? 0 : W;

        fieldCtx.save();
        fieldCtx.scale(cols / W, rows / H);
        fieldCtx.translate(pivotX, cy);
        fieldCtx.rotate(rotation);
        fieldCtx.scale(scale, scale);
        fieldCtx.translate(-pivotX, -cy);
        fieldCtx.imageSmoothingEnabled = true;
        fieldCtx.imageSmoothingQuality = 'high';
        fieldCtx.drawImage(tiles[tileName], x, cy - hh / 2, hw, hh);
        fieldCtx.restore();
      }

      function fillFields(seconds) {
        aCtx.setTransform(1, 0, 0, 1, 0, 0);
        bCtx.setTransform(1, 0, 0, 1, 0, 0);
        aCtx.fillStyle = '#fff';
        bCtx.fillStyle = '#fff';
        aCtx.fillRect(0, 0, cols, rows);
        bCtx.fillRect(0, 0, cols, rows);
        drawHand(aCtx, 'LA', true, seconds);
        drawHand(aCtx, 'RA', false, seconds);
        drawHand(bCtx, 'LB', true, seconds);
        drawHand(bCtx, 'RB', false, seconds);
      }

      function render(time) {
        const t = ((time % LOOP) + LOOP) % LOOP;
        ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
        ctx.clearRect(0, 0, W, H);
        if (!fieldsReady || !aCtx || !bCtx) return;

        fillFields(t);
        let pixelsA, pixelsB;
        try {
          pixelsA = aCtx.getImageData(0, 0, cols, rows).data;
          pixelsB = bCtx.getImageData(0, 0, cols, rows).data;
        } catch (error) {
          console.warn('Kindred hand source could not be sampled.', error);
          fieldsReady = false;
          return;
        }

        const leftMix = mixAt(t, 6.2, 14.6, 1.6);
        const rightMix = mixAt(t, 2.4, 10.4, 1.6);
        const tick = Math.floor(t * 7);
        const quietXWidth = portrait ? .44 : .2;
        const quietYCenter = portrait ? .33 : .385;
        const transitioningLeft = leftMix > .001 && leftMix < .999;
        const transitioningRight = rightMix > .001 && rightMix < .999;
        ctx.fillStyle = '#0d0d0d';

        for (let j = 0; j < rows; j++) {
          const shifted = hash(j, tick) > .965;
          const shift = shifted ? Math.round((hash(tick, j) - .5) * 8) : 0;
          const py = (j + .5) * rowStep;
          const ey = (py / H - quietYCenter) / .085;

          for (let i = 0; i < cols; i++) {
            const sampleI = clamp(i - shift, 0, cols - 1);
            const sampleIndex = (j * cols + sampleI) * 4;
            const index = j * cols + i;
            const seed = seeds[index];
            const mix = i < cols / 2 ? leftMix : rightMix;
            const onFront = i < cols / 2 ? transitioningLeft : transitioningRight;
            const data = seed < mix ? pixelsB : pixelsA;
            const lum = data[sampleIndex] / 255;
            let value = clamp((1 - lum - .16) / .42, 0, 1);
            if (value === 0) continue;

            value *= .86 + .14 * Math.sin(t * 3.2 + seed * 40);
            const centerDistance = Math.abs((i + .5) / cols - .5);
            value *= smooth(.035, .11, centerDistance);
            value *= smooth(.85, 1.25, Math.hypot(centerDistance / quietXWidth, ey));

            if (onFront) {
              const delta = Math.abs(seed - mix);
              if (delta < .12) {
                value *= delta / .12;
                if (hash(i + tick, j) <= .4) value *= .3;
              }
            }

            let level = 0;
            for (let n = LEVELS.length - 1; n > 0; n--) {
              if (value >= LEVELS[n] - .13) {
                level = LEVELS[n];
                break;
              }
            }
            if (!level) continue;
            const radius = level === .26 ? R * .38 : R * level;
            ctx.beginPath();
            ctx.arc((i + .5) * step, py, radius, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }

      const source = new Image();
      source.crossOrigin = 'anonymous';
      source.onload = () => sliceTiles(source);
      source.onerror = () => console.warn('Kindred hand source failed to load.');
      source.src = SOURCE_URL;

      window.addEventListener('resize', resize, { passive: true });
      resize();

      let raf = 0;
      let pageVisible = true;
      // 性能纪律（P0 设计系统）：动画上限 30fps；prefers-reduced-motion 时只渲染一帧静态图
      const FRAME_MIN_MS = 1000 / 30;
      let lastRender = 0;
      const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      function frame(now) {
        raf = 0;
        if (!pageVisible || document.hidden) return;
        if (reduceMotion) { render(0); return; }
        if (now - lastRender >= FRAME_MIN_MS - 1) {
          lastRender = now;
          render((now - firstTime) / 1000);
        }
        raf = requestAnimationFrame(frame);
      }
      function kick() {
        if (!raf && pageVisible && !document.hidden) raf = requestAnimationFrame(frame);
      }
      document.addEventListener('visibilitychange', kick);
      if ('IntersectionObserver' in window && hero) {
        new IntersectionObserver(entries => {
          pageVisible = entries.some(e => e.isIntersecting);
          if (pageVisible) kick();
        }, { threshold: 0.01 }).observe(hero);
      }
      kick();
    })();

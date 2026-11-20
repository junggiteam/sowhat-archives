(() => {
  'use strict';
  // Today's date (Asia/Seoul) and rolling KMA weather for major cities (hidden only if the KMA data is stale).
  const box = document.querySelector('#sowhat-archive [data-swa-today]');
  if (!box || box.dataset.ready) return;
  box.dataset.ready = 'true';
  const dateNode = box.querySelector('[data-swa-date]');
  const weather = box.querySelector('[data-swa-weather]');
  const days = ['일', '월', '화', '수', '목', '금', '토'];
  function showDate() {
    const parts = {};
    new Intl.DateTimeFormat('en-US', {timeZone: 'Asia/Seoul', year: 'numeric', month: 'numeric', day: 'numeric', weekday: 'short'}).formatToParts(new Date()).forEach(p => { parts[p.type] = p.value; });
    const weekday = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].indexOf(parts.weekday);
    const year = document.createElement('span');
    year.className = 'swa-year';
    year.textContent = parts.year + '년 ';
    dateNode.replaceChildren(year, parts.month + '월 ' + parts.day + '일(' + days[weekday] + ')');
    box.hidden = false;
  }
  const svg = body => '<svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + body + '</svg>';
  const sun = '<circle cx="12" cy="12" r="4.2" stroke="#f0a020" fill="#ffd25e"/><path stroke="#f0a020" d="M12 2.5v2M12 19.5v2M4.6 4.6 6 6M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4"/>';
  const cloud = (y = 0) => '<path transform="translate(0 ' + y + ')" stroke="#7d8591" fill="#eef0f3" d="M7 18.5h10.2a3.8 3.8 0 0 0 .4-7.6A5.5 5.5 0 0 0 7 10.3a4.1 4.1 0 0 0 0 8.2Z"/>';
  const icons = {
    clear: svg(sun),
    night: svg('<path stroke="#6a72c4" fill="#dfe2fb" d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5Z"/>'),
    partly: svg('<g transform="translate(-3 -3) scale(.8)">' + sun + '</g>' + cloud(1.5)),
    cloudy: svg(cloud()),
    fog: svg(cloud(-3) + '<path stroke="#9aa1ab" d="M5 19h14M7 22h10"/>'),
    rain: svg(cloud(-3) + '<path stroke="#3d8be0" d="M8.5 18.5 7.5 21.5M12.5 18.5l-1 3M16.5 18.5l-1 3"/>'),
    snow: svg(cloud(-3) + '<g stroke="#5aa4e6"><path d="M8 18.5v3M6.7 20h2.6M12 19v3M10.7 20.5h2.6M16 18.5v3M14.7 20h2.6"/></g>'),
    thunder: svg(cloud(-3) + '<path stroke="#e2a400" fill="#ffd25e" d="m12.5 15-2.5 4h3l-1.5 4"/>')
  };
  const thermometer = '<svg class="swa-temp-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M14 14.76V5a2 2 0 0 0-4 0v9.76a4 4 0 1 0 4 0Z"/><path d="M12 9v7"/></svg>';
  const kmaUrl = 'https://sowhat-cron.junggiteam.workers.dev/weather.json';
  const seoulHour = () => Number(new Intl.DateTimeFormat('en-US', {timeZone: 'Asia/Seoul', hour: 'numeric', hourCycle: 'h23'}).format(new Date()));
  // 기상청 초단기실황·예보 (refreshed every 30 minutes by the sowhat-cron Cloudflare Worker).
  function fromKma(payload) {
    if (!payload || payload.schemaVersion !== 2 || payload.source !== 'kma' || !Array.isArray(payload.cities)) return [];
    const updated = Date.parse(payload.updatedAt);
    if (!Number.isFinite(updated) || Date.now() - updated > 3 * 60 * 60 * 1000) return [];
    const day = seoulHour() >= 6 && seoulHour() < 18;
    return payload.cities.map(d => {
      let info = null;
      if (d.lightning) info = ['thunder', '뇌우'];
      else if (d.pty === 1 || d.pty === 5) info = ['rain', '비'];
      else if (d.pty === 2 || d.pty === 6) info = ['snow', '비/눈'];
      else if (d.pty === 3 || d.pty === 7) info = ['snow', '눈'];
      else if (d.sky === 1) info = [day ? 'clear' : 'night', '맑음'];
      else if (d.sky === 3) info = ['partly', '구름많음'];
      else if (d.sky === 4) info = ['cloudy', '흐림'];
      return info && {icon: info[0], label: info[1], temperature: d.temperature, place: String(d.place || '').slice(0, 6)};
    }).filter(Boolean);
  }
  const valid = view => view && Number.isFinite(Number(view.temperature)) && icons[view.icon] && view.place;
  function item(view) {
    const node = document.createElement('span');
    node.className = 'swa-weather-item';
    const icon = document.createElement('span');
    icon.className = 'swa-weather-icon';
    icon.setAttribute('aria-hidden', 'true');
    icon.innerHTML = icons[view.icon];
    const label = document.createElement('span');
    label.textContent = view.label;
    const temp = document.createElement('span');
    temp.className = 'swa-temp';
    temp.innerHTML = thermometer;
    temp.append(Math.round(Number(view.temperature)) + '°C');
    const place = document.createElement('span');
    place.className = 'swa-weather-place';
    place.textContent = view.place;
    node.append(icon, label, temp, place);
    return node;
  }
  const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let views = [];
  let index = 0;
  let paused = false;
  function show(animate) {
    if (!views.length) return;
    const next = item(views[index % views.length]);
    const current = weather.querySelector('.swa-weather-item:not(.swa-leaving)');
    weather.hidden = false;
    if (!animate || reduceMotion || !current) { weather.replaceChildren(next); return; }
    current.classList.add('swa-leaving');
    next.classList.add('swa-entering');
    weather.append(next);
    setTimeout(() => { current.remove(); next.classList.remove('swa-entering'); }, 450);
  }
  // Size the slot to the widest city so the divider hugs the weather and nothing jumps while rolling.
  function fitWidth() {
    let widest = 0;
    views.forEach(view => {
      const probe = item(view);
      probe.style.visibility = 'hidden';
      weather.append(probe);
      widest = Math.max(widest, probe.getBoundingClientRect().width);
      probe.remove();
    });
    if (widest) weather.style.width = Math.ceil(widest + parseFloat(getComputedStyle(weather).paddingLeft || 0) + 1) + 'px';
  }
  function setViews(list) {
    const clean = list.filter(valid);
    if (!clean.length) return false;
    const place = views.length ? views[index % views.length].place : '';
    views = clean;
    index = Math.max(0, views.findIndex(v => v.place === place));
    show(false);
    fitWidth();
    return true;
  }
  weather.addEventListener('mouseenter', () => { paused = true; });
  weather.addEventListener('mouseleave', () => { paused = false; });
  const roller = setInterval(() => {
    if (!box.isConnected) { clearInterval(roller); return; }
    if (paused || document.hidden || views.length < 2) return;
    index = (index + 1) % views.length;
    show(true);
  }, 4000);
  async function getJson(url) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch(url, {signal: controller.signal, credentials: 'omit'});
      if (!response.ok) throw new Error('unavailable');
      return await response.json();
    } finally { clearTimeout(timer); }
  }
  const cacheKey = 'swa-weather-v4';
  const maxAge = 20 * 60 * 1000;
  let loading = false;
  async function loadWeather() {
    try {
      const cached = JSON.parse(localStorage.getItem(cacheKey) || 'null');
      if (cached && Date.now() - cached.at < maxAge && setViews(cached.views || [])) return;
    } catch (_) {}
    if (loading) return;
    loading = true;
    let list = [];
    try { list = fromKma(await getJson(kmaUrl + '?v=' + Math.floor(Date.now() / 600000))); } catch (_) {}
    if (setViews(list)) { try { localStorage.setItem(cacheKey, JSON.stringify({views: views, at: Date.now()})); } catch (_) {} }
    else { views = []; weather.hidden = true; } // KMA data missing or older than 3 hours
    loading = false;
  }
  showDate();
  loadWeather();
  const tick = setInterval(() => {
    if (!box.isConnected) { clearInterval(tick); return; }
    showDate();
    if (!document.hidden) loadWeather();
  }, 10 * 60 * 1000);
})();
(() => {
  'use strict';
  const root = document.getElementById('sowhat-archive');
  if (!root || root.dataset.ready) return;
  const dataNode = root.querySelector('[data-swa-seed]');
  const grid = root.querySelector('[data-swa-grid]');
  const search = root.querySelector('[data-swa-search]');
  const more = root.querySelector('[data-swa-more]');
  const empty = root.querySelector('[data-swa-empty]');
  const months = root.querySelector('[data-swa-months]');
  const structured = root.querySelector('[data-swa-structured]');
  const archiveMonth = root.dataset.archiveMonth || '';
  const archiveBase = root.dataset.archiveBase;
  const archiveUrl = key => archiveBase + (key ? key.replace('-', '/') + '/' : '');
  const monthName = key => key.slice(0, 4) + '년 ' + Number(key.slice(5)) + '월';
  const scoped = items => items.filter(x => !archiveMonth || x.date.startsWith(archiveMonth));
  const imageHosts = new Set(['img.stibee.com', 'img2.stibee.com', 'cdn.stibee.com', 'resource.stibee.com', 'cdn.imweb.me']);
  const calendarIcon = '<svg class="swa-cal" viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>';
  let limit = 9;
  let currentSignature = '';
  let refreshing = false;
  let lastRefresh = 0;

  function normalize(raw) {
    if (!Array.isArray(raw)) return [];
    const seen = new Set();
    return raw.filter(x => x && typeof x.id === 'string' && typeof x.title === 'string' && x.title.trim() && /^\d{4}-\d{2}-\d{2}$/.test(x.date) && /^https:\/\/stib\.ee\/[A-Za-z0-9_-]+$/.test(x.url)).map(x => {
      let image = '';
      try { const u = new URL(x.image); if (u.protocol === 'https:' && imageHosts.has(u.hostname)) image = u.href; } catch (_) {}
      return {id: x.id, title: x.title, date: x.date, url: x.url, image, volume: Number.isInteger(x.volume) && x.volume > 0 ? x.volume : null};
    }).filter(x => { if (seen.has(x.id)) return false; seen.add(x.id); return true; }).sort((a, b) => b.date.localeCompare(a.date));
  }
  let allItems;
  try { allItems = normalize(JSON.parse(dataNode.textContent)); } catch (_) { return; }
  // New month links go live only after their static pages have been published.
  const publishedMonths = new Set(allItems.map(x => x.date.slice(0,7)));
  let dataset = scoped(allItems);
  if (!dataset.length) return;
  root.dataset.ready = 'true';
  root.querySelector('[data-swa-tools]').removeAttribute('aria-hidden');
  root.querySelector('[data-swa-tools]').removeAttribute('inert');
  root.querySelector('[data-swa-bottom]').hidden = false;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }
  function rebuildMonths() {
    const counts = new Map();
    allItems.forEach(x => counts.set(x.date.slice(0, 7), (counts.get(x.date.slice(0, 7)) || 0) + 1));
    months.replaceChildren();
    [['', allItems.length], ...Array.from(counts.entries()).filter(([key])=>publishedMonths.has(key))].forEach(([key, value]) => {
      const link = element('a', 'swa-month-link');
      link.href = archiveUrl(key);
      if (key === archiveMonth) link.setAttribute('aria-current', 'page');
      link.append(document.createTextNode(key ? monthName(key) : '전체 뉴스레터'), element('span', '', String(value)));
      months.append(link);
    });
    if (structured) structured.textContent = JSON.stringify({'@context':'https://schema.org','@type':'CollectionPage','@id':root.dataset.canonicalUrl+'#archive',name:(archiveMonth ? monthName(archiveMonth)+' ' : '')+'쏘왓레터 모아보기',url:root.dataset.canonicalUrl,inLanguage:'ko-KR',isPartOf:{'@id':archiveBase+'#website'},mainEntity:{'@type':'ItemList',numberOfItems:dataset.length,itemListElement:dataset.map((x,i)=>({'@type':'ListItem',position:i+1,item:{'@type':'CreativeWork',name:x.title,url:x.url,datePublished:x.date,...(x.image ? {image:x.image} : {})}}))}});
  }
  function card(x, index) {
    const article = element('article', 'swa-card');
    if (x.volume) article.id = 'vol-' + x.volume;
    const anchor = element('a');
    anchor.href = x.url;
    anchor.target = '_blank';
    anchor.rel = 'noopener';
    anchor.setAttribute('aria-label', x.title + ' — 스티비 원문 새 창');
    const cover = element('div', 'swa-cover');
    cover.append(element('span', 'swa-cover-fallback', 'SO WHAT?'));
    if (x.image) {
      const image = element('img');
      image.src = x.image;
      image.alt = x.title;
      image.width = 630;
      image.height = 360;
      image.loading = index < 3 ? 'eager' : 'lazy';
      image.decoding = 'async';
      image.addEventListener('error', () => { image.remove(); cover.classList.add('swa-no-image'); }, {once:true});
      cover.append(image);
    } else cover.classList.add('swa-no-image');
    const meta = element('p', 'swa-meta');
    const date = element('time');
    const calendar = element('span');
    calendar.innerHTML = calendarIcon;
    date.append(calendar.firstChild, document.createTextNode(x.date.replace(/-/g, '.')));
    date.dateTime = x.date;
    meta.append(element('span', 'swa-volume', x.volume ? 'Vol. ' + String(x.volume).padStart(3, '0') : 'SO WHAT LETTER'), date);
    const body = element('div', 'swa-card-body');
    const heading = element('h2', '', x.title);
    heading.title = x.title;
    body.append(meta, heading);
    anchor.append(cover, body);
    article.append(anchor);
    return article;
  }
  function render() {
    const query = search.value.trim().toLocaleLowerCase();
    // '115', '115호', 'Vol.115', 'Vol. 115', 'vol115' all mean issue 115.
    const vol = /^(?:vol\.?\s*)?0*(\d{1,4})\s*호?$/i.exec(query);
    const items = dataset.filter(x => !query || (vol && x.volume === Number(vol[1])) || x.title.toLocaleLowerCase().includes(query));
    const fragment = document.createDocumentFragment();
    items.slice(0, limit).forEach((x, i) => fragment.append(card(x, i)));
    grid.replaceChildren(fragment);
    more.hidden = items.length <= limit;
    empty.hidden = items.length !== 0;
  }
  search.addEventListener('input', () => { limit = 9; render(); });
  more.addEventListener('click', () => {
    const firstNew = limit;
    limit += 9;
    render();
    // Mobile: bring the first newly loaded issue to the top of the screen.
    if (window.matchMedia && window.matchMedia('(max-width: 820px)').matches) {
      const target = grid.children[firstNew];
      if (target) {
        const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        window.scrollTo({ top: target.getBoundingClientRect().top + window.scrollY - 16, behavior: reduce ? 'auto' : 'smooth' });
      }
    }
  });
  const menus = Array.from(root.querySelectorAll('details[data-swa-menu]'));
  menus.forEach(menu => menu.addEventListener('toggle', () => { if (menu.open) menus.forEach(other => { if (other !== menu) other.open = false; }); }));
  document.addEventListener('click', event => { menus.forEach(menu => { if (menu.open && !menu.contains(event.target)) menu.open = false; }); });
  document.addEventListener('keydown', event => { if (event.key !== 'Escape') return; menus.forEach(menu => { if (menu.open) { menu.open = false; menu.querySelector('summary').focus(); } }); });
  // Mobile: fixed '뉴스레터 구독하기' bar jumps to the subscribe box and hides while the box or footer is on screen.
  const stickyCta = root.querySelector('[data-swa-sticky-cta]');
  const subscribe = root.querySelector('#sowhat-subscribe-form');
  if (stickyCta && subscribe) {
    stickyCta.addEventListener('click', event => {
      event.preventDefault();
      const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      subscribe.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'center' });
    });
    // Hide while the subscribe box or the footer is on screen (checked on scroll so it never covers them).
    const pageFoot = root.querySelector('.swa-footer');
    const near = el => { if (!el) return false; const r = el.getBoundingClientRect(); return r.top < window.innerHeight + 120 && r.bottom > 0; };
    const updateCta = () => stickyCta.classList.toggle('is-hidden', near(subscribe) || near(pageFoot));
    window.addEventListener('scroll', updateCta, { passive: true });
    window.addEventListener('resize', updateCta, { passive: true });
    updateCta();
    // Samsung Internet / Chrome on Android: while the browser toolbar slides in or out the
    // fixed bar can be drawn partly below the visible screen. Keep it on the visible
    // viewport's bottom edge and re-place it once scrolling stops.
    const vv = window.visualViewport;
    let settle = 0;
    const pinCta = () => {
      const gap = vv ? Math.round(window.innerHeight - vv.height - vv.offsetTop) : 0;
      stickyCta.style.bottom = gap > 0 ? gap + 'px' : '0px';
    };
    const pinLater = () => {
      pinCta();
      clearTimeout(settle);
      settle = setTimeout(() => {
        if (stickyCta.classList.contains('is-hidden')) return;
        stickyCta.style.transform = 'translateZ(0)';
        requestAnimationFrame(() => { stickyCta.style.transform = ''; pinCta(); });
      }, 120);
    };
    if (vv) { vv.addEventListener('resize', pinLater); vv.addEventListener('scroll', pinLater); }
    window.addEventListener('scroll', pinLater, { passive: true });
    window.addEventListener('resize', pinLater, { passive: true });
    pinCta();
  }
  const mobileReader = window.matchMedia ? window.matchMedia('(max-width: 820px)') : null;
  grid.addEventListener('click', event => {
    if (!mobileReader || !mobileReader.matches || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const link = event.target.closest('a[href]');
    const match = link && /^https:\/\/stib\.ee\/([A-Za-z0-9_-]+)$/.exec(link.href);
    if (!match) return;
    event.preventDefault();
    // Remember how far the list was opened so the back bar returns to the same place.
    try { sessionStorage.setItem('swa-return:' + location.pathname, JSON.stringify({ limit, query: search.value, y: window.scrollY, at: Date.now() })); } catch (_) {}
    const sameSite = location.hostname === new URL(archiveBase).hostname || /^(localhost|127\.0\.0\.1)$/.test(location.hostname);
    location.assign((sameSite ? '/' : archiveBase) + 'read/?id=' + encodeURIComponent(match[1]));
  });
  // Mobile: scale the embedded subscribe form (built for 300px) up to the available width.
  const subscribeFrame = subscribe && subscribe.querySelector('iframe');
  if (subscribe && subscribeFrame) {
    const fitSubscribe = () => {
      const mobile = window.matchMedia && window.matchMedia('(max-width: 820px)').matches;
      const layout = subscribe.closest('.swa-layout');
      const pad = layout ? getComputedStyle(layout) : null;
      const avail = layout ? layout.clientWidth - parseFloat(pad.paddingLeft) - parseFloat(pad.paddingRight) : 300;
      const k = mobile ? Math.max(0.85, Math.min(avail / 300, 1.3)) : 1;
      // PC: tell the form to use 24px side padding so it lines up with the intro text (mobile keeps 16px).
      try { subscribeFrame.contentWindow.postMessage({ swaPc: !mobile }, 'https://junggiteam.github.io'); } catch (_) {}
      if (k === 1) {
        subscribe.style.width = subscribe.style.height = '';
        subscribeFrame.style.transform = subscribeFrame.style.transformOrigin = '';
        subscribeFrame.style.margin = '-5px 0 0 -1px';
        return;
      }
      subscribe.style.width = (300 * k) + 'px';
      subscribe.style.height = (277 * k) + 'px';
      subscribeFrame.style.transformOrigin = '0 0';
      subscribeFrame.style.transform = 'scale(' + k + ')';
      subscribeFrame.style.margin = (-5 * k) + 'px 0 0 ' + (-1 * k) + 'px';
    };
    fitSubscribe();
    subscribeFrame.addEventListener('load', fitSubscribe);
    window.addEventListener('resize', fitSubscribe, { passive: true });
  }
  // PC: fit the big title by its visible ink, whatever font the viewer has (Pretendard, Malgun Gothic,
  // Apple SD Gothic Neo...). Each line's first letter starts exactly on the text line and the wider
  // line's last letter ends exactly on the right edge of the intro text and the subscribe form.
  const title = root.querySelector('.swa-intro h1');
  const introBox = root.querySelector('.swa-intro');
  if (title && introBox) {
    const lines = Array.from(title.querySelectorAll('span'));
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const inkOf = (ch, font, size) => {
      canvas.width = Math.ceil(size * 3); canvas.height = Math.ceil(size * 2);
      ctx.font = font; ctx.textBaseline = 'top';
      const ox = Math.round(size);
      ctx.fillText(ch, ox, Math.round(size * 0.3));
      const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
      let min = Infinity, max = -1;
      for (let i = 3; i < data.length; i += 4) {
        if (data[i] > 60) { const x = ((i - 3) / 4) % canvas.width; if (x < min) min = x; if (x > max) max = x; }
      }
      if (max < 0) return { left: 0, right: 0 };
      return { left: min - ox, right: ctx.measureText(ch).width - (max + 1 - ox) };
    };
    const fitTitle = () => {
      const pc = window.matchMedia && window.matchMedia('(min-width: 821px)').matches;
      title.style.fontSize = '';
      title.style.whiteSpace = '';
      lines.forEach(line => { line.style.marginLeft = ''; });
      if (!pc || !lines.length) return;
      // the empty side space of the last letter may stick out past the box; never let a line wrap
      title.style.whiteSpace = 'nowrap';
      const cs = getComputedStyle(introBox);
      const inner = introBox.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
      let size = parseFloat(getComputedStyle(title).fontSize);
      let bearings = [];
      for (let round = 0; round < 4; round++) {
        const ts = getComputedStyle(title);
        const font = ts.fontWeight + ' ' + size + 'px ' + ts.fontFamily;
        const spacing = parseFloat(ts.letterSpacing) || 0;
        bearings = lines.map(line => {
          const text = line.textContent.trim();
          return { first: inkOf(text[0], font, size).left, last: inkOf(text[text.length - 1], font, size).right };
        });
        const widths = lines.map((line, i) => {
          const range = document.createRange(); range.selectNodeContents(line);
          return range.getBoundingClientRect().width - spacing - bearings[i].first - bearings[i].last;
        });
        const widest = Math.max(...widths);
        if (!(widest > 0)) break;
        size = size * inner / widest;
        title.style.fontSize = size.toFixed(2) + 'px';
      }
      lines.forEach((line, i) => { line.style.marginLeft = (-bearings[i].first).toFixed(2) + 'px'; });
    };
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(fitTitle); else fitTitle();
    window.addEventListener('resize', fitTitle, { passive: true });
  }
  // PC: TOP button appears after scrolling down and returns smoothly to the top.
  const toTop = root.querySelector('[data-swa-totop]');
  if (toTop) {
    toTop.hidden = false;
    const pageFooter = root.querySelector('.swa-footer');
    const updateTop = () => {
      toTop.classList.toggle('is-visible', window.scrollY > 400);
      // Lift the button above the footer so it never covers the footer text.
      const overlap = pageFooter ? window.innerHeight - pageFooter.getBoundingClientRect().top : 0;
      toTop.style.bottom = overlap > 0 ? (overlap + 16) + 'px' : '';
    };
    window.addEventListener('resize', updateTop, { passive: true });
    window.addEventListener('scroll', updateTop, { passive: true });
    updateTop();
    toTop.addEventListener('click', event => {
      event.preventDefault();
      const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      window.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' });
    });
  }
  rebuildMonths();
  try {
    const saved = JSON.parse(sessionStorage.getItem('swa-return:' + location.pathname) || 'null');
    if (saved && Date.now() - saved.at < 30 * 60 * 1000) {
      limit = Math.max(9, Math.min(Number(saved.limit) || 9, 200));
      search.value = typeof saved.query === 'string' ? saved.query.slice(0, 60) : '';
      window.addEventListener('load', () => setTimeout(() => window.scrollTo(0, Number(saved.y) || 0), 0), { once: true });
      if (document.readyState === 'complete') setTimeout(() => window.scrollTo(0, Number(saved.y) || 0), 0);
    }
    sessionStorage.removeItem('swa-return:' + location.pathname);
  } catch (_) {}
  // Links like /2026/11/#vol-103 (RSS, shared links): open the list far enough to show that card, then scroll to it.
  const volHash = /^#vol-(\d+)$/.exec(location.hash);
  if (volHash) {
    const at = dataset.findIndex(x => x.volume === Number(volHash[1]));
    if (at >= limit) limit = Math.ceil((at + 1) / 9) * 9;
  }
  render();
  if (volHash) {
    const jump = () => { const target = document.getElementById('vol-' + volHash[1]); if (target) target.scrollIntoView({ block: 'start' }); };
    jump();
    window.addEventListener('load', jump, { once: true });
  }
  currentSignature = JSON.stringify(allItems);

  async function refresh() {
    if (refreshing || Date.now() - lastRefresh < 5 * 60 * 1000) return;
    refreshing = true;
    const bucket = Math.floor(Date.now() / 300000);
    const endpoints = ['https://raw.githubusercontent.com/junggiteam/naver-news/main/data/sowhat_archive.json', 'https://junggiteam.github.io/naver-news/data/sowhat_archive.json'];
    try {
      for (const endpoint of endpoints) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 12000);
        try {
          const response = await fetch(endpoint + '?v=' + bucket, {signal:controller.signal, credentials:'omit'});
          if (!response.ok) throw new Error('Archive unavailable');
          const payload = await response.json();
          const updated = payload.schemaVersion === 1 && payload.source === 'https://page.stibee.com/archives/479387' ? normalize(payload.items) : [];
          if (!updated.length || updated.length < allItems.length * .75 || !scoped(updated).length) throw new Error('Invalid archive response');
          const signature = JSON.stringify(updated);
          if (signature !== currentSignature) {
            allItems = updated;
            dataset = scoped(updated);
            currentSignature = signature;
            rebuildMonths();
            render();
          }
          root.dataset.feedUpdatedAt = payload.updatedAt;
          root.dataset.feedSource = endpoint;
          lastRefresh = Date.now();
          return;
        } catch (_) { /* Keep the server-delivered archive and try the next source. */ }
        finally { clearTimeout(timer); }
      }
    } finally { refreshing = false; }
  }
  refresh();
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
  const poll = setInterval(() => { if (!root.isConnected) clearInterval(poll); else if (!document.hidden) refresh(); }, 5 * 60 * 1000);
})();

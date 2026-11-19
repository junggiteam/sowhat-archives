(() => {
  'use strict';
  // Today's date (Asia/Seoul) and rolling weather for major cities: KMA first, Open-Meteo as a fallback.
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
  const cities = [['서울', 37.5665, 126.978], ['인천', 37.4563, 126.7052], ['대전', 36.3504, 127.3845], ['광주', 35.1595, 126.8526], ['대구', 35.8714, 128.6014], ['울산', 35.5384, 129.3114], ['부산', 35.1796, 129.0756], ['제주', 33.4996, 126.5312]];
  const kmaUrl = 'https://raw.githubusercontent.com/junggiteam/sowhat-archives/weather/weather.json';
  const seoulHour = () => Number(new Intl.DateTimeFormat('en-US', {timeZone: 'Asia/Seoul', hour: 'numeric', hourCycle: 'h23'}).format(new Date()));
  // 기상청 초단기실황·예보 (published to the weather branch by GitHub Actions).
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
  // Fallback when the KMA file is unavailable or stale: keyless Open-Meteo (WMO codes).
  function fromOpenMeteo(payload) {
    const list = Array.isArray(payload) ? payload : [payload];
    return list.map((entry, i) => {
      const current = entry && entry.current;
      const code = Number(current && current.weather_code);
      const day = current && current.is_day !== 0;
      let info = null;
      if (code === 0 || code === 1) info = [day ? 'clear' : 'night', '맑음'];
      else if (code === 2) info = ['partly', '구름많음'];
      else if (code === 3) info = ['cloudy', '흐림'];
      else if (code === 45 || code === 48) info = ['fog', '안개'];
      else if ((code >= 51 && code <= 67) || (code >= 80 && code <= 82)) info = ['rain', '비'];
      else if ((code >= 71 && code <= 77) || code === 85 || code === 86) info = ['snow', '눈'];
      else if (code >= 95 && code <= 99) info = ['thunder', '뇌우'];
      return info && cities[i] && {icon: info[0], label: info[1], temperature: current.temperature_2m, place: cities[i][0]};
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
  const cacheKey = 'swa-weather-v3';
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
    if (!list.length) {
      const lat = cities.map(c => c[1]).join(','), lon = cities.map(c => c[2]).join(',');
      try { list = fromOpenMeteo(await getJson('https://api.open-meteo.com/v1/forecast?latitude=' + lat + '&longitude=' + lon + '&current=temperature_2m,weather_code,is_day&timezone=Asia%2FSeoul')); } catch (_) {}
    }
    if (setViews(list)) { try { localStorage.setItem(cacheKey, JSON.stringify({views: views, at: Date.now()})); } catch (_) {} }
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
    const items = dataset.filter(x => (!query || (x.title + ' ' + (x.volume || '')).toLocaleLowerCase().includes(query)));
    const fragment = document.createDocumentFragment();
    items.slice(0, limit).forEach((x, i) => fragment.append(card(x, i)));
    grid.replaceChildren(fragment);
    more.hidden = items.length <= limit;
    empty.hidden = items.length !== 0;
  }
  search.addEventListener('input', () => { limit = 9; render(); });
  more.addEventListener('click', () => { limit += 9; render(); });
  const monthMenu = root.querySelector('[data-swa-month-menu]');
  if (monthMenu) {
    document.addEventListener('click', event => { if (monthMenu.open && !monthMenu.contains(event.target)) monthMenu.open = false; });
    document.addEventListener('keydown', event => { if (event.key === 'Escape' && monthMenu.open) { monthMenu.open = false; monthMenu.querySelector('summary').focus(); } });
  }
  rebuildMonths();
  render();
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

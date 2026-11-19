
(() => {
  'use strict';
  // Category page: show 10 sections at a time (all are in the HTML for search engines), PC TOP button.
  const root = document.querySelector('#sowhat-archive.swa-category');
  if (!root || root.dataset.catReady) return;
  root.dataset.catReady = 'true';
  const rows = Array.from(root.querySelectorAll('.swa-cat-row'));
  const bottom = root.querySelector('[data-swa-cat-bottom]');
  const more = root.querySelector('[data-swa-cat-more]');
  // Keep the current category tab visible when the tab row scrolls sideways (mobile).
  const tabs = root.querySelector('.swa-cat-tabs');
  const current = tabs && tabs.querySelector('[aria-current=page]');
  if (current && tabs.scrollWidth > tabs.clientWidth) tabs.scrollLeft = Math.max(0, current.offsetLeft - tabs.offsetLeft - 20);
  const STEP = 10;
  let shown = STEP;
  const apply = () => {
    rows.forEach((row, i) => { row.hidden = i >= shown; });
    if (bottom) bottom.hidden = rows.length <= shown;
  };
  apply();
  if (more) more.addEventListener('click', () => {
    const firstNew = shown;
    shown += STEP;
    apply();
    if (window.matchMedia && window.matchMedia('(max-width: 820px)').matches && rows[firstNew]) {
      const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      window.scrollTo({ top: rows[firstNew].getBoundingClientRect().top + window.scrollY - 16, behavior: reduce ? 'auto' : 'smooth' });
    }
  });
  const toTop = root.querySelector('.swa-totop');
  const foot = root.querySelector('.swa-footer');
  if (toTop) {
    toTop.hidden = false;
    const update = () => {
      toTop.classList.toggle('is-visible', window.scrollY > 400);
      const overlap = foot ? window.innerHeight - foot.getBoundingClientRect().top : 0;
      toTop.style.bottom = overlap > 0 ? (overlap + 16) + 'px' : '';
    };
    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update, { passive: true });
    update();
    toTop.addEventListener('click', event => {
      event.preventDefault();
      const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      window.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' });
    });
  }
})();

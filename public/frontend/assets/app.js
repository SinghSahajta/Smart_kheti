
/* ================================================================
   Smart खेती — shared JS 
   ================================================================ */

const q = (selector, parent = document) => parent.querySelector(selector);
const qa = (selector, parent = document) => Array.from(parent.querySelectorAll(selector));

const fetchJSON = async (url, opts = {}) => {
  try {
    const res = await fetch(url, opts);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'API Error');
    return { data, error: null };
  } catch (err) {
    return { data: null, error: err };
  }
};

const showToast = (msg) => {
  let container = q('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = 'toast toast-info neo';
  toast.innerHTML = `<span>ℹ</span> <span>${msg}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.add('toast-out');
    toast.addEventListener('animationend', () => toast.remove());
  }, 3000);
};

const formatDate = (dateString) => {
  if (!dateString) return '--';
  return new Date(dateString).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric'
  });
};

const setActiveNav = (id) => {
  qa('.bottom-nav__item').forEach(item => {
    item.classList.toggle('active', item.getAttribute('href')?.includes(id));
  });
};

const animateRing = (el, valuePercent) => {
  if (!el) return;
  const val = Math.max(0, Math.min(100, Number(valuePercent) || 0));
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  
  if (reducedMotion) {
    el.style.background = `conic-gradient(var(--brand) ${val}%, transparent 0)`;
    return;
  }
  
  let current = 0;
  const duration = 800;
  const start = performance.now();
  
  const step = (now) => {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const easeOutStr = 1 - Math.pow(1 - progress, 3);
    current = val * easeOutStr;
    el.style.background = `conic-gradient(var(--brand) ${current}%, rgba(26,77,46,.1) 0)`;
    
    if (progress < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
};

document.addEventListener('DOMContentLoaded', () => {
  /* Page mount animations */
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const elements = qa('.reveal');
  
  if (reducedMotion) {
    elements.forEach(el => el.classList.add('show'));
  } else {
    elements.forEach((el, index) => {
      setTimeout(() => el.classList.add('show'), 60 * index);
    });
  }

  /* Footer Injection */
  const footerEl = q('#global-footer');
  if (footerEl) {
    const year = new Date().getFullYear();
    footerEl.innerHTML = `
      <div class="footer__inner">
        <div class="footer__top">
          <div class="footer__brand">
            <div class="footer__brand-name">Smart <span class="brand-hi">खेती</span></div>
            <div class="footer__tagline">Crop‑stage AI for Indian farms</div>
          </div>
          <div class="footer__links">
            <a href="#">About</a>
            <a href="#">Privacy</a>
            <a href="#">Terms</a>
            <a href="#">Contact</a>
          </div>
          <div class="flex items-center gap-3">
            <button class="footer__lang-toggle">EN / HI</button>
            <button id="scrollToTopBtn" aria-label="Scroll to top" class="footer__lang-toggle" style="padding: .3rem .6rem;">↑</button>
          </div>
        </div>
        <hr class="footer__divider" />
        <div class="footer__copy">Copyright © Smart खेती ${year}</div>
      </div>
    `;
    const upBtn = q('#scrollToTopBtn', footerEl);
    if (upBtn) {
      upBtn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
    }
    footerEl.className = 'site-footer';
  }
});

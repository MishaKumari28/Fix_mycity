/**
 * FixMyCity — Main App JS
 * Theme toggle, drag-drop, shared utilities
 */

// ── Theme Toggle ──────────────────────────────────────────────────
const THEME_KEY = 'fmc-theme';

function applyTheme(theme) {
  document.documentElement.setAttribute('data-bs-theme', theme);
  const icon = document.getElementById('themeIcon');
  if (icon) {
    icon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
  }
  localStorage.setItem(THEME_KEY, theme);
}

function initTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  const preferred = saved || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  applyTheme(preferred);
}

document.addEventListener('DOMContentLoaded', () => {
  initTheme();

  const btn = document.getElementById('themeToggle');
  if (btn) {
    btn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-bs-theme');
      applyTheme(current === 'dark' ? 'light' : 'dark');
    });
  }
});

// ── Toast notification ────────────────────────────────────────────
function showToast(msg, type = 'success') {
  const existing = document.getElementById('fmcToast');
  if (existing) existing.remove();

  const el = document.createElement('div');
  el.id = 'fmcToast';
  el.className = `toast align-items-center text-bg-${type} border-0 position-fixed bottom-0 end-0 m-3 show`;
  el.setAttribute('role', 'alert');
  el.style.zIndex = 9999;
  el.innerHTML = `
    <div class="d-flex">
      <div class="toast-body fw-medium">${msg}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" onclick="this.closest('.toast').remove()"></button>
    </div>`;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

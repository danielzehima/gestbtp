// GESTBTP - App JS

// ===== API toasts globale : window.toast(message, type) =====
window.toast = function (msg, type = 'info', delay = 4500) {
  let stack = document.getElementById('toastStack');
  if (!stack) {
    stack = document.createElement('div');
    stack.id = 'toastStack';
    stack.className = 'toast-stack';
    document.body.appendChild(stack);
  }
  const icons = { success: 'check-circle', danger: 'exclamation-circle',
                  warning: 'exclamation-circle', info: 'info-circle' };
  const el = document.createElement('div');
  el.className = 'toast-item toast-' + type;
  el.setAttribute('role', 'status');
  el.innerHTML = `<i class="fas fa-${icons[type] || 'info-circle'}"></i><span></span>` +
                 `<button class="toast-close" aria-label="Fermer">&times;</button>`;
  el.querySelector('span').textContent = msg;
  stack.appendChild(el);
  bindToast(el, delay);
};

function bindToast(el, delay = 4500) {
  const close = () => {
    el.classList.add('hide');
    setTimeout(() => el.remove(), 350);
  };
  el.querySelector('.toast-close')?.addEventListener('click', close);
  if (delay) setTimeout(close, delay);
}

document.addEventListener('DOMContentLoaded', () => {
  // Menu mobile
  const toggle = document.querySelector('.menu-toggle');
  const sidebar = document.querySelector('.sidebar');
  if (toggle && sidebar) {
    toggle.addEventListener('click', () => sidebar.classList.toggle('open'));
  }

  // Toasts issus des flash messages serveur (auto-dismiss + fermeture)
  document.querySelectorAll('#toastStack .toast-item').forEach(el => bindToast(el));

  // Ancien format .flash s'il en reste quelque part
  document.querySelectorAll('.flash').forEach(el => {
    setTimeout(() => { el.style.transition = 'opacity .4s'; el.style.opacity = 0;
      setTimeout(() => el.remove(), 400); }, 5000);
  });

  // Confirmation suppression
  document.querySelectorAll('form[data-confirm]').forEach(f => {
    f.addEventListener('submit', e => {
      if (!confirm(f.dataset.confirm)) e.preventDefault();
    });
  });

  // Animation des barres de progression
  document.querySelectorAll('.progress-fill[data-pct]').forEach(el => {
    const pct = parseInt(el.dataset.pct) || 0;
    requestAnimationFrame(() => { el.style.width = pct + '%'; });
    if (pct >= 100) el.classList.add('done');
  });
});

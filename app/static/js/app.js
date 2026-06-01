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
  // ===== Menu mobile : ouverture + fermeture (overlay, lien, Échap) =====
  const toggle = document.querySelector('.menu-toggle');
  const sidebar = document.querySelector('.sidebar');
  if (toggle && sidebar) {
    // Overlay cliquable créé dynamiquement
    let overlay = document.querySelector('.sidebar-overlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.className = 'sidebar-overlay';
      document.body.appendChild(overlay);
    }

    const openSidebar = () => {
      sidebar.classList.add('open');
      overlay.classList.add('show');
      document.body.style.overflow = 'hidden';
    };
    const closeSidebar = () => {
      sidebar.classList.remove('open');
      overlay.classList.remove('show');
      document.body.style.overflow = '';
    };

    toggle.addEventListener('click', (e) => {
      e.stopPropagation();
      sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
    });

    // Clic sur l'overlay (zone vide) -> ferme
    overlay.addEventListener('click', closeSidebar);

    // Clic sur un lien du menu -> ferme (navigation mobile)
    sidebar.querySelectorAll('a').forEach(a => a.addEventListener('click', closeSidebar));

    // Touche Échap -> ferme
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && sidebar.classList.contains('open')) closeSidebar();
    });

    // Si on repasse en grand écran, on réinitialise
    window.addEventListener('resize', () => {
      if (window.innerWidth > 900) closeSidebar();
    });
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

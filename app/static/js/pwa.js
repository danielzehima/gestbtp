// GESTBTP — PWA : enregistrement du service worker + bouton d'installation.

// 1) Enregistrer le service worker (servi à la racine pour un scope complet)
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(() => {});
  });
}

// 2) Bouton "Installer l'application" — DÉPLAÇABLE + fermable
let deferredPrompt = null;

async function doInstall(bar) {
  if (!deferredPrompt) {
    // Prompt déjà consommé ou navigateur ne le déclenche pas (ex: iOS)
    if (window.toast) {
      window.toast("Pour installer : menu du navigateur → « Ajouter à l'écran d'accueil ».", 'info', 6000);
    } else {
      alert("Pour installer l'application : ouvrez le menu de votre navigateur puis « Ajouter à l'écran d'accueil ».");
    }
    return;
  }
  try {
    await deferredPrompt.prompt();
    const choice = await deferredPrompt.userChoice;
    deferredPrompt = null;
    if (choice && choice.outcome === 'accepted') {
      bar.remove();
      if (window.toast) window.toast("Application en cours d'installation…", 'success');
    }
  } catch (err) {
    if (window.toast) window.toast("L'installation n'a pas pu démarrer. Réessayez.", 'danger');
  }
}

function showInstallButton() {
  if (document.getElementById('pwaInstallBar')) return;
  if (localStorage.getItem('pwaInstallDismissed')) return;

  // État du drag (déclaré tôt : utilisé par le clic et le déplacement)
  let startX, startY, origX, origY, dragging = false, dragged = false;

  // Conteneur déplaçable
  const bar = document.createElement('div');
  bar.id = 'pwaInstallBar';
  bar.style.cssText = [
    'position:fixed', 'z-index:4000', 'background:#FF6B00', 'color:#fff',
    'border-radius:999px', 'box-shadow:0 8px 24px rgba(255,107,0,.45)',
    'display:flex', 'align-items:center', 'gap:6px', 'padding:6px 6px 6px 14px',
    'font-weight:600', 'font-size:14px', 'user-select:none', 'touch-action:none',
    'right:20px', 'bottom:20px'
  ].join(';');

  // Poignée de déplacement
  const grip = document.createElement('span');
  grip.innerHTML = '<i class="fas fa-grip-vertical"></i>';
  grip.style.cssText = 'cursor:grab;opacity:.85;padding:0 4px';
  grip.title = 'Déplacer';

  // Action installer
  const action = document.createElement('button');
  action.innerHTML = '<i class="fas fa-download"></i> Installer l\'application';
  action.style.cssText = 'background:none;border:none;color:#fff;font-weight:600;font-size:14px;cursor:pointer;padding:6px 4px;display:flex;align-items:center;gap:8px';
  action.addEventListener('click', (e) => { e.stopPropagation(); if (!dragged) doInstall(bar); });

  // Croix de fermeture
  const close = document.createElement('button');
  close.innerHTML = '&times;';
  close.title = 'Masquer';
  close.style.cssText = 'background:rgba(255,255,255,.25);border:none;color:#fff;width:26px;height:26px;border-radius:50%;font-size:18px;line-height:1;cursor:pointer;flex:0 0 auto';
  close.addEventListener('click', (e) => {
    e.stopPropagation();
    bar.remove();
    localStorage.setItem('pwaInstallDismissed', '1');
  });

  bar.append(grip, action, close);
  document.body.appendChild(bar);

  // ---- Drag (souris + tactile) ----
  function onDown(e) {
    dragging = true; dragged = false;
    const p = e.touches ? e.touches[0] : e;
    const r = bar.getBoundingClientRect();
    // On bascule en positionnement left/top
    bar.style.left = r.left + 'px';
    bar.style.top = r.top + 'px';
    bar.style.right = 'auto';
    bar.style.bottom = 'auto';
    origX = r.left; origY = r.top;
    startX = p.clientX; startY = p.clientY;
    grip.style.cursor = 'grabbing';
    e.preventDefault();
  }
  function onMove(e) {
    if (!dragging) return;
    const p = e.touches ? e.touches[0] : e;
    const dx = p.clientX - startX, dy = p.clientY - startY;
    if (Math.abs(dx) > 4 || Math.abs(dy) > 4) dragged = true;
    let nx = origX + dx, ny = origY + dy;
    // garder dans l'écran
    const w = bar.offsetWidth, h = bar.offsetHeight;
    nx = Math.max(6, Math.min(window.innerWidth - w - 6, nx));
    ny = Math.max(6, Math.min(window.innerHeight - h - 6, ny));
    bar.style.left = nx + 'px';
    bar.style.top = ny + 'px';
  }
  function onUp() {
    dragging = false;
    grip.style.cursor = 'grab';
    // on réinitialise dragged un peu après pour ne pas bloquer un futur clic
    setTimeout(() => { dragged = false; }, 50);
  }

  // Le drag se déclenche UNIQUEMENT depuis la poignée (jamais depuis le bouton
  // Installer, sinon le clic d'installation serait avalé).
  grip.addEventListener('mousedown', onDown);
  grip.addEventListener('touchstart', onDown, { passive: false });
  document.addEventListener('mousemove', onMove);
  document.addEventListener('touchmove', onMove, { passive: false });
  document.addEventListener('mouseup', onUp);
  document.addEventListener('touchend', onUp);
}

// Chrome/Android/Edge : événement déclenché quand l'app est installable
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  showInstallButton();
});

// Une fois installée, on retire le bouton
window.addEventListener('appinstalled', () => {
  document.getElementById('pwaInstallBtn')?.remove();
});

// iOS (Safari) : pas de beforeinstallprompt -> on affiche une astuce une seule fois
(function iosHint() {
  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
  const standalone = window.navigator.standalone === true;
  if (isIOS && !standalone && !localStorage.getItem('iosInstallHintShown')) {
    setTimeout(() => {
      const bar = document.createElement('div');
      bar.style.cssText = [
        'position:fixed', 'bottom:0', 'left:0', 'right:0', 'z-index:4000',
        'background:#111', 'color:#fff', 'padding:14px 16px', 'font-size:13px',
        'display:flex', 'align-items:center', 'gap:10px', 'justify-content:center'
      ].join(';');
      bar.innerHTML = 'Pour installer GESTBTP : appuyez sur <strong>Partager</strong> ' +
        '<i class="fas fa-arrow-up-from-bracket"></i> puis « Sur l\'écran d\'accueil »' +
        ' <span style="margin-left:10px;cursor:pointer;text-decoration:underline" id="iosHintClose">Fermer</span>';
      document.body.appendChild(bar);
      document.getElementById('iosHintClose').addEventListener('click', () => {
        bar.remove(); localStorage.setItem('iosInstallHintShown', '1');
      });
    }, 2500);
  }
})();

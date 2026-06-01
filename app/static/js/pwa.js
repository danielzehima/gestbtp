// GESTBTP — PWA : enregistrement du service worker + bouton d'installation.

// 1) Enregistrer le service worker (servi à la racine pour un scope complet)
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(() => {});
  });
}

// 2) Bouton "Installer l'application"
let deferredPrompt = null;

function showInstallButton() {
  if (document.getElementById('pwaInstallBtn')) return;
  const btn = document.createElement('button');
  btn.id = 'pwaInstallBtn';
  btn.innerHTML = '<i class="fas fa-download"></i> Installer l\'application';
  btn.style.cssText = [
    'position:fixed', 'bottom:20px', 'right:20px', 'z-index:4000',
    'background:#FF6B00', 'color:#fff', 'border:none', 'padding:12px 18px',
    'border-radius:999px', 'font-weight:600', 'font-size:14px', 'cursor:pointer',
    'box-shadow:0 8px 24px rgba(255,107,0,.4)', 'display:flex',
    'align-items:center', 'gap:8px'
  ].join(';');
  btn.addEventListener('click', async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    deferredPrompt = null;
    btn.remove();
    if (outcome === 'accepted' && window.toast) {
      window.toast('Application installée ! Retrouvez GESTBTP sur votre écran d\'accueil.', 'success');
    }
  });
  document.body.appendChild(btn);
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

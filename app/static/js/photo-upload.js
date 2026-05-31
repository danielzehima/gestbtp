// GESTBTP — Compression/redimensionnement des photos AVANT upload.
// Vercel limite le corps des requêtes à ~4,5 Mo : on redimensionne donc
// chaque image côté navigateur pour qu'elle passe sans erreur 413.

async function gbtpResizeImage(file, maxDim = 1600, quality = 0.8) {
  if (!file.type || !file.type.startsWith('image/')) return file;
  let bitmap;
  try {
    bitmap = await createImageBitmap(file);
  } catch (_) {
    return file; // fallback : on envoie l'original
  }
  let { width, height } = bitmap;
  if (width > maxDim || height > maxDim) {
    const r = Math.min(maxDim / width, maxDim / height);
    width = Math.round(width * r);
    height = Math.round(height * r);
  }
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  canvas.getContext('2d').drawImage(bitmap, 0, 0, width, height);
  const blob = await new Promise(res => canvas.toBlob(res, 'image/jpeg', quality));
  if (!blob) return file;
  const name = file.name.replace(/\.[^.]+$/, '') + '.jpg';
  return new File([blob], name, { type: 'image/jpeg' });
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('form[data-photo-upload]').forEach(form => {
    form.addEventListener('submit', async e => {
      const input = form.querySelector('input[type="file"]');
      if (!input || !input.files || !input.files.length) return; // rien à traiter
      e.preventDefault();

      const btn = form.querySelector('button[type="submit"]');
      if (btn) { btn.disabled = true; btn.dataset.old = btn.innerHTML; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Envoi...'; }

      const fd = new FormData(form);
      fd.delete(input.name);
      for (const f of input.files) {
        try {
          const resized = await gbtpResizeImage(f);
          fd.append(input.name, resized, resized.name);
        } catch (_) {
          fd.append(input.name, f, f.name);
        }
      }

      try {
        const resp = await fetch(form.action, { method: 'POST', body: fd });
        if (resp.redirected) { window.location.href = resp.url; return; }
        if (resp.ok) { window.location.reload(); return; }
        throw new Error('HTTP ' + resp.status);
      } catch (err) {
        alert("Échec de l'envoi des photos. Réessayez avec une image plus légère.");
        if (btn) { btn.disabled = false; btn.innerHTML = btn.dataset.old; }
      }
    });
  });
});

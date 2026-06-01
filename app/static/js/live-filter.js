// GESTBTP — Recherche & filtres instantanés (côté client, sans rechargement).
//
// Utilisation : sur un conteneur de recherche, on déclare en data-attributes
// quel champ pilote le filtre et quels éléments filtrer.
//
//   <input data-live-search="#maTable tbody tr" placeholder="Rechercher...">
//   <select data-live-filter="#maTable tbody tr" data-filter-attr="data-statut">
//
// Chaque ligne/carte cible expose son texte (recherche) et, en option, des
// data-attributes pour les filtres (ex: data-statut="en_cours").

(function () {
  'use strict';

  function normalize(s) {
    // toLowerCase + suppression des accents (plage Unicode ̀-ͯ)
    return (s || '').toString().toLowerCase()
      .normalize('NFD').replace(/[̀-ͯ]/g, '');
  }

  // Applique tous les filtres d'un même groupe (même cible)
  function applyFilters(targetSel) {
    const items = document.querySelectorAll(targetSel);
    // Récupère les contrôles liés à cette cible
    const searchEls = document.querySelectorAll(`[data-live-search="${targetSel}"]`);
    const filterEls = document.querySelectorAll(`[data-live-filter="${targetSel}"]`);

    const term = normalize(searchEls.length ? searchEls[0].value : '');
    const activeFilters = [];
    filterEls.forEach(f => {
      if (f.value) activeFilters.push({ attr: f.dataset.filterAttr, val: f.value });
    });

    let visible = 0;
    items.forEach(el => {
      const text = normalize(el.dataset.search || el.textContent);
      let show = !term || text.includes(term);
      for (const f of activeFilters) {
        if ((el.getAttribute(f.attr) || '') !== f.val) { show = false; break; }
      }
      el.style.display = show ? '' : 'none';
      if (show) visible++;
    });

    // Message "aucun résultat" optionnel
    const empty = document.querySelector(`[data-live-empty="${targetSel}"]`);
    if (empty) empty.style.display = visible ? 'none' : '';
  }

  function debounce(fn, ms) {
    let t;
    return function () { clearTimeout(t); t = setTimeout(fn, ms); };
  }

  document.addEventListener('DOMContentLoaded', () => {
    const targets = new Set();
    document.querySelectorAll('[data-live-search]').forEach(e => targets.add(e.dataset.liveSearch));
    document.querySelectorAll('[data-live-filter]').forEach(e => targets.add(e.dataset.liveFilter));

    targets.forEach(target => {
      const run = () => applyFilters(target);
      document.querySelectorAll(`[data-live-search="${target}"]`).forEach(inp => {
        inp.addEventListener('input', debounce(run, 120));
      });
      document.querySelectorAll(`[data-live-filter="${target}"]`).forEach(sel => {
        sel.addEventListener('change', run);
      });
    });
  });
})();

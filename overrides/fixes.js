(function () {
  const PROJECT_RAW_ROOT = 'https://raw.githubusercontent.com/ExoticSytem/NIKKE-Mod-Tracker/main';
  const PROJECT_MANIFEST = `${PROJECT_RAW_ROOT}/assets/characters/manifest.json`;
  let imageRevision = Date.now();
  let projectImages = {};

  async function loadProjectManifest(force=false) {
    try {
      const sep = PROJECT_MANIFEST.includes('?') ? '&' : '?';
      const url = force ? `${PROJECT_MANIFEST}${sep}v=${Date.now()}` : PROJECT_MANIFEST;
      const r = await fetch(url, {cache:'no-store'});
      if (!r.ok) return false;
      const p = await r.json();
      projectImages = p && typeof p.images === 'object' && p.images ? p.images : {};
      return true;
    } catch (_e) {
      return false;
    }
  }

  function ownImageCandidates(c) {
    if (!c) return [];
    const id = String(c.id || '').trim();
    const ver = String(c.version || '').trim();
    if (!id || !ver) return [];
    const key = `${id}_${ver}`;
    const paths = Array.isArray(projectImages[key]) ? projectImages[key] : [];
    return paths.map(path => `${PROJECT_RAW_ROOT}/${String(path).replace(/^\/+/, '')}?v=${imageRevision}`);
  }

  function orderedImages(c) {
    const original = Array.isArray(c && c.images) ? c.images.filter(Boolean) : [];
    const raw = [...original].sort((a,b) => {
      const ar = String(a).includes('raw.githubusercontent.com') ? 0 : 1;
      const br = String(b).includes('raw.githubusercontent.com') ? 0 : 1;
      return ar - br;
    });
    return [...new Set([...ownImageCandidates(c), ...raw])];
  }

  imageHtml = function(c, cls='') {
    const urls = orderedImages(c);
    const cached = nativeCached(c.key);
    const src = cached || urls[0] || '';
    if (!src) return '<div class="placeholder">◇</div>';
    return `<img class="${cls}" loading="lazy" decoding="async" referrerpolicy="no-referrer" src="${esc(src)}" data-key="${esc(c.key)}" data-images='${esc(JSON.stringify(urls))}' data-idx="${cached?-1:0}" onerror="imgFail(this)">`;
  };

  window.imgFail = function(img) {
    let arr = [];
    try { arr = JSON.parse(img.dataset.images || '[]'); } catch (_e) {}
    let i = Number(img.dataset.idx || 0) + 1;
    if (i < arr.length) {
      img.dataset.idx = i;
      img.src = arr[i];
      return;
    }
    if (!img.dataset.nativeTried && window.AndroidBridge) {
      img.dataset.nativeTried = '1';
      try {
        const local = AndroidBridge.cacheImage(img.dataset.key || '', JSON.stringify(arr));
        if (local) { img.src = local; return; }
      } catch (_e) {}
    }
    img.style.display = 'none';
    const p = img.parentElement;
    if (p) {
      p.classList.add('noimg');
      if (!p.querySelector('.placeholder')) p.insertAdjacentHTML('beforeend','<div class="placeholder">◇</div>');
    }
  };

  async function readBundledCatalog() {
    try {
      if (window.AndroidBridge && AndroidBridge.getCatalogJson) {
        const raw = AndroidBridge.getCatalogJson();
        if (raw) return JSON.parse(raw);
      }
    } catch (_e) {}
    const r = await fetch('catalog.json', {cache:'no-store'});
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  }

  function clearNativeImageCache() {
    try {
      if (window.AndroidBridge && AndroidBridge.clearImageCache) AndroidBridge.clearImageCache();
    } catch (_e) {}
    imageRevision = Date.now();
  }

  async function refreshCatalog(showToast) {
    try {
      if (showToast) clearNativeImageCache();
      await loadProjectManifest(!!showToast);
      const p = await readBundledCatalog();
      catalog = Array.isArray(p.characters) ? p.characters : [];
      const info = $('catalogInfo');
      if (info) info.textContent = `${p.count || catalog.length} entradas · ${p.version || ''}`;
      render();
      if (showToast) toast(lang()==='es' ? 'Catálogo e imágenes actualizados' : 'Catalog and images refreshed');
      return true;
    } catch (e) {
      const grid = $('grid');
      if (grid) grid.innerHTML = `<div class="empty">${lang()==='es'?'No se pudo cargar el catálogo':'Could not load catalog'}: ${esc(e.message || e)}</div>`;
      return false;
    }
  }

  function wireButtons() {
    const refresh = $('refreshBtn');
    if (refresh) refresh.onclick = () => refreshCatalog(true);
    const sync = $('syncQuickBtn');
    if (sync) sync.onclick = syncNow;
  }

  function recoverIfNeeded() {
    if (!catalog.length || (($('grid') && $('grid').textContent) || '').includes('Failed to fetch')) {
      refreshCatalog(false);
    } else {
      render();
    }
  }

  wireButtons();
  loadProjectManifest(false).then(ok => { if (ok && catalog.length) render(); });
  recoverIfNeeded();
  setTimeout(recoverIfNeeded, 250);
  setTimeout(recoverIfNeeded, 1000);
})();

(function () {
  const PROJECT_RAW_ROOT = 'https://raw.githubusercontent.com/ExoticSytem/NIKKE-Mod-Tracker/main';
  const PROJECT_MANIFEST = `${PROJECT_RAW_ROOT}/assets/characters/manifest.json`;
  const PROJECT_CLASSIFICATION = `${PROJECT_RAW_ROOT}/admin/catalog_overrides.json`;
  const PROJECT_DISCOVERED = `${PROJECT_RAW_ROOT}/catalog/discovered.json`;
  let imageRevision = Date.now();
  let projectImages = {};
  let adminMeta = {};
  let discoveredCharacters = [];

  async function getJson(url, force=false) {
    try {
      const sep = url.includes('?') ? '&' : '?';
      const target = force ? `${url}${sep}v=${Date.now()}` : url;
      const r = await fetch(target, {cache:'no-store'});
      if (!r.ok) return null;
      return await r.json();
    } catch (_e) { return null; }
  }

  async function loadProjectManifest(force=false) {
    const p = await getJson(PROJECT_MANIFEST, force);
    projectImages = p && typeof p.images === 'object' && p.images ? p.images : {};
    return !!p;
  }

  async function loadProjectClassification(force=false) {
    const p = await getJson(PROJECT_CLASSIFICATION, force);
    const source = p && typeof p.characters === 'object' && p.characters ? p.characters : {};
    const next = {};
    Object.entries(source).forEach(([key, meta]) => {
      if (!meta || typeof meta !== 'object') return;
      const row = {};
      if (typeof meta.npc_extra === 'boolean') row.npc_extra = meta.npc_extra;
      if (meta.status === 'approved' || meta.status === 'discarded') row.status = meta.status;
      if (Object.keys(row).length) next[key] = row;
    });
    adminMeta = next;
    return !!p;
  }

  async function loadDiscoveredCatalog(force=false) {
    const p = await getJson(PROJECT_DISCOVERED, force);
    discoveredCharacters = Array.isArray(p && p.characters) ? p.characters : [];
    return !!p;
  }

  function isApprovedDiscovered(raw, key) {
    const meta = adminMeta[key] || {};
    if (meta.status === 'discarded') return false;
    if (!raw || !raw.needs_review) return true;
    return meta.status === 'approved' || typeof meta.npc_extra === 'boolean';
  }

  function mergeDiscovered(base) {
    const out = Array.isArray(base) ? base.map(x => x) : [];
    const keys = new Set(out.map(x => x && x.key).filter(Boolean));
    for (const raw of discoveredCharacters) {
      if (!raw || typeof raw !== 'object') continue;
      const id = String(raw.id || '').trim();
      const version = String(raw.version || '00').padStart(2, '0');
      const key = String(raw.key || `${id}_${version}`);
      const name = String(raw.name || '').trim();
      if (!id || !name || keys.has(key) || !isApprovedDiscovered(raw, key)) continue;
      const meta = adminMeta[key] || {};
      out.push({id, version, key, name, npcExtra:typeof meta.npc_extra==='boolean'?meta.npc_extra:false, catalogSource:'project_online', images:[]});
      keys.add(key);
    }
    return out;
  }

  npcOf = function(c) {
    if (!c) return false;
    const meta = adminMeta[c.key];
    if (meta && typeof meta.npc_extra === 'boolean') return !!meta.npc_extra;
    const synced = syncState && syncState.inventory ? syncState.inventory[c.key] : null;
    if (synced && typeof synced.is_npc_extra === 'boolean') return synced.is_npc_extra;
    return !!c.npcExtra;
  };

  function ownImageCandidates(c) {
    if (!c) return [];
    const id = String(c.id || '').trim(), ver = String(c.version || '').trim();
    if (!id || !ver) return [];
    const paths = Array.isArray(projectImages[`${id}_${ver}`]) ? projectImages[`${id}_${ver}`] : [];
    return paths.map(path => `${PROJECT_RAW_ROOT}/${String(path).replace(/^\/+/, '')}?v=${imageRevision}`);
  }

  function orderedImages(c) {
    const original = Array.isArray(c && c.images) ? c.images.filter(Boolean) : [];
    const raw = [...original].sort((a,b) => (String(a).includes('raw.githubusercontent.com')?0:1) - (String(b).includes('raw.githubusercontent.com')?0:1));
    return [...new Set([...ownImageCandidates(c), ...raw])];
  }

  imageHtml = function(c, cls='') {
    const urls = orderedImages(c), cached = nativeCached(c.key), src = cached || urls[0] || '';
    if (!src) return '<div class="placeholder">◇</div>';
    return `<img class="${cls}" loading="lazy" decoding="async" referrerpolicy="no-referrer" src="${esc(src)}" data-key="${esc(c.key)}" data-images='${esc(JSON.stringify(urls))}' data-idx="${cached?-1:0}" onerror="imgFail(this)">`;
  };

  window.imgFail = function(img) {
    let arr=[]; try { arr=JSON.parse(img.dataset.images||'[]'); } catch (_e) {}
    const i=Number(img.dataset.idx||0)+1;
    if (i<arr.length) { img.dataset.idx=i; img.src=arr[i]; return; }
    if (!img.dataset.nativeTried && window.AndroidBridge) {
      img.dataset.nativeTried='1';
      try { const local=AndroidBridge.cacheImage(img.dataset.key||'', JSON.stringify(arr)); if(local){img.src=local;return;} } catch (_e) {}
    }
    img.style.display='none'; const p=img.parentElement;
    if(p){p.classList.add('noimg');if(!p.querySelector('.placeholder'))p.insertAdjacentHTML('beforeend','<div class="placeholder">◇</div>');}
  };

  async function readBundledCatalog() {
    try { if(window.AndroidBridge&&AndroidBridge.getCatalogJson){const raw=AndroidBridge.getCatalogJson();if(raw)return JSON.parse(raw);} } catch (_e) {}
    const r=await fetch('catalog.json',{cache:'no-store'}); if(!r.ok)throw new Error(`HTTP ${r.status}`); return await r.json();
  }

  function clearNativeImageCache(){try{if(window.AndroidBridge&&AndroidBridge.clearImageCache)AndroidBridge.clearImageCache();}catch(_e){} imageRevision=Date.now();}

  async function refreshCatalog(showToast) {
    try {
      if(showToast)clearNativeImageCache();
      await Promise.all([loadProjectManifest(!!showToast),loadProjectClassification(!!showToast),loadDiscoveredCatalog(!!showToast)]);
      const p=await readBundledCatalog(); catalog=mergeDiscovered(Array.isArray(p.characters)?p.characters:[]);
      const info=$('catalogInfo'); if(info)info.textContent=`${catalog.length} entradas · ${p.version||p.catalog_version||''}`;
      render(); if(showToast)toast(lang()==='es'?'Catálogo e imágenes actualizados':'Catalog and images refreshed'); return true;
    } catch(e) {
      const grid=$('grid');if(grid)grid.innerHTML=`<div class="empty">${lang()==='es'?'No se pudo cargar el catálogo':'Could not load catalog'}: ${esc(e.message||e)}</div>`; return false;
    }
  }

  openDetail = function(k) {
    current=catalog.find(c=>c.key===k); if(!current)return; const d=data(k);
    $('detailName').textContent=current.name; $('detailId').textContent=`ID ${current.id} · Ver ${current.version}`;
    const wrap=$('detailImg').parentElement; wrap.innerHTML=imageHtml(current,'detailimage'); if(wrap.firstElementChild)wrap.firstElementChild.id='detailImg';
    $('npcBadge').innerHTML=npcOf(current)?'<span class="npc">NPC / Extra</span>':''; $('notes').value=d.notes||'';
    renderActions(); renderSyncedMods(); renderDetailTags(); $('modal').classList.remove('hidden');
  };

  function showLanguageOnboarding() {
    if(localStorage.getItem('nikkeLang'))return;
    const style=document.createElement('style');style.textContent=`.firstlang{position:fixed;inset:0;z-index:9999;background:#090b10ee;display:grid;place-items:center;padding:24px}.firstlang-card{width:min(440px,100%);background:#151a24;border:1px solid #30394a;border-radius:22px;padding:25px;box-shadow:0 28px 70px #000a;text-align:center}.firstlang-logo{font-weight:900;font-size:25px;letter-spacing:.04em}.firstlang-logo span{color:#ffcc33;font-size:13px}.firstlang-card h2{margin:24px 0 8px}.firstlang-card p{color:#aeb6c5;line-height:1.5;margin:0 0 22px}.firstlang-actions{display:grid;grid-template-columns:1fr 1fr;gap:10px}.firstlang-actions button{padding:15px;border-radius:13px;border:1px solid #384255;background:#222937;color:white;font-weight:800;font-size:16px}.firstlang-actions button:first-child{background:#ffcc33;color:#17130a;border-color:#ffcc33}`;document.head.appendChild(style);
    const layer=document.createElement('div');layer.className='firstlang';layer.innerHTML=`<div class="firstlang-card"><div class="firstlang-logo">NIKKE <span>MOD TRACKER</span></div><h2>Idioma / Language</h2><p>Elige el idioma de la interfaz.<br>Choose the interface language.</p><div class="firstlang-actions"><button data-lang="es">Español</button><button data-lang="en">English</button></div></div>`;document.body.appendChild(layer);
    layer.querySelectorAll('button').forEach(btn=>btn.onclick=()=>{localStorage.setItem('nikkeLang',btn.dataset.lang);layer.remove();try{applyLanguage();}catch(_e){}try{render();}catch(_e){}});
  }

  function wireButtons(){const refresh=$('refreshBtn');if(refresh)refresh.onclick=()=>refreshCatalog(true);const sync=$('syncQuickBtn');if(sync)sync.onclick=syncNow;}
  function recoverIfNeeded(){if(!catalog.length||(($('grid')&&$('grid').textContent)||'').includes('Failed to fetch'))refreshCatalog(false);else{catalog=mergeDiscovered(catalog);render();}}

  wireButtons(); showLanguageOnboarding();
  Promise.all([loadProjectManifest(false),loadProjectClassification(false),loadDiscoveredCatalog(false)]).then(()=>{if(catalog.length){catalog=mergeDiscovered(catalog);render();}});
  recoverIfNeeded(); setTimeout(recoverIfNeeded,250); setTimeout(recoverIfNeeded,1000);
})();

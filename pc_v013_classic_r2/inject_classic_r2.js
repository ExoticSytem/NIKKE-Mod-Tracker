(() => {
  if (window.__NMM_CLASSIC_R2__) return;
  window.__NMM_CLASSIC_R2__ = true;

  const API = 'http://127.0.0.1:8138';
  const sessions = new Map();
  const sleep = ms => new Promise(r => setTimeout(r, ms));

  function findPath(text) {
    const hits = String(text || '').match(/[A-Za-z]:\\[^\r\n]+/g);
    if (!hits || !hits.length) return null;
    return hits.sort((a, b) => b.length - a.length)[0].trim();
  }

  function renameManager() {
    try {
      document.title = document.title.replace(/NIKKE\s+Mod\s+Library/gi, 'NIKKE Mod Manager');
      const root = document.body || document.documentElement;
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      let node, seen = 0;
      while ((node = walker.nextNode()) && seen++ < 3500) {
        const v = node.nodeValue || '';
        if (/NIKKE\s+MOD\s+LIBRARY/i.test(v) || /NIKKE\s+Mod\s+Library/i.test(v)) {
          node.nodeValue = v
            .replace(/NIKKE\s+MOD\s+LIBRARY/gi, 'NIKKE MOD MANAGER')
            .replace(/NIKKE\s+Mod\s+Library/gi, 'NIKKE Mod Manager');
        }
      }
    } catch (_) {}
  }

  function hideImageAdmin() {
    const re = /^(agregar|añadir|cambiar|subir|reemplazar|eliminar)\s+imagen|^(add|change|upload|replace|remove)\s+image/i;
    document.querySelectorAll('button,a,[role="button"]').forEach(el => {
      const t = (el.textContent || '').trim();
      if (re.test(t)) el.style.display = 'none';
    });
  }

  function visibleRect(el) {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || Number(s.opacity || 1) === 0) return null;
    if (r.width < 20 || r.height < 20) return null;
    return r;
  }

  function findAlphaModal() {
    const matches = [];
    document.querySelectorAll('body *').forEach(el => {
      const text = el.innerText || '';
      if (!text.includes('Preview Alpha')) return;
      if (!/ARCHIVO DEL BUNDLE|BUNDLE FILE|Unity bundle|TEXTURA|TEXTURE/i.test(text)) return;
      const r = visibleRect(el);
      if (!r || r.width < 450 || r.height < 300) return;
      matches.push({el, area:r.width*r.height});
    });
    matches.sort((a,b)=>a.area-b.area);
    return matches.length ? matches[0].el : null;
  }

  function findPreviewImage(modal) {
    const imgs = [...modal.querySelectorAll('img')]
      .map(img => ({img, r:visibleRect(img)}))
      .filter(x => x.r && x.r.width >= 300 && x.r.height >= 180)
      .sort((a,b)=>(b.r.width*b.r.height)-(a.r.width*a.r.height));
    return imgs.length ? imgs[0].img : null;
  }

  function statusBadge(parent, text, error=false) {
    const d = document.createElement('div');
    d.className = 'nmm-r2-status';
    d.textContent = text;
    Object.assign(d.style, {
      position:'absolute', left:'12px', top:'12px', zIndex:'12', pointerEvents:'none',
      padding:'6px 9px', borderRadius:'999px', fontSize:'11px', fontWeight:'800',
      color:error ? '#fecaca' : '#fde68a',
      background:error ? 'rgba(69,10,10,.88)' : 'rgba(58,45,8,.88)',
      border:'1px solid ' + (error ? '#7f1d1d' : '#8a6813'),
      boxShadow:'0 4px 15px rgba(0,0,0,.25)'
    });
    parent.appendChild(d);
    return d;
  }

  async function prepare(path) {
    let last = null;
    for (let i=0;i<12;i++) {
      try {
        const r = await fetch(API + '/api/prepare?path=' + encodeURIComponent(path), {cache:'no-store'});
        const j = await r.json();
        if (!r.ok || j.error) throw new Error(j.error || 'No se pudo preparar el mod');
        return j;
      } catch (e) {
        last = e;
        await sleep(i < 4 ? 300 : 550);
      }
    }
    throw last || new Error('El motor de preview no respondió.');
  }

  function button(text, onClick, accent=false) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = text;
    Object.assign(b.style, {
      border:'1px solid ' + (accent ? '#9a7615' : '#3a4a60'),
      background:accent ? 'rgba(58,45,8,.95)' : 'rgba(15,23,37,.95)',
      color:accent ? '#fde68a' : '#e5e7eb', borderRadius:'7px', padding:'6px 9px',
      fontSize:'11px', fontWeight:'700', cursor:'pointer'
    });
    b.addEventListener('click', e => { e.preventDefault(); e.stopPropagation(); onClick(); });
    return b;
  }

  function animationChoice(names, action) {
    const prefs = action === 'aim'
      ? ['aim_idle','aim','idle']
      : action === 'cover'
        ? ['cover_idle','cover','idle']
        : ['idle','normal_idle','standing','wait'];
    for (const p of prefs) {
      const exact = names.find(n => n.toLowerCase() === p);
      if (exact) return exact;
      const part = names.find(n => n.toLowerCase().includes(p));
      if (part) return part;
    }
    return names[0] || '';
  }

  async function mountSpine(modal, image, path, manifest, badge) {
    if (!(window.PIXI && window.PIXI.spine)) throw new Error('El runtime Spine local no cargó.');
    if (manifest.type !== 'spine') throw new Error('Este mod no contiene un set Spine completo.');

    const parent = image.parentElement;
    if (!parent) throw new Error('No pude localizar el área de preview.');
    if (getComputedStyle(parent).position === 'static') parent.style.position = 'relative';

    const host = document.createElement('div');
    host.className = 'nmm-r2-spine-host';
    Object.assign(host.style, {
      position:'absolute', inset:'0', zIndex:'7', overflow:'hidden',
      background:'#05080d'
    });

    const controls = document.createElement('div');
    Object.assign(controls.style, {
      position:'absolute', left:'10px', right:'10px', bottom:'10px', zIndex:'11',
      minHeight:'42px', display:'flex', alignItems:'center', gap:'6px', flexWrap:'wrap',
      padding:'7px 8px', borderRadius:'9px', background:'rgba(11,18,32,.92)',
      border:'1px solid rgba(71,85,105,.75)', backdropFilter:'blur(5px)'
    });

    const canvasHost = document.createElement('div');
    Object.assign(canvasHost.style,{position:'absolute',inset:'0'});
    host.append(canvasHost, controls);
    parent.appendChild(host);

    const oldVisibility = image.style.visibility;
    image.style.visibility = 'hidden';

    const app = new PIXI.Application({
      width:Math.max(1, canvasHost.clientWidth), height:Math.max(1, canvasHost.clientHeight),
      backgroundAlpha:0, antialias:true, autoDensity:true,
      resolution:Math.min(window.devicePixelRatio || 1, 2)
    });
    app.view.style.width='100%'; app.view.style.height='100%'; app.view.style.display='block';
    canvasHost.appendChild(app.view);

    const base = API + '/asset/' + manifest.token + '/';
    const loader = new PIXI.Loader();
    loader.add('nikke_r2', base + manifest.skel, {metadata:{spineAtlasFile:base + manifest.atlas}});
    const model = await new Promise((resolve,reject) => {
      loader.onError.add(err => reject(err instanceof Error ? err : new Error(String(err))));
      loader.load((_ldr,res) => {
        try {
          if (!res.nikke_r2 || !res.nikke_r2.spineData) throw new Error('El loader no obtuvo spineData.');
          const m = new PIXI.spine.Spine(res.nikke_r2.spineData);
          app.stage.addChild(m);
          resolve(m);
        } catch (e) { reject(e); }
      });
    });

    try { model.skeleton.setToSetupPose(); model.update(0); } catch (_) {}

    let paused=false, drag=false, lx=0, ly=0;
    const fit = () => {
      const w=Math.max(1,canvasHost.clientWidth), h=Math.max(1,canvasHost.clientHeight);
      app.renderer.resize(w,h);
      let b;
      try { b=model.getLocalBounds(); } catch (_) { b=model.getBounds(); }
      const bw=Math.max(1,b.width), bh=Math.max(1,b.height);
      const scale=Math.min(w/bw,h/bh)*0.86;
      model.scale.set(scale);
      model.x=w/2-(b.x+b.width/2)*scale;
      model.y=h/2-(b.y+b.height/2)*scale;
    };

    const names=(model.spineData?.animations || []).map(a=>a.name);
    const select=document.createElement('select');
    Object.assign(select.style,{minWidth:'180px',maxWidth:'280px',background:'#111c2d',color:'#e5e7eb',border:'1px solid #415168',borderRadius:'7px',padding:'6px',fontSize:'11px'});
    if (names.length) {
      names.forEach(n=>{const o=document.createElement('option');o.value=n;o.textContent=n;select.appendChild(o);});
    } else {
      const o=document.createElement('option');o.textContent='Pose base';o.value='';select.appendChild(o);select.disabled=true;
    }

    const pause=button('⏸ Pausa',()=>{
      paused=!paused;
      model.state.timeScale=paused?0:1;
      pause.textContent=paused?'▶ Reanudar':'⏸ Pausa';
    });
    const minus=button('−',()=>model.scale.set(model.scale.x/1.12));
    const plus=button('+',()=>model.scale.set(model.scale.x*1.12));
    const reset=button('↺ Ajustar',fit);
    const texture=button('Ver textura',()=>{
      const showing = host.style.display !== 'none';
      if (showing) { host.style.display='none'; image.style.visibility=oldVisibility || 'visible'; texture.textContent='Ver armado'; }
      else { host.style.display='block'; image.style.visibility='hidden'; texture.textContent='Ver textura'; }
    });
    const info=document.createElement('span');
    info.textContent='Personaje armado · Spine ' + (manifest.spineVersion || '?');
    Object.assign(info.style,{marginLeft:'auto',fontSize:'10px',color:'#94a3b8',whiteSpace:'nowrap'});
    controls.append(pause, select, reset, minus, plus, texture, info);

    const initial=animationChoice(names, manifest.action || '');
    if (initial) {
      select.value=initial;
      model.state.setAnimation(0,initial,true);
    }
    select.onchange=()=>{if(select.value)model.state.setAnimation(0,select.value,true);};

    fit();
    const ro = new ResizeObserver(fit); ro.observe(canvasHost);
    app.view.addEventListener('pointerdown',e=>{drag=true;lx=e.clientX;ly=e.clientY;});
    app.view.addEventListener('pointermove',e=>{if(!drag)return;model.x+=e.clientX-lx;model.y+=e.clientY-ly;lx=e.clientX;ly=e.clientY;});
    app.view.addEventListener('pointerup',()=>drag=false);
    app.view.addEventListener('pointerleave',()=>drag=false);
    app.view.addEventListener('wheel',e=>{e.preventDefault();model.scale.set(model.scale.x*(e.deltaY<0?1.08:.92));},{passive:false});

    if (badge) badge.remove();
    const ok=statusBadge(parent,'✓ Personaje armado');
    setTimeout(()=>{try{ok.remove();}catch(_){}},2300);

    sessions.set(modal, {
      cleanup:()=>{
        try{ro.disconnect();}catch(_){}
        try{app.destroy(true,{children:true,texture:false,baseTexture:false});}catch(_){}
        try{host.remove();}catch(_){}
        try{image.style.visibility=oldVisibility;}catch(_){}
      }
    });
  }

  async function enhance(modal) {
    if (!modal || modal.dataset.nmmR2 === '1') return;
    const text=modal.innerText || '';
    const path=findPath(text);
    if (!path) return;
    if (/3dmigoto/i.test(path)) return; // R2 se concentra solo en mods normales.
    const image=findPreviewImage(modal);
    if (!image) return;

    modal.dataset.nmmR2='1';
    const parent=image.parentElement;
    if (!parent) { delete modal.dataset.nmmR2; return; }
    if (getComputedStyle(parent).position === 'static') parent.style.position='relative';
    const badge=statusBadge(parent,'Armando personaje…');

    try {
      const manifest=await prepare(path);
      await mountSpine(modal,image,path,manifest,badge);
    } catch (e) {
      try{badge.textContent='No se pudo armar · se mantiene la textura';badge.style.color='#fecaca';badge.style.borderColor='#7f1d1d';badge.style.background='rgba(69,10,10,.88)';}catch(_){}
      setTimeout(()=>{try{badge.remove();}catch(_){}},4000);
      modal.dataset.nmmR2='failed';
      console.warn('[NMM R2] Preview Spine:',e);
    }
  }

  function cleanupClosed() {
    for (const [modal,session] of sessions.entries()) {
      if (!document.contains(modal)) {
        try{session.cleanup();}catch(_){}
        sessions.delete(modal);
      }
    }
  }

  function tick() {
    renameManager(); hideImageAdmin(); cleanupClosed();
    const modal=findAlphaModal();
    if (modal) enhance(modal);
  }

  const heartbeat=()=>fetch(API+'/api/heartbeat',{cache:'no-store',mode:'no-cors'}).catch(()=>{});
  heartbeat(); setInterval(heartbeat,1500);
  new MutationObserver(()=>tick()).observe(document.documentElement,{subtree:true,childList:true,characterData:true});
  setInterval(tick,650);
  tick();
})();

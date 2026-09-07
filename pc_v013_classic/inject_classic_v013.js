(() => {
  if (window.__NMM_CLASSIC_V013__) return;
  window.__NMM_CLASSIC_V013__ = true;

  const API = 'http://127.0.0.1:8137';
  const sessions = new WeakMap();

  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  function findPath(text) {
    const hits = String(text || '').match(/[A-Za-z]:\\[^\r\n]+/g);
    if (!hits || !hits.length) return null;
    return hits.sort((a,b)=>b.length-a.length)[0].trim();
  }

  function renameManager() {
    try {
      document.title = document.title.replace(/NIKKE\s+Mod\s+Library/gi, 'NIKKE Mod Manager');
      const walker = document.createTreeWalker(document.body || document.documentElement, NodeFilter.SHOW_TEXT);
      let n, count = 0;
      while ((n = walker.nextNode()) && count < 2500) {
        count++;
        const v = n.nodeValue || '';
        if (/NIKKE\s+MOD\s+LIBRARY/i.test(v) || /NIKKE\s+Mod\s+Library/i.test(v)) {
          n.nodeValue = v.replace(/NIKKE\s+MOD\s+LIBRARY/gi, 'NIKKE MOD MANAGER').replace(/NIKKE\s+Mod\s+Library/gi, 'NIKKE Mod Manager');
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

  async function ensureRuntime() {
    if (window.PIXI && window.PIXI.spine) return;
    const load = src => new Promise((resolve,reject) => {
      const old = [...document.scripts].find(s => s.src === src);
      if (old) { if (window.PIXI && window.PIXI.spine) resolve(); else old.addEventListener('load', resolve, {once:true}); return; }
      const s = document.createElement('script');
      s.src = src; s.async = true; s.onload = resolve; s.onerror = () => reject(new Error('No se pudo cargar el runtime de animación.'));
      document.head.appendChild(s);
    });
    if (!window.PIXI) await load('https://cdnjs.cloudflare.com/ajax/libs/pixi.js/6.5.10/browser/pixi.min.js');
    if (!(window.PIXI && window.PIXI.spine)) await load('https://cdn.jsdelivr.net/npm/pixi-spine@4.0.4/dist/pixi-spine.umd.js');
    if (!(window.PIXI && window.PIXI.spine)) throw new Error('Pixi/Spine no quedó disponible.');
  }

  async function apiPrepare(path) {
    let last;
    for (let i=0;i<16;i++) {
      try {
        const r = await fetch(API + '/api/prepare?path=' + encodeURIComponent(path), {cache:'no-store'});
        const j = await r.json();
        if (!r.ok || j.error) throw new Error(j.error || 'Error preparando el mod');
        return j;
      } catch (e) {
        last = e;
        await sleep(i < 5 ? 350 : 650);
      }
    }
    throw last || new Error('El motor de preview no respondió.');
  }

  function makeButton(text, fn, accent=false) {
    const b = document.createElement('button');
    b.type='button'; b.textContent=text;
    Object.assign(b.style, {
      border:'1px solid ' + (accent ? '#b78a14' : '#334155'), borderRadius:'8px', padding:'7px 10px',
      background:accent ? '#3a2d08' : '#172033', color:accent ? '#fde68a' : '#e5e7eb',
      cursor:'pointer', fontWeight:'700', fontSize:'12px'
    });
    b.onclick = e => { e.preventDefault(); e.stopPropagation(); fn(); };
    return b;
  }

  function createShell(modal, path) {
    const old = modal.querySelector(':scope > .nmm-v013-classic-panel');
    if (old) old.remove();
    if (getComputedStyle(modal).position === 'static') modal.style.position='relative';

    const panel=document.createElement('div');
    panel.className='nmm-v013-classic-panel';
    Object.assign(panel.style, {
      position:'absolute', left:'14px', right:'14px', top:'78px', bottom:'14px', zIndex:'40',
      background:'#08101c', border:'1px solid #26354a', borderRadius:'12px', overflow:'hidden',
      boxShadow:'0 14px 40px rgba(0,0,0,.35)', display:'grid', gridTemplateRows:'auto 1fr auto'
    });

    const top=document.createElement('div');
    Object.assign(top.style,{minHeight:'42px',background:'#0f1725',borderBottom:'1px solid #26354a',display:'flex',alignItems:'center',gap:'7px',padding:'7px 10px'});
    const badge=document.createElement('span'); badge.textContent='Preview v0.13';
    Object.assign(badge.style,{fontSize:'11px',fontWeight:'900',color:'#facc15',marginRight:'6px'});
    const tabs=document.createElement('div'); Object.assign(tabs.style,{display:'flex',gap:'6px',flex:'1'});
    const useAlpha=makeButton('Usar Alpha',()=>panel.remove());
    useAlpha.title='Volver temporalmente al preview original';
    top.append(badge,tabs,useAlpha);

    const stage=document.createElement('div');
    Object.assign(stage.style,{position:'relative',minHeight:'0',overflow:'hidden',background:'radial-gradient(circle at 50% 42%,#172033 0,#080d16 60%,#05080d 100%)'});
    const msg=document.createElement('div'); msg.textContent='Preparando vista previa…';
    Object.assign(msg.style,{position:'absolute',inset:'0',display:'flex',alignItems:'center',justifyContent:'center',padding:'24px',textAlign:'center',color:'#cbd5e1',fontWeight:'700'});
    stage.appendChild(msg);

    const foot=document.createElement('div');
    Object.assign(foot.style,{minHeight:'50px',background:'#0f1725',borderTop:'1px solid #26354a',display:'flex',alignItems:'center',gap:'7px',padding:'7px 10px',flexWrap:'wrap'});

    panel.append(top,stage,foot); modal.appendChild(panel);
    return {panel,top,tabs,stage,msg,foot,path};
  }

  function relatedTabs(shell, manifest, currentPath) {
    shell.tabs.innerHTML='';
    const rel=manifest.related || {};
    ['standing','aim','cover'].forEach(act=>{
      if(!rel[act]) return;
      const b=makeButton(act[0].toUpperCase()+act.slice(1),()=>renderPath(shell,rel[act]));
      if (String(rel[act]).toLowerCase() === String(currentPath).toLowerCase()) {
        b.style.borderColor='#b78a14'; b.style.color='#fde68a'; b.style.background='#3a2d08';
      }
      shell.tabs.appendChild(b);
    });
  }

  function showError(shell, text) {
    shell.stage.innerHTML='';
    const d=document.createElement('div');
    Object.assign(d.style,{position:'absolute',inset:'0',display:'flex',alignItems:'center',justifyContent:'center',padding:'30px',textAlign:'center',color:'#fecaca',whiteSpace:'pre-wrap'});
    d.textContent='No se pudo montar la vista previa mejorada.\n\n'+text+'\n\nPuedes pulsar “Usar Alpha” para ver el preview original.';
    shell.stage.appendChild(d); shell.foot.innerHTML='';
  }

  function staticPreview(shell,m) {
    const images=(m.images||[]).slice().sort((a,b)=>(b.area||0)-(a.area||0));
    shell.stage.innerHTML=''; shell.foot.innerHTML='';
    if(!images.length) { showError(shell,m.note || 'No encontré una textura utilizable.'); return; }
    const img=document.createElement('img');
    Object.assign(img.style,{width:'100%',height:'100%',objectFit:'contain',display:'block',transformOrigin:'50% 50%',userSelect:'none'});
    shell.stage.appendChild(img);
    let zoom=1, idx=0;
    const sel=document.createElement('select');
    Object.assign(sel.style,{minWidth:'260px',maxWidth:'48%',background:'#172033',color:'#e5e7eb',border:'1px solid #334155',borderRadius:'8px',padding:'7px'});
    images.forEach((im,i)=>{const o=document.createElement('option');o.value=String(i);o.textContent=(im.sourceName||im.name||('Textura '+(i+1)))+' · '+(im.width||'?')+'×'+(im.height||'?');sel.appendChild(o);});
    const setImage=()=>{idx=Number(sel.value)||0;const im=images[idx];img.src=API+'/asset/'+m.token+'/'+encodeURIComponent(im.name);zoom=1;img.style.transform='scale(1)';};
    sel.onchange=setImage;
    shell.foot.append(sel,makeButton('−',()=>{zoom/=1.12;img.style.transform='scale('+zoom+')';}),makeButton('+',()=>{zoom*=1.12;img.style.transform='scale('+zoom+')';}),makeButton('↺ Ajustar',()=>{zoom=1;img.style.transform='scale(1)';}));
    const note=document.createElement('span'); note.textContent=m.unityVersionRepaired?'3DMigoto · cabecera Unity reparada en memoria':'3DMigoto · vista estática';
    Object.assign(note.style,{marginLeft:'auto',fontSize:'11px',color:'#94a3b8'}); shell.foot.appendChild(note);
    setImage();
  }

  async function spinePreview(shell,m) {
    shell.stage.innerHTML=''; shell.foot.innerHTML='';
    await ensureRuntime();
    const host=document.createElement('div');Object.assign(host.style,{position:'absolute',inset:'0'});shell.stage.appendChild(host);
    const app=new PIXI.Application({width:Math.max(1,host.clientWidth),height:Math.max(1,host.clientHeight),transparent:true,antialias:true,autoDensity:true,resolution:Math.min(devicePixelRatio||1,2)});
    host.appendChild(app.view);
    const base=API+'/asset/'+m.token+'/';
    const loader=new PIXI.Loader();
    loader.add('nikke',base+m.skel,{metadata:{spineAtlasFile:base+m.atlas}});
    const model=await new Promise((resolve,reject)=>{
      loader.onError.add(e=>reject(e));
      loader.load((_ldr,res)=>{try{if(!res.nikke||!res.nikke.spineData)throw new Error('No se obtuvo spineData');const md=new PIXI.spine.Spine(res.nikke.spineData);app.stage.addChild(md);resolve(md);}catch(e){reject(e);}});
    });
    let baseScale=1, paused=false, demoTimer=null, demoIndex=0, drag=false,lx=0,ly=0;
    const fit=()=>{const w=Math.max(1,host.clientWidth),h=Math.max(1,host.clientHeight);app.renderer.resize(w,h);let b;try{b=model.getLocalBounds();}catch(_){b=model.getBounds();}const bw=Math.max(1,b.width),bh=Math.max(1,b.height);baseScale=Math.min(w/bw,h/bh)*.82;model.scale.set(baseScale);model.x=w/2-(b.x+b.width/2)*baseScale;model.y=h/2-(b.y+b.height/2)*baseScale;};
    const names=(model.spineData?.animations||[]).map(x=>x.name);
    const sel=document.createElement('select');Object.assign(sel.style,{minWidth:'220px',background:'#172033',color:'#e5e7eb',border:'1px solid #334155',borderRadius:'8px',padding:'7px'});
    names.forEach(n=>{const o=document.createElement('option');o.value=n;o.textContent=n;sel.appendChild(o);});
    const loop=document.createElement('label');loop.style.cssText='display:flex;align-items:center;gap:5px;color:#cbd5e1;font-size:12px';loop.innerHTML='<input type="checkbox" checked> Loop';
    const loopBox=loop.querySelector('input');
    const stopDemo=()=>{if(demoTimer){clearInterval(demoTimer);demoTimer=null;}auto.textContent='Demo Auto';};
    const playName=(n,lp=true)=>{if(!n)return;sel.value=n;model.state.setAnimation(0,n,lp);};
    const choose=(hints)=>{for(const h of hints){const ex=names.find(n=>n.toLowerCase()===h);if(ex)return ex;const part=names.find(n=>n.toLowerCase().includes(h));if(part)return part;}return names[0]||'';};
    const idle=makeButton('Demo Idle',()=>{stopDemo();playName(choose(['idle','normal_idle','standing','wait']),true);},true);
    const action=makeButton('Demo Acción',()=>{stopDemo();playName(choose(['burst','skill','attack','shoot','aim','cover']),true);},true);
    const auto=makeButton('Demo Auto',()=>{if(demoTimer){stopDemo();return;}demoIndex=0;const step=()=>{if(!names.length)return;playName(names[demoIndex++%names.length],false);};step();demoTimer=setInterval(step,4200);auto.textContent='Detener Demo';},true);
    const pause=makeButton('⏸ Pausa',()=>{paused=!paused;model.state.timeScale=paused?0:1;pause.textContent=paused?'▶ Reanudar':'⏸ Pausa';});
    const reset=makeButton('↺ Ajustar',fit); const minus=makeButton('−',()=>model.scale.set(model.scale.x/1.12)); const plus=makeButton('+',()=>model.scale.set(model.scale.x*1.12));
    sel.onchange=()=>{stopDemo();playName(sel.value,loopBox.checked);};loopBox.onchange=()=>playName(sel.value,loopBox.checked);
    shell.foot.append(pause,sel,loop,idle,action,auto,reset,minus,plus);
    const info=document.createElement('span');info.textContent='Spine '+(m.spineVersion||'')+(m.unityVersionRepaired?' · Unity reparado':'');Object.assign(info.style,{marginLeft:'auto',fontSize:'11px',color:'#94a3b8'});shell.foot.appendChild(info);
    const initial=choose(m.action==='aim'?['aim_idle','aim']:m.action==='cover'?['cover_idle','cover']:['idle','normal_idle','standing']); playName(initial,true);
    fit();
    const ro=new ResizeObserver(fit);ro.observe(host);
    app.view.addEventListener('pointerdown',e=>{drag=true;lx=e.clientX;ly=e.clientY;});app.view.addEventListener('pointermove',e=>{if(!drag)return;model.x+=e.clientX-lx;model.y+=e.clientY-ly;lx=e.clientX;ly=e.clientY;});app.view.addEventListener('pointerup',()=>drag=false);app.view.addEventListener('pointerleave',()=>drag=false);app.view.addEventListener('wheel',e=>{e.preventDefault();model.scale.set(model.scale.x*(e.deltaY<0?1.08:.92));},{passive:false});
    sessions.set(shell.panel,{destroy:()=>{stopDemo();try{ro.disconnect();}catch(_){}try{app.destroy(true,{children:true,texture:false,baseTexture:false});}catch(_){}}});
  }

  async function renderPath(shell,path) {
    const old=sessions.get(shell.panel); if(old?.destroy) old.destroy(); sessions.delete(shell.panel);
    shell.path=path; shell.stage.innerHTML='';shell.foot.innerHTML='';
    const msg=document.createElement('div');msg.textContent='Preparando vista previa…';Object.assign(msg.style,{position:'absolute',inset:'0',display:'flex',alignItems:'center',justifyContent:'center',color:'#cbd5e1',fontWeight:'700'});shell.stage.appendChild(msg);
    try {
      const m=await apiPrepare(path); relatedTabs(shell,m,path);
      if(m.type==='spine') await spinePreview(shell,m); else staticPreview(shell,m);
    } catch(e) { showError(shell,e?.message||String(e)); }
  }

  function attachPreview() {
    const nodes=[...document.querySelectorAll('div,section,dialog')].filter(el=>{
      const t=el.innerText||'';
      return t.includes('Preview Alpha') && (t.includes('ARCHIVO DEL BUNDLE')||t.includes('BUNDLE FILE')||/[A-Za-z]:\\/.test(t));
    });
    nodes.sort((a,b)=>(a.innerText||'').length-(b.innerText||'').length);
    const modal=nodes[0]; if(!modal) return;
    const path=findPath(modal.innerText); if(!path) return;
    if(modal.dataset.nmmClassicPath===path && modal.querySelector(':scope > .nmm-v013-classic-panel')) return;
    modal.dataset.nmmClassicPath=path;
    const shell=createShell(modal,path); renderPath(shell,path);
  }

  const heartbeat=()=>fetch(API+'/api/heartbeat',{cache:'no-store',mode:'no-cors'}).catch(()=>{});
  setInterval(heartbeat,1200); heartbeat();

  const observer=new MutationObserver(()=>{renameManager();hideImageAdmin();attachPreview();});
  observer.observe(document.documentElement,{subtree:true,childList:true,characterData:true});
  setInterval(()=>{renameManager();hideImageAdmin();attachPreview();},900);
  renameManager(); hideImageAdmin(); attachPreview();
})();
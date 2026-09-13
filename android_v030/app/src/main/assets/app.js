const $=s=>document.querySelector(s), $$=s=>Array.from(document.querySelectorAll(s));
const BASE='https://raw.githubusercontent.com/ExoticSytem/NIKKE-Mod-Tracker/main/catalog/admin/';
const K={catalog:'nmt_catalog_v3',inventory:'nmt_inventory_v3',tags:'nmt_tags_v3',pair:'nmt_pair_v3'};
const state={catalog:[],inventory:{},tags:{},pair:null,filter:'mods',query:'',selected:null,catalogVersion:'',syncing:false};
const load=(k,d)=>{try{return JSON.parse(localStorage.getItem(k))??d}catch{return d}};
const save=(k,v)=>localStorage.setItem(k,JSON.stringify(v));
const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const keyOf=c=>c.key||`${c.id}_${c.version}`;
const inv=k=>state.inventory[k]||null;
const totalMods=k=>{const x=inv(k);return x?Object.values(x.counts||{}).reduce((a,b)=>a+(+b||0),0):0};
const cardUrl=c=>c.image_file?`${BASE}images/${encodeURIComponent(keyOf(c))}__card.png`:'';
const fullUrl=c=>c.image_file?`${BASE}${c.image_file}`:'';
const isNpc=(c,k)=>{const cl=String(c?.classification||'').toLowerCase();return !!(inv(k)?.is_npc_extra||cl.includes('npc')||cl.includes('extra'))};

function init(){
  const cc=load(K.catalog,null); if(cc?.characters){state.catalog=cc.characters;state.catalogVersion=cc.catalog_version||''}
  state.inventory=load(K.inventory,{}); state.tags=load(K.tags,{}); state.pair=load(K.pair,null);
  if(!Object.keys(state.inventory).length) state.filter='all';
  bind(); render(); updateStatus();
  try{Native.ready();Native.loadCatalog()}catch(e){$('#catalogStatus').textContent='Sin conexión nativa'}
  if(state.pair) setTimeout(syncNow,500);
}
function bind(){
  $('#search').addEventListener('input',e=>{state.query=e.target.value.trim().toLowerCase();render()});
  $('#filters').addEventListener('click',e=>{const b=e.target.closest('button[data-filter]');if(!b)return;state.filter=b.dataset.filter;$$('#filters button').forEach(x=>x.classList.toggle('active',x===b));render()});
  $('#syncBtn').onclick=syncNow; $('#catalogBtn').onclick=()=>{statusCatalog('Actualizando catálogo…');try{Native.loadCatalog()}catch{}};
  $('#pairHelpBtn').onclick=()=>$('#pairModal').classList.remove('hidden');
  $$('[data-pair-close]').forEach(x=>x.onclick=()=>$('#pairModal').classList.add('hidden'));
  $$('[data-close]').forEach(x=>x.onclick=closeDetail);
  $('#clearPairBtn').onclick=()=>{state.pair=null;save(K.pair,null);updateStatus();$('#pairModal').classList.add('hidden');toast('PC desvinculado')};
  $('#clearCacheBtn').onclick=()=>{try{Native.clearImageCache()}catch{}};
  $('#tagAddBtn').onclick=addTag; $('#tagInput').addEventListener('keydown',e=>{if(e.key==='Enter')addTag()});
  $('#detailName').onclick=()=>{if(!state.selected)return;try{Native.copyText(state.selected.name||'')}catch{} };
}
function mergedCatalog(){
  const map=new Map(state.catalog.map(c=>[keyOf(c),c]));
  for(const [k,v] of Object.entries(state.inventory)){if(!map.has(k))map.set(k,{key:k,id:v.id||k.split('_')[0],version:v.version||k.split('_')[1]||'',name:v.name||k,image_file:'',classification:v.is_npc_extra?'npc':'unknown',is_placeholder:true})}
  return [...map.values()];
}
function visible(){
  const q=state.query;
  return mergedCatalog().filter(c=>{
    const k=keyOf(c), i=inv(k), tm=totalMods(k), cf=(i?.conflicts||[]).length, npc=isNpc(c,k);
    if(state.filter==='mods'&&!tm)return false;if(state.filter==='conflicts'&&!cf)return false;if(state.filter==='npc'&&!npc)return false;
    if(q&&!`${c.name} ${c.id} ${c.version} ${k}`.toLowerCase().includes(q))return false;return true;
  }).sort((a,b)=>{const am=totalMods(keyOf(a)),bm=totalMods(keyOf(b));if(bm!==am)return bm-am;return String(a.name).localeCompare(String(b.name),'es')});
}
function render(){
  const list=visible(), grid=$('#grid'), empty=$('#empty');
  if(!list.length){grid.innerHTML='';empty.classList.remove('hidden');empty.textContent=state.filter==='mods'?'Todavía no hay mods sincronizados. Vincula el PC o cambia a “Todos”.':'No hay resultados.';return}
  empty.classList.add('hidden');
  grid.innerHTML=list.map(c=>{const k=keyOf(c),i=inv(k),tm=totalMods(k),cf=(i?.conflicts||[]).length,img=cardUrl(c),letter=esc((c.name||'?').slice(0,1).toUpperCase());return `<article class="card" data-key="${esc(k)}"><div class="placeholder">${letter}</div>${img?`<img loading="lazy" src="${esc(img)}" alt="" onerror="this.onerror=null;this.src='${esc(fullUrl(c))}'">`:''}<div class="card-info"><div class="card-name">${esc(c.name||k)}</div><div class="card-meta">ID ${esc(c.id)} · Ver ${esc(c.version)}</div><div class="badges">${tm?`<span class="badge mod">${tm} mod${tm===1?'':'s'}</span>`:''}${cf?`<span class="badge conflict">${cf} conflicto${cf===1?'':'s'}</span>`:''}</div></div></article>`}).join('');
  grid.querySelectorAll('.card').forEach(el=>el.onclick=()=>openDetail(el.dataset.key));
}
function openDetail(k){const c=mergedCatalog().find(x=>keyOf(x)===k);if(!c)return;state.selected=c;const i=inv(k)||{counts:{},mods:[],conflicts:[]};$('#detailName').textContent=c.name||k;$('#detailMeta').textContent=`ID ${c.id} · Ver ${c.version}${isNpc(c,k)?' · NPC / Extra':''}`;const fu=fullUrl(c);$('#detailImage').innerHTML=fu?`<img src="${esc(fu)}" alt="${esc(c.name)}">`:`<div class="placeholder">${esc((c.name||'?')[0])}</div>`;const counts=i.counts||{};const npc=isNpc(c,k);$('#detailCounts').innerHTML=(npc?['standing']:['aim','cover','standing']).map(a=>`<div class="count">${a[0].toUpperCase()+a.slice(1)} <b>${+counts[a]||0}</b></div>`).join('');renderTags();const mods=i.mods||[];$('#detailMods').innerHTML=mods.length?mods.map(m=>`<div class="modrow"><div class="mn">${esc(m.name||m.file_name||'Mod')}</div><div class="mm">${esc(m.action||'')}${m.author?` · ${esc(m.author)}`:''}${m.conflict?' · CONFLICTO':''}</div></div>`).join(''):`<div class="muted">Sin mods sincronizados para esta variante.</div>`;$('#modal').classList.remove('hidden')}
function closeDetail(){state.selected=null;$('#modal').classList.add('hidden')}
function currentTagList(k){const b=state.tags[k]||{};return Object.values(b).filter(x=>x&&x.present).sort((a,b)=>String(a.tag).localeCompare(String(b.tag),'es'))}
function renderTags(){if(!state.selected)return;const k=keyOf(state.selected);$('#detailTags').innerHTML=currentTagList(k).map(t=>`<span class="tag">${esc(t.tag)}<button data-tag="${esc(t.tag.toLowerCase())}">×</button></span>`).join('');$('#detailTags').querySelectorAll('button').forEach(b=>b.onclick=()=>setTag(b.dataset.tag,false))}
function addTag(){if(!state.selected)return;const inp=$('#tagInput'),tag=inp.value.trim().replace(/\s+/g,' ').slice(0,40);if(!tag)return;setTag(tag,true);inp.value=''}
function setTag(tag,present){const k=keyOf(state.selected),norm=String(tag).toLowerCase();state.tags[k]??={};const old=state.tags[k][norm];state.tags[k][norm]={tag:old?.tag||tag,present,updated_at:Date.now()};save(K.tags,state.tags);renderTags();if(state.pair)setTimeout(syncNow,120)}
function updateStatus(){const d=$('#pcDot'),s=$('#pcStatus');if(state.pair){d.className='dot ok';s.textContent=state.pair.name||'PC vinculado'}else{d.className='dot';s.textContent='PC no vinculado'}const c=state.catalog.length;statusCatalog(c?`${c} personajes/skins · ${state.catalogVersion||'catálogo guardado'}`:'Sin catálogo guardado')}
function statusCatalog(t){$('#catalogStatus').textContent=t}
function syncNow(){if(state.syncing)return;if(!state.pair){$('#pairModal').classList.remove('hidden');return}state.syncing=true;$('#syncBtn').textContent='…';$('#pcStatus').textContent='Sincronizando…';try{Native.sync(state.pair.host,state.pair.token,JSON.stringify(state.tags))}catch(e){onNativeSyncError(String(e))}}
function applySnapshot(s){if(!s||!s.ok)throw new Error(s?.error||'Respuesta inválida');state.inventory=s.inventory||{};state.tags=s.tags||state.tags||{};save(K.inventory,state.inventory);save(K.tags,state.tags);if(state.filter==='all'&&Object.keys(state.inventory).length){state.filter='mods';$$('#filters button').forEach(x=>x.classList.toggle('active',x.dataset.filter==='mods'))}render();if(state.selected)openDetail(keyOf(state.selected));state.syncing=false;$('#syncBtn').textContent='↻';$('#pcDot').className='dot ok';$('#pcStatus').textContent=state.pair?.name||'PC sincronizado'}
window.onNativeCatalog=json=>{try{const x=JSON.parse(json);if(!Array.isArray(x.characters))throw new Error('Formato inválido');state.catalog=x.characters;state.catalogVersion=x.catalog_version||'';save(K.catalog,x);updateStatus();render()}catch(e){onNativeCatalogError(e.message)}};
window.onNativeCatalogError=err=>{statusCatalog(state.catalog.length?`${state.catalog.length} personajes/skins · sin conexión para actualizar`:`No se pudo cargar el catálogo: ${err}`)};
window.onNativeSync=json=>{try{applySnapshot(JSON.parse(json));toast('Sincronización completa')}catch(e){onNativeSyncError(e.message)}};
window.onNativeSyncError=err=>{state.syncing=false;$('#syncBtn').textContent='↻';$('#pcDot').className='dot err';$('#pcStatus').textContent='PC no disponible';toast('No se pudo sincronizar')};
window.receivePairUri=uri=>{try{const u=new URL(uri);const host=u.searchParams.get('host'),token=u.searchParams.get('token'),name=u.searchParams.get('name')||'NIKKE Mod Manager PC';if(!host||!token)throw 0;state.pair={host,token,name};save(K.pair,state.pair);updateStatus();$('#pairModal').classList.add('hidden');toast('PC vinculado');setTimeout(syncNow,150)}catch{toast('QR de vinculación inválido')}};
window.androidBack=()=>{if(!$('#modal').classList.contains('hidden')){closeDetail();return true}if(!$('#pairModal').classList.contains('hidden')){$('#pairModal').classList.add('hidden');return true}return false};
let toastTimer;function toast(t){const el=$('#toast');el.textContent=t;el.classList.remove('hidden');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.add('hidden'),1500)}
window.addEventListener('DOMContentLoaded',init);

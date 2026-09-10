let state = null;
let currentView = 'characters';
let characterFilter = 'all';
let characterSort = 'id_asc';
let characterCategory = 'all';
let characterTagFilter = 'all';
let characterSelectionMode = false;
let selectedCharacters = new Set();
let visibleCharacterKeys = [];
let uiLanguage = 'es';
let selectedMods = new Set();
let pendingDelete = [];
let toastTimer = null;

const $ = (id) => document.getElementById(id);
const esc = (s='') => String(s).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

const I18N = {
  es: {
    brand_sub:'MOD MANAGER', nav_label:'NAVEGACIÓN', nav_characters:'Personajes', nav_mods:'Mods', nav_conflicts:'Conflictos', settings_label:'AJUSTES', nav_settings:'Configuración',
    scanned_folder:'CARPETA ESCANEADA', scan_now:'Escanear ahora', refresh:'Actualizar', ready:'Listo', scanning:'Escaneando...', loading:'Cargando...', selecting:'Seleccionando...', deleting:'Eliminando...', loading_image:'Cargando imagen...', updating_catalog:'Buscando nuevos personajes...',
    page_characters:'Personajes', page_characters_sub:'Cada ID + Ver se trata como una skin/personaje independiente', page_mods:'Mods', page_mods_sub:'Archivos detectados en tu carpeta, sin activar ni desactivar nada', page_conflicts:'Conflictos', page_conflicts_sub:'Destinos duplicados por ID + Ver + acción', page_settings:'Configuración', page_settings_sub:'Carpetas, catálogo, idioma e imágenes',
    search_character:'Buscar personaje, ID o versión...', sort_id_asc:'ID: menor a mayor', sort_id_desc:'ID: mayor a menor', sort_name_asc:'Nombre: A-Z', sort_name_desc:'Nombre: Z-A', sort_mods_desc:'Más mods primero', sort_conflicts_first:'Conflictos primero',
    filter_all:'Todos', filter_with_mods:'Con mods', filter_without_mods:'Sin mods', filter_conflicts:'Conflictos', type_all:'Todos', type_npc_extra:'Solo NPC / Extra', type_non_npc:'Ocultar NPC / Extra', tag_filter_all:'Todas las etiquetas', tag_filter_untagged:'Sin etiquetas', variants:'personajes / variantes', no_results:'No hay resultados', no_results_hint:'Prueba otro filtro o selecciona la carpeta donde guardas tus mods.',
    search_mod:'Buscar mod, personaje o autor...', all_actions:'Todas las acciones', only_conflicts:'Solo conflictos', action_aim:'Aim', action_cover:'Cover', action_standing:'Standing',
    send_selected_trash:'Enviar seleccionados a Papelera', send_n_trash:'Enviar {n} a Papelera', col_mod:'Mod', col_character:'Personaje', col_target:'ID / Ver', col_action:'Acción', col_status:'Estado',
    author_detected:'Autor detectado', not_in_catalog:'No está en catálogo', conflict:'Conflicto', show_in_explorer:'Mostrar en Explorador', preview_mod:'Vista previa experimental', preview_loading:'Montando modelo Spine del mod normal...', preview_title:'Preview Alpha', preview_raw_note:'Classic R3 intenta mostrar el modelo armado usando atlas + skel dentro del mismo Preview Alpha.', preview_failed:'No se pudo generar la vista previa: {error}', preview_source:'Archivo del bundle', preview_texture:'Textura', preview_detected:'Detectado', preview_cached:'Caché', send_to_trash:'Enviar a Papelera', no_mods_filter:'No hay mods para este filtro',
    conflict_intro:'Un conflicto aparece cuando 2 o más mods apuntan al mismo <b>ID + Ver + acción</b>. No significa que dos acciones diferentes del mismo personaje entren en conflicto.', no_conflicts:'No se detectaron conflictos', no_conflicts_hint:'Con la carpeta actual no hay destinos duplicados.',
    settings_mod_folder:'Carpeta de mods', settings_mod_folder_desc:'La app solo la <b>lee</b>. No activa ni desactiva mods; eso queda en tu activador externo.', choose_folder:'Seleccionar carpeta', scan:'Escanear', open_folder:'Abrir carpeta',
    settings_images:'Imágenes de personajes', settings_images_desc:'Se prioriza arte en alta resolución desde Prydwen para personajes jugables y NPC antiguos que luego se volvieron jugables; Nikke-DB queda como respaldo exacto por ID + Ver. Una imagen manual siempre tiene prioridad.', open_images_folder:'Abrir carpeta de imágenes', cache_images:'Descargar imágenes para uso sin conexión', cached_images:'{n} imágenes guardadas localmente', caching_images:'Descargando imágenes...', cache_done:'{n} nuevas · {hq} en alta calidad · {c} ya guardadas · {f} sin imagen encontrada',
    settings_language:'Idioma', settings_language_desc:'Cambia toda la interfaz sin reiniciar la aplicación. Aim, Cover y Standing permanecen en inglés.', interface_language:'Idioma de la interfaz',
    official_catalog:'Catálogo', catalog_metric:'entradas ID + Ver', catalog_desc:'Tu lista sigue siendo la base protegida. Las actualizaciones online solo pueden <b>agregar</b> entradas nuevas; nunca reemplazan nombres existentes.',
    classification_title:'NPC / Extra', classification_desc:'La clasificación NPC / Extra se mantiene centralmente en el catálogo del proyecto. Los jugadores reciben las correcciones al actualizar; no se edita localmente.', npc_count:'{n} entradas marcadas como NPC / Extra', playable_reference:'Referencia jugables: Prydwen {p} / Enikk {e}',
    catalog_updates_title:'Actualizaciones del catálogo', catalog_updates_desc:'La app revisa Nikke-DB para nuevos ID + Ver y refresca Prydwen/Enikk para saber qué personajes son jugables. Tu catálogo base nunca se sobreescribe.', auto_updates:'Comprobar automáticamente una vez al día', check_updates:'Buscar actualizaciones ahora', last_catalog_check:'Última comprobación: {date}', online_added:'{n} entradas agregadas desde la fuente online', update_added:'Se agregaron {n} entradas nuevas al catálogo.', update_none:'El catálogo ya estaba al día.', update_failed:'No se pudo comprobar el catálogo: {error}',
    mobile_sync_title:'Sincronización con Android', mobile_sync_desc:'Escanea este QR con la cámara del teléfono. El móvil recibirá los nombres de tus mods y las etiquetas se sincronizarán en ambos sentidos por tu red Wi-Fi.', mobile_sync_wifi:'El PC y el teléfono deben estar en la misma Wi-Fi al sincronizar. No se usan cuentas ni servidores externos.', mobile_sync_new_code:'Generar nuevo código', mobile_sync_ready:'Listo para vincular', mobile_sync_off:'Sincronización local no disponible', mobile_sync_last:'Última sincronización: {date}', mobile_sync_received:'Cambios del teléfono sincronizados.',
    safe_delete:'Eliminación segura', safe_delete_desc:'“Eliminar” manda el archivo o carpeta a la <b>Papelera de reciclaje</b>. La app no hace borrado permanente.',
    send_trash_title:'Enviar a la Papelera', delete_one_confirm:'Este elemento se enviará a la Papelera de reciclaje.', delete_many_confirm:'Los elementos seleccionados se enviarán a la Papelera de reciclaje.', cancel:'Cancelar', send_trash:'Enviar a Papelera',
    no_folder:'Sin configurar', mods_badge_one:'1 mod', mods_badge_many:'{n} mods', conflict_badge:'⚠ conflicto', no_mod_action:'Sin mods para esta acción.', assign_image:'Usar imagen manual', remove_image:'Quitar imagen local',
    files_detected_zero:'No hay mods detectados para esta variante.', files_detected_one:'1 archivo detectado para esta variante.', files_detected_many:'{n} archivos detectados para esta variante.', key_label:'CLAVE',
    npc_badge:'NPC / Extra', classification_label:'Clasificación', classification_auto:'Automático', classification_normal:'No es NPC / Extra', classification_npc:'NPC / Extra', classification_auto_result:'Detección automática: {result}', classification_manual_note:'Clasificación corregida manualmente', normal_result:'No NPC / Extra', npc_result:'NPC / Extra',
    catalog_source_official:'Catálogo base', catalog_source_online:'Agregado online',
    select_multiple:'Seleccionar varios', exit_selection:'Salir de selección', selected_characters:'seleccionados', tag_placeholder:'Escribe una etiqueta...', add_tag:'Agregar etiqueta', remove_tag:'Quitar etiqueta', select_visible:'Seleccionar visibles', clear_selection:'Limpiar selección', tag_added:'Etiqueta aplicada a {n} personaje(s).', tag_removed:'Etiqueta quitada de {n} personaje(s).', tag_required:'Escribe una etiqueta primero.', tags_label:'Etiquetas', no_tags:'Sin etiquetas', folder_configured:'Carpeta configurada.', scan_done:'Escaneo listo: {n} mods detectados.', delete_done_one:'1 elemento enviado a la Papelera.', delete_done_many:'{n} elementos enviados a la Papelera.', delete_errors:'Se eliminaron {n}; {e} error(es).', api_unavailable:'API no disponible todavía'
  },
  en: {
    brand_sub:'MOD LIBRARY', nav_label:'NAVIGATION', nav_characters:'Characters', nav_mods:'Mods', nav_conflicts:'Conflicts', settings_label:'SETTINGS', nav_settings:'Settings',
    scanned_folder:'SCANNED FOLDER', scan_now:'Scan now', refresh:'Refresh', ready:'Ready', scanning:'Scanning...', loading:'Loading...', selecting:'Selecting...', deleting:'Deleting...', loading_image:'Loading image...', updating_catalog:'Checking for new characters...',
    page_characters:'Characters', page_characters_sub:'Each ID + Ver is treated as an independent skin/character', page_mods:'Mods', page_mods_sub:'Files detected in your folder; nothing is enabled or disabled', page_conflicts:'Conflicts', page_conflicts_sub:'Duplicate targets by ID + Ver + action', page_settings:'Settings', page_settings_sub:'Folders, catalog, language and images',
    search_character:'Search character, ID or version...', sort_id_asc:'ID: low to high', sort_id_desc:'ID: high to low', sort_name_asc:'Name: A-Z', sort_name_desc:'Name: Z-A', sort_mods_desc:'Most mods first', sort_conflicts_first:'Conflicts first',
    filter_all:'All', filter_with_mods:'With mods', filter_without_mods:'Without mods', filter_conflicts:'Conflicts', type_all:'All', type_npc_extra:'NPC / Extra only', type_non_npc:'Hide NPC / Extra', tag_filter_all:'All tags', tag_filter_untagged:'Untagged', variants:'characters / variants', no_results:'No results', no_results_hint:'Try another filter or select the folder where you keep your mods.',
    search_mod:'Search mod, character or author...', all_actions:'All actions', only_conflicts:'Conflicts only', action_aim:'Aim', action_cover:'Cover', action_standing:'Standing',
    send_selected_trash:'Send selected to Recycle Bin', send_n_trash:'Send {n} to Recycle Bin', col_mod:'Mod', col_character:'Character', col_target:'ID / Ver', col_action:'Action', col_status:'Status',
    author_detected:'Detected author', not_in_catalog:'Not in catalog', conflict:'Conflict', show_in_explorer:'Show in Explorer', preview_mod:'Experimental preview', preview_loading:'Mounting normal mod Spine model...', preview_title:'Preview Alpha', preview_raw_note:'Classic R3 tries to render the assembled model from atlas + skel inside the same Preview Alpha.', preview_failed:'Could not generate preview: {error}', preview_source:'Bundle file', preview_texture:'Texture', preview_detected:'Detected', preview_cached:'Cache', send_to_trash:'Send to Recycle Bin', no_mods_filter:'No mods match this filter',
    conflict_intro:'A conflict appears when 2 or more mods target the same <b>ID + Ver + action</b>. Different actions for the same character do not conflict with each other.', no_conflicts:'No conflicts detected', no_conflicts_hint:'There are no duplicated targets in the current folder.',
    settings_mod_folder:'Mods folder', settings_mod_folder_desc:'The app only <b>reads</b> it. It does not enable or disable mods; your external activator remains in charge.', choose_folder:'Select folder', scan:'Scan', open_folder:'Open folder',
    settings_images:'Character images', settings_images_desc:'High-resolution Prydwen art is preferred for playable characters and old NPC records that later became playable; Nikke-DB remains the exact ID + Ver fallback. Manual images always take priority.', open_images_folder:'Open images folder', cache_images:'Download images for offline use', cached_images:'{n} images stored locally', caching_images:'Downloading images...', cache_done:'{n} new · {hq} high quality · {c} already stored · {f} with no image found',
    settings_language:'Language', settings_language_desc:'Change the interface without restarting. Aim, Cover and Standing always stay in English.', interface_language:'Interface language',
    official_catalog:'Catalog', catalog_metric:'ID + Ver entries', catalog_desc:'Your list remains the protected baseline. Online updates can only <b>add</b> new entries; existing names are never overwritten.',
    classification_title:'NPC / Extra', classification_desc:'NPC / Extra classification is maintained centrally in the project catalog. Players receive corrections on refresh; it is not edited locally.', npc_count:'{n} entries marked NPC / Extra', playable_reference:'Playable reference: Prydwen {p} / Enikk {e}',
    catalog_updates_title:'Catalog updates', catalog_updates_desc:'The app checks Nikke-DB for new ID + Ver entries and refreshes Prydwen/Enikk to identify playable characters. Your baseline catalog is never overwritten.', auto_updates:'Check automatically once per day', check_updates:'Check for updates now', last_catalog_check:'Last check: {date}', online_added:'{n} entries added from the online source', update_added:'Added {n} new catalog entries.', update_none:'The catalog is already up to date.', update_failed:'Could not check the catalog: {error}',
    mobile_sync_title:'Android sync', mobile_sync_desc:'Scan this QR with your phone camera. Android receives your mod names and tags sync both ways over your Wi-Fi network.', mobile_sync_wifi:'PC and phone must be on the same Wi-Fi while syncing. No accounts or external servers are used.', mobile_sync_new_code:'Generate new code', mobile_sync_ready:'Ready to pair', mobile_sync_off:'Local sync unavailable', mobile_sync_last:'Last sync: {date}', mobile_sync_received:'Phone changes synced.',
    safe_delete:'Safe deletion', safe_delete_desc:'“Delete” sends the file or folder to the <b>Recycle Bin</b>. The app never permanently deletes it.',
    send_trash_title:'Send to Recycle Bin', delete_one_confirm:'This item will be sent to the Recycle Bin.', delete_many_confirm:'The selected items will be sent to the Recycle Bin.', cancel:'Cancel', send_trash:'Send to Recycle Bin',
    no_folder:'Not configured', mods_badge_one:'1 mod', mods_badge_many:'{n} mods', conflict_badge:'⚠ conflict', no_mod_action:'No mods for this action.', assign_image:'Use manual image', remove_image:'Remove local image',
    files_detected_zero:'No mods detected for this variant.', files_detected_one:'1 file detected for this variant.', files_detected_many:'{n} files detected for this variant.', key_label:'KEY',
    npc_badge:'NPC / Extra', classification_label:'Classification', classification_auto:'Automatic', classification_normal:'Not NPC / Extra', classification_npc:'NPC / Extra', classification_auto_result:'Automatic detection: {result}', classification_manual_note:'Classification manually corrected', normal_result:'Not NPC / Extra', npc_result:'NPC / Extra',
    catalog_source_official:'Baseline catalog', catalog_source_online:'Added online',
    select_multiple:'Select multiple', exit_selection:'Exit selection', selected_characters:'selected', tag_placeholder:'Type a tag...', add_tag:'Add tag', remove_tag:'Remove tag', select_visible:'Select visible', clear_selection:'Clear selection', tag_added:'Tag applied to {n} character(s).', tag_removed:'Tag removed from {n} character(s).', tag_required:'Type a tag first.', tags_label:'Tags', no_tags:'No tags',
    folder_configured:'Folder configured.', scan_done:'Scan complete: {n} mods detected.', delete_done_one:'1 item sent to the Recycle Bin.', delete_done_many:'{n} items sent to the Recycle Bin.', delete_errors:'{n} deleted; {e} error(s).', api_unavailable:'API is not available yet'
  }
};

function t(key, vars={}) {
  const dict=I18N[uiLanguage]||I18N.es;
  let text=dict[key]??I18N.es[key]??key;
  Object.entries(vars).forEach(([k,v])=>{ text=text.replaceAll(`{${k}}`,String(v)); });
  return text;
}
function actionLabel(action){ return t(`action_${action}`); }
function modCountText(n){ return n===1?t('mods_badge_one'):t('mods_badge_many',{n}); }
function npcResultText(c){ return c.is_npc_extra?t('npc_result'):t('normal_result'); }

function toast(msg,error=false){
  const el=$('toast'); if(toastTimer) clearTimeout(toastTimer); el.textContent=msg;
  el.className='toast'+(error?' error':''); toastTimer=setTimeout(()=>el.classList.add('hidden'),3800);
}
function setBusy(busy,text=null){
  const label=busy?(text||t('scanning')):t('ready'); $('syncStatus').textContent='● '+label; $('syncStatus').style.color=busy?'#ffb74d':'#23c982';
}
async function apiCall(name,...args){
  try{ if(!window.pywebview?.api?.[name]) throw new Error(t('api_unavailable')); return await window.pywebview.api[name](...args); }
  catch(e){ toast(e.message||String(e),true); throw e; }
}

function applyStaticI18n(){
  document.documentElement.lang=uiLanguage;
  document.querySelectorAll('[data-i18n]').forEach(el=>{ el.textContent=t(el.dataset.i18n); });
  document.querySelectorAll('[data-i18n-html]').forEach(el=>{ el.innerHTML=t(el.dataset.i18nHtml); });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el=>{ el.placeholder=t(el.dataset.i18nPlaceholder); });
  $('conflictIntro').innerHTML=t('conflict_intro'); switchView(currentView,false);
}

function setState(next){
  const firstLoad=state===null; state=next; selectedMods.clear(); selectedCharacters=new Set([...selectedCharacters].filter(k=>state.characters?.some(c=>c.key===k)));
  uiLanguage=state.settings?.language||'es'; characterSort=state.settings?.character_sort||'id_asc';
  if(firstLoad) characterFilter=state.settings?.default_character_filter||'all';
  applyStaticI18n();
  if($('languageSelect')) $('languageSelect').value=uiLanguage;
  if($('characterSort')) $('characterSort').value=characterSort;
  document.querySelectorAll('#characterFilterChips .chip').forEach(x=>x.classList.toggle('active',x.dataset.filter===characterFilter));
  renderAll();
}
function renderAll(){ if(!state) return; refreshTagFilter(); renderStats(); renderCharacters(); renderMods(); renderConflicts(); renderSettings(); }

function renderStats(){
  $('sidebarConflictCount').textContent=state.stats.conflicts;
  $('sidebarFolder').textContent=state.settings.mods_folder||t('no_folder');
  $('catalogMetric').textContent=state.stats.catalog;
  if($('cachedImagesText')) $('cachedImagesText').textContent=t('cached_images',{n:state.stats.cached_images||0});
}

function imageMarkup(c){
  const initial=(c.name||'?').trim()[0]?.toUpperCase()||'?';
  const fallback=`<div class="placeholder-letter">${esc(initial)}</div>`;
  if(!c.image_url) return fallback;
  const fallbacks=Array.isArray(c.image_fallback_urls)?c.image_fallback_urls:[];
  const data=fallbacks.length?` data-fallbacks="${esc(JSON.stringify(fallbacks))}"`:'';
  const onerror=`try{const a=JSON.parse(this.dataset.fallbacks||'[]');if(a.length){this.src=a.shift();this.dataset.fallbacks=JSON.stringify(a);this.classList.remove('fit-contain');this.classList.add('fit-cover');}else{this.remove();}}catch(e){this.remove();}`;
  const fit=c.image_fit==='contain'?'fit-contain':'fit-cover';
  return `${fallback}<img class="${fit}" loading="lazy" src="${esc(c.image_url)}"${data} alt="${esc(c.name)}" onerror="${onerror}"/>`;
}

function parseNumberish(v){ const s=String(v??''); return /^\d+$/.test(s)?Number(s):Number.POSITIVE_INFINITY; }
function compareIdAsc(a,b){
  const ai=parseNumberish(a.id),bi=parseNumberish(b.id); if(ai!==bi) return ai-bi;
  if(ai===Number.POSITIVE_INFINITY){ const idCmp=String(a.id).localeCompare(String(b.id),undefined,{numeric:true,sensitivity:'base'}); if(idCmp) return idCmp; }
  const av=parseNumberish(a.version),bv=parseNumberish(b.version); if(av!==bv) return av-bv;
  const verCmp=String(a.version).localeCompare(String(b.version),undefined,{numeric:true,sensitivity:'base'}); if(verCmp) return verCmp;
  return String(a.name).localeCompare(String(b.name),undefined,{sensitivity:'base'});
}
function compareCharacters(a,b){
  switch(characterSort){
    case'id_desc':return-compareIdAsc(a,b); case'name_asc':return a.name.localeCompare(b.name,undefined,{sensitivity:'base',numeric:true})||compareIdAsc(a,b);
    case'name_desc':return b.name.localeCompare(a.name,undefined,{sensitivity:'base',numeric:true})||compareIdAsc(a,b); case'mods_desc':return(b.mod_count-a.mod_count)||compareIdAsc(a,b);
    case'conflicts_first':return(Number(b.has_conflict)-Number(a.has_conflict))||(b.mod_count-a.mod_count)||compareIdAsc(a,b); default:return compareIdAsc(a,b);
  }
}

function tagPills(c,limit=3){
  const tags=Array.isArray(c.tags)?c.tags:[];
  if(!tags.length)return '';
  const shown=tags.slice(0,limit).map(x=>`<span class="tag-pill">${esc(x)}</span>`).join('');
  return `<div class="tag-row">${shown}${tags.length>limit?`<span class="tag-pill more">+${tags.length-limit}</span>`:''}</div>`;
}
function refreshTagFilter(){
  const sel=$('characterTagFilter'); if(!sel||!state)return;
  const previous=characterTagFilter;
  sel.innerHTML=`<option value="all">${esc(t('tag_filter_all'))}</option><option value="untagged">${esc(t('tag_filter_untagged'))}</option>`+(state.available_tags||[]).map(tag=>`<option value="tag:${esc(tag)}"># ${esc(tag)}</option>`).join('');
  const exists=[...sel.options].some(o=>o.value===previous); characterTagFilter=exists?previous:'all'; sel.value=characterTagFilter;
  const dl=$('tagSuggestions'); if(dl)dl.innerHTML=(state.available_tags||[]).map(tag=>`<option value="${esc(tag)}"></option>`).join('');
}
function updateBulkTagBar(){
  const bar=$('bulkTagBar'); if(!bar)return;
  bar.classList.toggle('hidden',!characterSelectionMode);
  $('bulkSelectedCount').textContent=selectedCharacters.size;
  $('toggleCharacterSelectBtn').innerHTML=characterSelectionMode?`☒ <span>${esc(t('exit_selection'))}</span>`:`☑ <span>${esc(t('select_multiple'))}</span>`;
  $('addTagSelectedBtn').disabled=selectedCharacters.size===0; $('removeTagSelectedBtn').disabled=selectedCharacters.size===0;
}

function renderCharacters(){
  const q=$('characterSearch').value.trim().toLowerCase(); let chars=state.characters.filter(c=>!c.is_placeholder);
  if(characterFilter==='with_mods') chars=chars.filter(c=>c.mod_count>0);
  if(characterFilter==='without_mods') chars=chars.filter(c=>c.mod_count===0);
  if(characterFilter==='conflicts') chars=chars.filter(c=>c.has_conflict);
  if(characterCategory==='npc_extra') chars=chars.filter(c=>c.is_npc_extra);
  if(characterCategory==='non_npc') chars=chars.filter(c=>!c.is_npc_extra);
  if(characterTagFilter==='untagged') chars=chars.filter(c=>!(c.tags||[]).length);
  if(characterTagFilter.startsWith('tag:')){const wanted=characterTagFilter.slice(4).toLowerCase();chars=chars.filter(c=>(c.tags||[]).some(x=>x.toLowerCase()===wanted));}
  if(q) chars=chars.filter(c=>`${c.name} ${c.id} ${c.version} ${c.key} ${(c.tags||[]).join(' ')}`.toLowerCase().includes(q));
  chars.sort(compareCharacters); visibleCharacterKeys=chars.map(c=>c.key); $('variantCount').textContent=chars.length;
  $('characterGrid').innerHTML=chars.map(c=>{
    const action=(name)=>{ const n=c.counts[name]||0,bad=c.action_conflicts[name]; return `<div class="action-cell"><div class="action-name">${esc(actionLabel(name))}</div><div class="action-count ${bad?'bad':n?'good':'zero'}">${bad?'⚠ '+n:n||'—'}</div></div>`; };
    const npcBadge=c.is_npc_extra?`<div class="category-badge category-npc_extra">${esc(t('npc_badge'))}</div>`:'';
    const actions=c.is_npc_extra?`<div class="action-row npc-action-row">${action('standing')}</div>`:`<div class="action-row">${action('aim')}${action('cover')}${action('standing')}</div>`;
    const selectBox=characterSelectionMode?`<label class="character-select-box" title="${esc(t('select_multiple'))}"><input class="character-check" type="checkbox" data-key="${esc(c.key)}" ${selectedCharacters.has(c.key)?'checked':''}/><span></span></label>`:'';
    const selectedClass=selectedCharacters.has(c.key)?' selected-card':'';
    return `<article class="character-card${selectedClass}" data-character="${esc(c.key)}"><div class="char-image">${imageMarkup(c)}${selectBox}${npcBadge}${c.mod_count?`<div class="mods-badge">${esc(modCountText(c.mod_count))}</div>`:''}${c.has_conflict?`<div class="conflict-badge">${esc(t('conflict_badge'))}</div>`:''}</div><div class="char-body"><div class="char-title" title="${esc(c.name)}">${esc(c.name)}</div><div class="char-id">ID: ${esc(c.id)} · Ver: ${esc(c.version)}</div>${tagPills(c)}${actions}</div></article>`;
  }).join('');
  $('characterEmpty').classList.toggle('hidden',chars.length!==0);
  document.querySelectorAll('.character-check').forEach(ch=>ch.addEventListener('click',e=>e.stopPropagation()));
  document.querySelectorAll('.character-check').forEach(ch=>ch.addEventListener('change',()=>{ch.checked?selectedCharacters.add(ch.dataset.key):selectedCharacters.delete(ch.dataset.key);renderCharacters();updateBulkTagBar();}));
  document.querySelectorAll('[data-character]').forEach(el=>el.addEventListener('click',()=>{const key=el.dataset.character;if(characterSelectionMode){selectedCharacters.has(key)?selectedCharacters.delete(key):selectedCharacters.add(key);renderCharacters();updateBulkTagBar();}else openCharacter(key);}));
  updateBulkTagBar();
}

function filteredMods(){
  const q=$('modSearch').value.trim().toLowerCase(),f=$('actionFilter').value;
  return state.items.filter(m=>{ if(f==='conflict'&&!m.conflict)return false; if(f!=='all'&&f!=='conflict'&&m.action!==f)return false; if(q&&!`${m.name} ${m.mod_title} ${m.character_name} ${m.author_guess} ${m.id} ${m.version}`.toLowerCase().includes(q))return false; return true; });
}
function renderMods(){
  const mods=filteredMods();
  $('modsTableBody').innerHTML=mods.length?mods.map(m=>`<tr><td><input class="mod-check" type="checkbox" data-mod-id="${m.item_id}" ${selectedMods.has(m.item_id)?'checked':''}/></td><td><div class="mod-name">${esc(m.mod_title||m.name)}</div><div class="subline">${m.author_guess?`${esc(t('author_detected'))}: ${esc(m.author_guess)} · `:''}${esc(m.name)}</div></td><td><div class="mod-name">${esc(m.character_name)}</div><div class="subline">ID ${esc(m.id)} · Ver ${esc(m.version)}${m.catalog_match?'':` · ${esc(t('not_in_catalog'))}`}</div></td><td class="target-code">${esc(m.id)}/${esc(m.version)}</td><td><span class="action-tag action-${m.action}">${esc(actionLabel(m.action))}</span></td><td>${m.conflict?`<span class="status-bad">⚠ ${esc(t('conflict'))}</span>`:'<span class="status-ok">✓ OK</span>'}</td><td><button class="icon-btn preview-one" data-id="${m.item_id}" title="${esc(t('preview_mod'))}">👁</button> <button class="icon-btn open-item" data-id="${m.item_id}" title="${esc(t('show_in_explorer'))}">📁</button> <button class="icon-btn delete-one" data-id="${m.item_id}" title="${esc(t('send_to_trash'))}">🗑</button></td></tr>`).join(''):`<tr><td colspan="7"><div class="empty-state"><h3>${esc(t('no_mods_filter'))}</h3></div></td></tr>`;
  document.querySelectorAll('.mod-check').forEach(ch=>ch.addEventListener('change',()=>{ch.checked?selectedMods.add(ch.dataset.modId):selectedMods.delete(ch.dataset.modId);updateDeleteButton();}));
  document.querySelectorAll('.preview-one').forEach(b=>b.addEventListener('click',()=>openPreview(b.dataset.id))); document.querySelectorAll('.open-item').forEach(b=>b.addEventListener('click',()=>apiCall('open_item',b.dataset.id))); document.querySelectorAll('.delete-one').forEach(b=>b.addEventListener('click',()=>requestDelete([b.dataset.id]))); updateDeleteButton();
}
function updateDeleteButton(){ const b=$('deleteSelected'); b.disabled=selectedMods.size===0; b.textContent=selectedMods.size?`🗑 ${t('send_n_trash',{n:selectedMods.size})}`:`🗑 ${t('send_selected_trash')}`; }

function renderConflicts(){
  const cs=state.conflicts;
  $('conflictGrid').innerHTML=cs.map(c=>`<div class="conflict-card"><div class="conflict-head"><div><div class="conflict-title">${esc(c.character_name)}</div><div class="conflict-meta">ID ${esc(c.id)} · Ver ${esc(c.version)} · ${esc(actionLabel(c.action))}</div></div><div class="conflict-count">⚠ ${esc(modCountText(c.count))}</div></div>${c.items.map(m=>`<div class="conflict-item"><div class="grow"><div class="conflict-item-title">${esc(m.mod_title||m.name)}</div><div class="conflict-item-path">${esc(m.path)}</div></div><button class="icon-btn conflict-preview" data-id="${m.item_id}" title="${esc(t('preview_mod'))}">👁</button><button class="icon-btn conflict-open" data-id="${m.item_id}">📁</button><button class="icon-btn conflict-delete" data-id="${m.item_id}">🗑</button></div>`).join('')}</div>`).join('');
  $('conflictEmpty').classList.toggle('hidden',cs.length!==0); document.querySelectorAll('.conflict-preview').forEach(b=>b.addEventListener('click',()=>openPreview(b.dataset.id))); document.querySelectorAll('.conflict-open').forEach(b=>b.addEventListener('click',()=>apiCall('open_item',b.dataset.id))); document.querySelectorAll('.conflict-delete').forEach(b=>b.addEventListener('click',()=>requestDelete([b.dataset.id])));
}

function niceDate(value){ if(!value)return'—'; try{return new Date(value).toLocaleString(uiLanguage==='es'?'es-CL':'en-US');}catch(_e){return value;} }
function renderSettings(){
  refreshTagFilter();
  $('settingsFolder').textContent=state.settings.mods_folder||t('no_folder'); $('languageSelect').value=uiLanguage; $('characterSort').value=characterSort; $('characterCategory').value=characterCategory;
  $('cachedImagesText').textContent=t('cached_images',{n:state.stats.cached_images||0});
  $('npcMetric').textContent=state.stats.npc_extra||0; $('npcMetricText').textContent=t('npc_count',{n:state.stats.npc_extra||0});
  const pr=state.playable_reference||{}; $('playableReferenceText').textContent=t('playable_reference',{p:pr.prydwen_site_count??'—',e:pr.unique_playable_names??'—'});
  $('baseCatalogText').textContent=`${state.base_catalog_count||0} + ${state.online_catalog_count||0}`;
  $('autoCatalogUpdates').checked=!!state.settings.auto_catalog_updates;
  $('catalogUpdateLast').textContent=t('last_catalog_check',{date:niceDate(state.catalog_updates?.last_checked)});
  $('catalogOnlineCount').textContent=t('online_added',{n:state.catalog_updates?.online_total||0});
  const ms=state.mobile_sync||{};
  if($('mobileSyncStatus')) $('mobileSyncStatus').textContent=ms.enabled?t('mobile_sync_ready'):t('mobile_sync_off');
  if($('mobileSyncHost')) $('mobileSyncHost').textContent=ms.host||'—';
  if($('mobileSyncLast')) $('mobileSyncLast').textContent=t('mobile_sync_last',{date:ms.last_sync||'—'});
  if($('mobilePairQr')){if(ms.qr_url){$('mobilePairQr').src=ms.qr_url;$('mobilePairQr').style.display='block';}else $('mobilePairQr').style.display='none';}
}

function openCharacter(key){
  const c=state.characters.find(x=>x.key===key); if(!c)return; const mods=state.items.filter(x=>x.character_key===key);
  const visibleActions=c.is_npc_extra?['standing']:['aim','cover','standing'];
  const sections=visibleActions.map(action=>{ const items=mods.filter(x=>x.action===action),conflict=c.action_conflicts[action]; const countText=conflict?`⚠ ${modCountText(items.length)}`:items.length?modCountText(items.length):'—'; return `<div class="detail-section"><div class="detail-section-head"><span>${esc(actionLabel(action))}</span><span class="${conflict?'status-bad':items.length?'status-ok':''}">${esc(countText)}</span></div>${items.length?items.map(m=>`<div class="detail-mod"><div class="grow"><div class="detail-name">${esc(m.mod_title||m.name)}</div><div class="detail-path">${esc(m.path)}</div></div><button class="icon-btn detail-preview" data-id="${m.item_id}" title="${esc(t('preview_mod'))}">👁</button><button class="icon-btn detail-open" data-id="${m.item_id}">📁</button><button class="icon-btn detail-delete" data-id="${m.item_id}">🗑</button></div>`).join(''):`<div class="detail-mod"><span class="subline">${esc(t('no_mod_action'))}</span></div>`}</div>`; }).join('');
  const filesText=c.mod_count===0?t('files_detected_zero'):c.mod_count===1?t('files_detected_one'):t('files_detected_many',{n:c.mod_count});
  const badge=c.is_npc_extra?`<div class="detail-category category-npc_extra">${esc(t('npc_badge'))}</div>`:'';
  const sourceText=c.catalog_source==='nikke_db_online'?t('catalog_source_online'):t('catalog_source_official');
  const tags=(c.tags||[]).map(x=>`<span class="tag-pill removable-tag" data-tag="${esc(x)}">${esc(x)} <b>×</b></span>`).join('')||`<span class="subline">${esc(t('no_tags'))}</span>`;
  $('modalContent').innerHTML=`<div class="detail-head"><div class="detail-image">${imageMarkup(c)}</div><div class="detail-info">${badge}<h2>${esc(c.name)}</h2><div class="detail-code">ID ${esc(c.id)} · VER ${esc(c.version)} · ${esc(t('key_label'))} ${esc(c.key)}</div><div class="detail-code source-code">${esc(sourceText)}</div><p class="subtitle" style="margin-top:14px">${esc(filesText)}</p><div class="detail-tag-editor"><div class="detail-tag-title">${esc(t('tags_label'))}</div><div class="tag-row detail-tags">${tags}</div><div class="detail-tag-add"><input id="singleTagInput" list="tagSuggestions" maxlength="40" placeholder="${esc(t('tag_placeholder'))}"/><button id="singleAddTagBtn" class="secondary-btn">＋ ${esc(t('add_tag'))}</button></div></div></div></div><div class="detail-actions">${sections}</div>`;
  $('characterModal').classList.remove('hidden');
  $('singleAddTagBtn').onclick=async()=>{const tag=$('singleTagInput').value.trim();if(!tag){toast(t('tag_required'),true);return;}const s=await apiCall('update_character_tags',[key],tag,'add');setState(s);openCharacter(key);};
  document.querySelectorAll('.removable-tag').forEach(x=>x.addEventListener('click',async()=>{const s=await apiCall('update_character_tags',[key],x.dataset.tag,'remove');setState(s);openCharacter(key);}));
  document.querySelectorAll('.detail-preview').forEach(b=>b.addEventListener('click',()=>openPreview(b.dataset.id))); document.querySelectorAll('.detail-open').forEach(b=>b.addEventListener('click',()=>apiCall('open_item',b.dataset.id))); document.querySelectorAll('.detail-delete').forEach(b=>b.addEventListener('click',()=>requestDelete([b.dataset.id],true)));
}
function closeCharacter(){$('characterModal').classList.add('hidden');}
function closePreview(){$('previewModal').classList.add('hidden');}
async function openPreview(itemId){
  const m=state?.items?.find(x=>x.item_id===itemId);
  $('previewContent').innerHTML=`<div class="preview-loading"><div class="preview-spinner">↻</div><h2>${esc(t('preview_title'))}</h2><p>${esc(t('preview_loading'))}</p>${m?`<div class="preview-mod-label">${esc(m.mod_title||m.name)}</div>`:''}</div>`;
  $('previewModal').classList.remove('hidden');
  try{
    const r=await apiCall('preview_item',itemId);
    if(!r?.ok){
      $('previewContent').innerHTML=`<div class="preview-error"><div class="preview-error-icon">⚠</div><h2>${esc(t('preview_title'))}</h2><p>${esc(t('preview_failed',{error:r?.error||'—'}))}</p><div class="detail-path">${esc(r?.path||m?.path||'')}</div></div>`;
      return;
    }
    const detected=[r.character_id_detected?`ID ${r.character_id_detected}`:'',r.skin_key_detected!==null&&r.skin_key_detected!==undefined?`Skin ${r.skin_key_detected}`:'',r.pose_detected?String(r.pose_detected):''].filter(Boolean).join(' · ')||'—';
    const nkab=r.nkab_version?`NKAB v${r.nkab_version}`:'Unity bundle';
    $('previewContent').innerHTML=`<div class="preview-head"><div><div class="preview-kicker">${esc(t('preview_title'))}</div><h2>${esc(r.mod_name||m?.mod_title||m?.name||'Mod')}</h2><div class="preview-sub">${esc(r.character_name||m?.character_name||'')} · ID ${esc(r.id||m?.id||'')} · Ver ${esc(r.version||m?.version||'')} · ${esc(actionLabel(r.action||m?.action||''))}</div></div><span class="preview-alpha-badge">ALPHA</span></div><div class="preview-stage"><img src="${esc(r.preview_url)}?v=${Date.now()}" alt="Preview"/></div><div class="preview-note">⚠ ${esc(t('preview_raw_note'))}</div><div class="preview-meta-grid"><div><b>${esc(t('preview_texture'))}</b><span>${esc(r.texture_name||'Texture2D')} · ${esc(r.texture_width||'?')}×${esc(r.texture_height||'?')}</span></div><div><b>${esc(t('preview_detected'))}</b><span>${esc(detected)}</span></div><div><b>Bundle</b><span>${esc(nkab)}</span></div><div><b>${esc(t('preview_source'))}</b><span title="${esc(r.source_file||'')}">${esc(r.source_file||'—')}</span></div></div>`;
  }catch(e){
    $('previewContent').innerHTML=`<div class="preview-error"><div class="preview-error-icon">⚠</div><h2>${esc(t('preview_title'))}</h2><p>${esc(t('preview_failed',{error:e.message||String(e)}))}</p></div>`;
  }
}

function requestDelete(ids,closeDetail=false){pendingDelete=ids;$('confirmText').textContent=ids.length===1?t('delete_one_confirm'):t('delete_many_confirm');$('confirmModal').classList.remove('hidden');if(closeDetail)$('confirmModal').dataset.closeDetail='1';else delete $('confirmModal').dataset.closeDetail;}
async function doDelete(){ $('confirmModal').classList.add('hidden');setBusy(true,t('deleting'));const s=await apiCall('delete_items',pendingDelete),n=s.delete_result?.deleted?.length||0,errors=s.delete_result?.errors||[];setState(s);setBusy(false);if($('confirmModal').dataset.closeDetail==='1')closeCharacter();toast(errors.length?t('delete_errors',{n,e:errors.length}):(n===1?t('delete_done_one'):t('delete_done_many',{n})),!!errors.length);pendingDelete=[]; }

function switchView(view,updateVisibility=true){ currentView=view;if(updateVisibility){document.querySelectorAll('.view').forEach(v=>v.classList.remove('active-view'));$(`view-${view}`).classList.add('active-view');document.querySelectorAll('.nav-btn[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===view));}const meta={characters:[t('page_characters'),t('page_characters_sub')],mods:[t('page_mods'),t('page_mods_sub')],conflicts:[t('page_conflicts'),t('page_conflicts_sub')],settings:[t('page_settings'),t('page_settings_sub')]}[view];$('pageTitle').textContent=meta[0];$('pageSubtitle').textContent=meta[1]; }
async function refresh(){setBusy(true,t('scanning'));const s=await apiCall('refresh');setState(s);setBusy(false);toast(t('scan_done',{n:s.stats.mods}));}

function bind(){
  document.querySelectorAll('.nav-btn[data-view]').forEach(b=>b.addEventListener('click',()=>switchView(b.dataset.view))); $('refreshBtn').onclick=refresh;$('sidebarScan').onclick=refresh;$('scanSettingsBtn').onclick=refresh;
  $('characterSearch').addEventListener('input',renderCharacters);$('modSearch').addEventListener('input',renderMods);$('actionFilter').addEventListener('change',renderMods);$('characterCategory').addEventListener('change',e=>{characterCategory=e.target.value;renderCharacters();});$('characterTagFilter').addEventListener('change',e=>{characterTagFilter=e.target.value;renderCharacters();});
  $('characterSort').addEventListener('change',async e=>{characterSort=e.target.value;renderCharacters();try{const s=await apiCall('set_character_sort',characterSort);state.settings=s.settings;}catch(_e){}});
  $('characterFilterChips').addEventListener('click',e=>{const b=e.target.closest('.chip');if(!b)return;characterFilter=b.dataset.filter;document.querySelectorAll('#characterFilterChips .chip').forEach(x=>x.classList.toggle('active',x===b));renderCharacters();});
  $('toggleCharacterSelectBtn').onclick=()=>{characterSelectionMode=!characterSelectionMode;if(!characterSelectionMode)selectedCharacters.clear();renderCharacters();updateBulkTagBar();};
  $('selectVisibleCharactersBtn').onclick=()=>{visibleCharacterKeys.forEach(key=>selectedCharacters.add(key));renderCharacters();updateBulkTagBar();};
  $('clearCharacterSelectionBtn').onclick=()=>{selectedCharacters.clear();renderCharacters();updateBulkTagBar();};
  const applyBulkTag=async operation=>{const tag=$('bulkTagInput').value.trim();if(!tag){toast(t('tag_required'),true);return;}if(!selectedCharacters.size)return;setBusy(true,t('loading'));const s=await apiCall('update_character_tags',[...selectedCharacters],tag,operation),r=s.tag_update_result||{};setState(s);setBusy(false);$('bulkTagInput').value='';toast(operation==='add'?t('tag_added',{n:r.changed||0}):t('tag_removed',{n:r.changed||0}));};
  $('addTagSelectedBtn').onclick=()=>applyBulkTag('add');$('removeTagSelectedBtn').onclick=()=>applyBulkTag('remove');
  $('deleteSelected').onclick=()=>requestDelete([...selectedMods]);$('selectAllMods').addEventListener('change',e=>{const mods=filteredMods();if(e.target.checked)mods.forEach(m=>selectedMods.add(m.item_id));else mods.forEach(m=>selectedMods.delete(m.item_id));renderMods();});
  $('chooseFolderBtn').onclick=async()=>{setBusy(true,t('selecting'));const s=await apiCall('choose_mods_folder');setState(s);setBusy(false);if(s.settings.mods_folder)toast(t('folder_configured'));};$('openFolderBtn').onclick=()=>apiCall('open_mods_folder');$('openImagesBtn').onclick=()=>apiCall('open_images_folder');
  $('cacheImagesBtn').onclick=async()=>{setBusy(true,t('caching_images'));const s=await apiCall('cache_character_images'),r=s.image_cache_result||{};setState(s);setBusy(false);toast(t('cache_done',{n:r.downloaded||0,hq:r.high_quality||0,c:r.already_cached||0,f:r.failed||0}));};
  if($('regeneratePairBtn')) $('regeneratePairBtn').onclick=async()=>{setBusy(true,t('loading'));const s=await apiCall('regenerate_mobile_pairing_token');setState(s);setBusy(false);toast(t('mobile_sync_ready'));};
  $('languageSelect').addEventListener('change',async e=>{setBusy(true,t('loading'));const s=await apiCall('set_language',e.target.value);setState(s);setBusy(false);});
  $('autoCatalogUpdates').addEventListener('change',async e=>{const s=await apiCall('set_auto_catalog_updates',e.target.checked);setState(s);});
  $('checkCatalogUpdatesBtn').onclick=async()=>{setBusy(true,t('updating_catalog'));const s=await apiCall('check_catalog_updates'),r=s.catalog_update_result||{};setState(s);setBusy(false);if(r.ok)toast(r.added_count?t('update_added',{n:r.added_count}):t('update_none'));else toast(t('update_failed',{error:r.error||'—'}),true);};
  document.querySelectorAll('[data-close-modal]').forEach(x=>x.addEventListener('click',closeCharacter));document.querySelectorAll('[data-close-preview]').forEach(x=>x.addEventListener('click',closePreview));$('cancelDelete').onclick=()=>{$('confirmModal').classList.add('hidden');pendingDelete=[];};$('confirmDelete').onclick=doDelete;document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeCharacter();closePreview();$('confirmModal').classList.add('hidden');}});
}

async function init(){bind();applyStaticI18n();setBusy(true,t('loading'));const s=await apiCall('get_state');setState(s);setBusy(false);}
window.addEventListener('nikke-mobile-sync',async()=>{try{const s=await apiCall('get_state');setState(s);toast(t('mobile_sync_received'));}catch(_e){}});
window.addEventListener('pywebviewready',init);

/* === Classic v0.15.2 AttachmentSafe: no Pixi loader hang, low-level runtime + sanitized NIKKE atlas (bounds: format) === */
(() => {
  let r8PixiApp = null;
  let r8SpineObj = null;
  let r8Zoom = 1;
  const r8Scripts = [];

  function r8LoadScript(src){
    return new Promise((resolve,reject)=>{
      const existing=[...document.scripts].find(s => (s.getAttribute('src')||'').includes(src));
      if(existing && (src.includes('nikke-spine-runtime') ? window.__NMM_SPINE_LOW__ : true)){
        r8Scripts.push(src+':already'); resolve(); return;
      }
      const s=document.createElement('script');
      s.src=src+'?v=r8lowlevel001';
      s.async=false;
      s.onload=()=>{ r8Scripts.push(src+':ok'); resolve(); };
      s.onerror=()=>{ r8Scripts.push(src+':error'); reject(new Error('No cargó '+src)); };
      document.head.appendChild(s);
    });
  }

  function r8RuntimeInfo(){
    const low=window.__NMM_SPINE_LOW__||{};
    const pixi=low.PIXI||window.PIXI||null;
    const pixiSpine=low.pixiSpine||(pixi&&pixi.spine)||window.pixi_spine||{};
    const base=low.base||{};
    const TextureAtlas=low.TextureAtlas||pixiSpine.TextureAtlas||base.TextureAtlas||null;
    const SpineClass=low.SpineClass||pixiSpine.Spine||(pixi&&pixi.spine&&pixi.spine.Spine)||null;
    const runtimes=[];
    try { window.__nmmV0146MeshFallback && window.__nmmV0146MeshFallback(); } catch(e) {}
    function add(name,obj){ if(obj && obj.SkeletonBinary && obj.AtlasAttachmentLoader && !runtimes.some(x=>x.obj===obj)) runtimes.push({name,obj}); }
    if(Array.isArray(low.runtimes)) for(const r of low.runtimes) add(r.name||'runtime', r.mod||r.obj||r);
    add('3.8', low.spine38); add('3.7', low.spine37); add('4.1', low.spine41);
    add('PIXI.spine38', pixi&&pixi.spine38); add('PIXI.spine37', pixi&&pixi.spine37); add('PIXI.spine41', pixi&&pixi.spine41);
    const summary=`PIXI=${!!pixi}; low=${!!low.version}; TextureAtlas=${!!TextureAtlas}; SpineClass=${!!SpineClass}; runtimes=${runtimes.map(r=>r.name).join(',')||'0'}; scripts=${r8Scripts.join('|')}; lowver=${low.version||''}`;
    return {low,pixi,pixiSpine,TextureAtlas,SpineClass,runtimes,summary};
  }

  async function r8EnsureRuntime(status){
    if(status) status.textContent='Cargando motor NIKKE Spine Viewer / low-level...';
    // Load the viewer libs first only to stay aligned with the uploaded viewer, then load the bundled low-level parser.
    try{ await r8LoadScript('assets/vendor/viewer/pixi.min.js'); }catch(e){}
    try{ await r8LoadScript('assets/vendor/viewer/pixi-spine.js'); }catch(e){}
    await r8LoadScript('assets/vendor/nikke-spine-runtime.js');
    const info=r8RuntimeInfo();
    if(!info.pixi || !info.TextureAtlas || !info.SpineClass || !info.runtimes.length){
      throw new Error('Runtime low-level incompleto. '+info.summary);
    }
    return info;
  }

  function r8Cleanup(){
    try{ if(r8PixiApp){ r8PixiApp.destroy(true,{children:true,texture:false,baseTexture:false}); } }catch(e){}
    r8PixiApp=null; r8SpineObj=null; r8Zoom=1;
  }

  function r8BytesFromB64(b64){
    const bin=atob(String(b64||''));
    const out=new Uint8Array(bin.length);
    for(let i=0;i<bin.length;i++) out[i]=bin.charCodeAt(i);
    return out;
  }

  function r8WaitBaseTexture(baseTexture){
    return new Promise((resolve,reject)=>{
      if(baseTexture.valid) return resolve(baseTexture);
      let done=false;
      const ok=()=>{ if(!done){ done=true; resolve(baseTexture); } };
      try { window.__nmmV0150PatchRuntime && window.__nmmV0150PatchRuntime(); } catch(e) {}
      const bad=(e)=>{ if(!done){ done=true; reject(e||new Error('No cargó textura Spine')); } };
      try{ baseTexture.once('loaded', ok); baseTexture.once('error', bad); }catch(e){}
      try { window.__nmmV0150PatchRuntime && window.__nmmV0150PatchRuntime(); } catch(e) {}
      setTimeout(()=>{ if(!done){ if(baseTexture.valid) ok(); else bad(new Error('Timeout cargando textura Spine')); } }, 8000);
    });
  }

  function r8PickAnimation(anims, action){
    const list=(anims||[]).map(a=>String(a)).filter(Boolean);
    const low=list.map(a=>a.toLowerCase());
    const hints=[];
    action=String(action||'').toLowerCase();
    if(action.includes('aim')) hints.push('aim_idle','aim','idle','stand');
    if(action.includes('cover')) hints.push('cover_idle','cover','idle','stand');
    if(action.includes('standing')) hints.push('idle','stand','wait','loop');
    hints.push('idle','stand','wait','loop');
    for(const h of hints){ const i=low.findIndex(a=>a.includes(h)); if(i>=0) return list[i]; }
    return list[0]||'';
  }

  function r8Fit(){
    if(!r8PixiApp || !r8SpineObj) return;
    const w=r8PixiApp.renderer.width||900;
    const h=r8PixiApp.renderer.height||560;
    try{ r8SpineObj.update(0.016); }catch(e){}
    let b;
    try{ b=r8SpineObj.getLocalBounds(); }catch(e){ b={x:-200,y:-400,width:400,height:800}; }
    const bw=Math.max(1,b.width||1), bh=Math.max(1,b.height||1);
    let scale=Math.min((w*.82)/bw,(h*.86)/bh);
    if(!isFinite(scale)||scale<=0) scale=1;
    r8SpineObj.scale.set(scale*r8Zoom);
    r8SpineObj.x=(w/2)-((b.x+bw/2)*r8SpineObj.scale.x);
    r8SpineObj.y=(h/2)-((b.y+bh/2)*r8SpineObj.scale.y);
  }

  async function r8BuildSkeletonData(r, info){
    const PIXI8=info.pixi;
    const baseTexture=PIXI8.BaseTexture.from(r.spine_texture_url);
    await r8WaitBaseTexture(baseTexture);
    // The texture exported by preview.py is already padded to the atlas canvas. One baseTexture is enough for NIKKE one-page atlases.
    try { window.__nmmPatchSpineAtlasSequences && window.__nmmPatchSpineAtlasSequences(); } catch(e) {}
      try { window.__nmmInstallRuntimeCompat && window.__nmmInstallRuntimeCompat(); } catch(e) {}
      try { window.__nmmV0150PatchRuntime && window.__nmmV0150PatchRuntime(); } catch(e) {}
    const atlas=new info.TextureAtlas(String(r.spine_atlas_text||''), function(_line, callback){ callback(baseTexture); });
    const bytes=r8BytesFromB64(r.spine_skel_b64);
    let lastErr=null;
    for(const pair of info.runtimes){
      const Runtime=pair.obj||pair.mod||pair;
      try{
        try { window.__nmmV0146MeshFallback && window.__nmmV0146MeshFallback(); } catch(e) {}
        if(!Runtime || !Runtime.SkeletonBinary || !Runtime.AtlasAttachmentLoader) continue;
        try { window.__nmmPatchSpineAtlasSequences && window.__nmmPatchSpineAtlasSequences(); } catch(e) {}
      try { window.__nmmInstallRuntimeCompat && window.__nmmInstallRuntimeCompat(); } catch(e) {}
      try { window.__nmmV0150PatchRuntime && window.__nmmV0150PatchRuntime(); } catch(e) {}
        const atlasLoader=new Runtime.AtlasAttachmentLoader(atlas);
        try { window.__nmmHardenAttachmentLoader && window.__nmmHardenAttachmentLoader(atlasLoader, atlas); } catch(e) {}
        try { window.__nmmPatchSpineAtlasSequences && window.__nmmPatchSpineAtlasSequences(); } catch(e) {}
        try { window.__nmmPatchSpineAttachmentNulls && window.__nmmPatchSpineAttachmentNulls(); } catch(e) {}
        try { window.__nmmV0146MeshFallback && window.__nmmV0146MeshFallback(); } catch(e) {}
      try { window.__nmmInstallRuntimeCompat && window.__nmmInstallRuntimeCompat(); } catch(e) {}
      try { window.__nmmV0150PatchRuntime && window.__nmmV0150PatchRuntime(); } catch(e) {}
        const binary=new Runtime.SkeletonBinary(atlasLoader);
        binary.scale=1;
        try { window.__nmmPatchSpineAtlasSequences && window.__nmmPatchSpineAtlasSequences(); } catch(e) {}
        try { window.__nmmPatchSpineAttachmentNulls && window.__nmmPatchSpineAttachmentNulls(); } catch(e) {}
        try { window.__nmmV0146MeshFallback && window.__nmmV0146MeshFallback(); } catch(e) {}
      try { window.__nmmInstallRuntimeCompat && window.__nmmInstallRuntimeCompat(); } catch(e) {}
      try { window.__nmmV0150PatchRuntime && window.__nmmV0150PatchRuntime(); } catch(e) {}
        const data=binary.readSkeletonData(bytes);
        if(data) return {data, runtime: pair.name||'runtime'};
      }catch(e){ lastErr=e; }
    }
    throw lastErr || new Error('Ningún runtime pudo leer el .skel');
  }

  async function r8RenderSpine(r){
    const host=document.getElementById('r8SpineHost');
    const fallback=document.getElementById('r8TextureFallback');
    const status=document.getElementById('r8SpineStatus');
    const controls=document.getElementById('r8SpineControls');
    try{
      r8Cleanup();
      const info=await r8EnsureRuntime(status);
      const width=Math.max(640,host?.clientWidth||900), height=Math.max(420,host?.clientHeight||560);
      r8PixiApp=new info.pixi.Application({width,height,backgroundAlpha:0,antialias:true,autoDensity:true,transparent:true,preserveDrawingBuffer:true,resolution:window.devicePixelRatio||1});
      host.innerHTML=''; host.appendChild(r8PixiApp.view);
      if(status) status.textContent='Leyendo .skel + .atlas con low-level...';
      const built=await r8BuildSkeletonData(r, info);
      try { window.__nmmV0150PatchRuntime && window.__nmmV0150PatchRuntime(); } catch(e) {}
      r8SpineObj=new info.SpineClass(built.data);
      r8SpineObj.autoUpdate=true;
      r8PixiApp.stage.addChild(r8SpineObj);
      const animations=(built.data.animations||[]).map(a=>a.name||String(a));
      const chosen=r8PickAnimation(animations,r.action_hint||r.action||'');
      if(chosen && r8SpineObj.state) r8SpineObj.state.setAnimation(0,chosen,true);
      r8Fit();
      if(fallback) fallback.style.display='none';
      if(host) host.style.display='block';
      if(status) status.textContent=(chosen?`Modelo Spine armado · runtime ${built.runtime} · animación: ${chosen}`:`Modelo Spine armado · runtime ${built.runtime}`);
      if(controls){
        controls.innerHTML='<button id="r8PauseBtn">Pausa</button><select id="r8AnimSelect"></select><button id="r8FitBtn">Ajustar</button><button id="r8ZoomOut">−</button><button id="r8ZoomIn">+</button><button id="r8ToggleTexture">Ver textura</button><button id="r8DebugBtn">Debug v0.15.2</button>';
        const sel=document.getElementById('r8AnimSelect');
        if(sel){ sel.innerHTML=animations.map(n=>`<option value="${esc(n)}">${esc(n)}</option>`).join(''); if(chosen) sel.value=chosen; sel.onchange=()=>{ try{ r8SpineObj.state.setAnimation(0,sel.value,true); if(status) status.textContent=`Modelo Spine armado · runtime ${built.runtime} · animación: ${sel.value}`; }catch(e){} }; }
        const pause=document.getElementById('r8PauseBtn'); if(pause) pause.onclick=()=>{ if(!r8PixiApp) return; if(r8PixiApp.ticker.started){ r8PixiApp.ticker.stop(); pause.textContent='Reanudar'; } else { r8PixiApp.ticker.start(); pause.textContent='Pausa'; } };
        const fit=document.getElementById('r8FitBtn'); if(fit) fit.onclick=()=>{ r8Zoom=1; r8Fit(); };
        const zout=document.getElementById('r8ZoomOut'); if(zout) zout.onclick=()=>{ r8Zoom=Math.max(.25,r8Zoom-.1); r8Fit(); };
        const zin=document.getElementById('r8ZoomIn'); if(zin) zin.onclick=()=>{ r8Zoom=Math.min(3,r8Zoom+.1); r8Fit(); };
        const tog=document.getElementById('r8ToggleTexture'); if(tog) tog.onclick=()=>{ const tex=fallback&&fallback.style.display!=='none'; if(tex){ fallback.style.display='none'; host.style.display='block'; tog.textContent='Ver textura'; } else { fallback.style.display='block'; host.style.display='none'; tog.textContent='Ver armado'; } };
        const dbg=document.getElementById('r8DebugBtn'); if(dbg) dbg.onclick=()=>alert(r8RuntimeInfo().summary+'; canvas='+(r.spine_canvas_width||'?')+'x'+(r.spine_canvas_height||'?')+'; pages='+(r.spine_atlas_pages||[]).join(','));
      }
    }catch(err){
      console.error('Classic v0.15.2 AttachmentSafe render failed',err);
      r8Cleanup();
      if(host) host.style.display='none';
      if(fallback) fallback.style.display='block';
      if(status){
        let dbg='';
        try{ dbg=r8RuntimeInfo().summary; }catch(e){ dbg='sin runtime info'; }
        dbg += '; canvas='+(r.spine_canvas_width||'?')+'x'+(r.spine_canvas_height||'?')+'; texture='+(r.texture_width||'?')+'x'+(r.texture_height||'?')+'; pages='+(r.spine_atlas_pages||[]).join(',');
        status.innerHTML='No se pudo armar con Viewer LowLevel: '+esc(err&&err.message?err.message:err)+'<br><small>DEBUG v0.15.2 · '+esc(dbg)+'</small>';
      }
      if(controls) controls.innerHTML='<button id="r8OnlyTexture">Mostrando textura fallback</button><button id="r8DebugFail">Debug v0.15.2</button>';
      const b=document.getElementById('r8DebugFail'); if(b) b.onclick=()=>alert((()=>{try{return r8RuntimeInfo().summary}catch(e){return String(e)}})());
    }
  }

  window.closePreview=function(){ r8Cleanup(); const modal=document.getElementById('previewModal'); if(modal) modal.classList.add('hidden'); };
  window.openPreview=async function(itemId){
    const m=state?.items?.find(x=>x.item_id===itemId);
    const pc=document.getElementById('previewContent'); const pm=document.getElementById('previewModal');
    if(!pc||!pm) return;
    r8Cleanup();
    pc.innerHTML=`<div class="preview-loading"><div class="preview-spinner">↻</div><h2>${esc(t('preview_title'))}</h2><p>Cargando con motor Viewer LowLevel...</p>${m?`<div class="preview-mod-label">${esc(m.mod_title||m.name)}</div>`:''}</div>`;
    pm.classList.remove('hidden');
    try{
      const r=await apiCall('preview_item',itemId);
      if(!r?.ok){ pc.innerHTML=`<div class="preview-error"><div class="preview-error-icon">⚠</div><h2>${esc(t('preview_title'))}</h2><p>${esc(t('preview_failed',{error:r?.error||'—'}))}</p><div class="detail-path">${esc(r?.path||m?.path||'')}</div></div>`; return; }
      const canSpine=!!(r.spine_ready&&r.spine_canvas&&r.spine_skel_b64&&r.spine_atlas_text&&r.spine_texture_url);
      pc.innerHTML=`<div class="preview-head"><div><div class="preview-kicker">Preview Alpha · Classic v0.15.2 AttachmentSafe</div><h2>${esc(r.mod_name||m?.mod_title||'Mod')}</h2><p>${esc(r.character_name||'')} · ID ${esc(r.id||'')} · Ver ${esc(r.version||'')} · ${esc((r.action||m?.action||'').toString())}</p></div><span class="preview-chip">${canSpine?'SPINE':'TEXTURA'}</span></div><div style="background:#05080d;border-top:1px solid rgba(255,255,255,.08);border-bottom:1px solid rgba(255,255,255,.08);min-height:560px;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden;"><div id="r8SpineHost" style="width:100%;height:560px;display:${canSpine?'block':'none'};"></div><img id="r8TextureFallback" src="${esc(r.preview_url)}" style="display:${canSpine?'none':'block'};max-width:100%;max-height:560px;object-fit:contain;" /></div><div id="r8SpineControls" style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:10px 14px;background:#0f1928;border-bottom:1px solid rgba(255,255,255,.08);"></div><div class="preview-warning" id="r8SpineStatus">${canSpine?'Preparando modelo armado con Viewer LowLevel...':esc(r.warning||'Fallback de textura.')}</div><div class="preview-grid"><div><span>${esc(t('preview_texture'))}</span><b>${esc(r.texture_name||'—')} · ${esc(r.texture_width||'')}×${esc(r.texture_height||'')} → atlas ${esc(r.spine_canvas_width||'')}×${esc(r.spine_canvas_height||'')}</b></div><div><span>SPINE</span><b>${canSpine?`${esc(r.spine_skel_name||'skel')} + ${esc(r.spine_atlas_name||'atlas')}`:'No detectado'}</b></div><div><span>${esc(t('preview_source'))}</span><b>${esc(r.source_file||'Unity bundle')}</b></div><div><span>${esc(t('preview_detected'))}</span><b>ID ${esc(r.character_id_detected||r.id||'—')} · ${esc(r.pose_detected||r.action_hint||'—')}</b></div></div>`;
      if(canSpine) setTimeout(()=>r8RenderSpine(r),50);
    }catch(err){ pc.innerHTML=`<div class="preview-error"><div class="preview-error-icon">⚠</div><h2>${esc(t('preview_title'))}</h2><p>${esc(err?.message||err)}</p></div>`; }
  };
})();


// --- NMM v0.14.4 Spine sequence + nullable attachment patch ----------------
(function () {
  if (window.__NMM_V0144_SEQUENCE_ATTACH_PATCH__) return;
  window.__NMM_V0144_SEQUENCE_ATTACH_PATCH__ = true;

  function variants(name) {
    var s = String(name == null ? '' : name);
    var out = [];
    function add(v) { if (v && v !== s && out.indexOf(v) < 0) out.push(v); }
    add(s.replace(/\d+$/, ''));
    add(s.replace(/[_-]?\d+$/, ''));
    add(s.replace(/t\d+$/, 't'));
    add(s.replace(/([a-z_]+)[0-9]+$/i, '$1'));
    return out;
  }

  function safeName(name, path, prefix) {
    var n = (name == null || name === '') ? (path || '') : name;
    if (n == null || n === '') n = (prefix || 'attachment') + '_unnamed';
    return String(n);
  }

  function scanRegions(atlas, wanted) {
    var list = variants(wanted);
    var regs = atlas && atlas.regions;
    if (!regs || !regs.length) return null;
    for (var n = 0; n < list.length; n++) {
      for (var i = 0; i < regs.length; i++) {
        var r = regs[i];
        if (r && r.name === list[n]) return r;
      }
    }
    return null;
  }

  function patchTextureAtlasClass(Ctor) {
    if (!Ctor || !Ctor.prototype) return false;
    var proto = Ctor.prototype;
    if (proto.__nmm_v0144_findRegion_patched) return true;
    var original = proto.findRegion;
    if (typeof original !== 'function') return false;
    proto.findRegion = function (name) {
      var r = original.call(this, name);
      if (r) return r;
      var vs = variants(name);
      for (var i = 0; i < vs.length; i++) {
        try { r = original.call(this, vs[i]); if (r) return r; } catch (e) {}
      }
      r = scanRegions(this, name);
      return r || null;
    };
    proto.__nmm_v0144_findRegion_patched = true;
    return true;
  }

  function patchAttachmentCtor(ns, key, fallback) {
    if (!ns || !ns[key] || ns[key].__nmm_v0144_safe_ctor) return false;
    var Original = ns[key];
    try {
      var Safe = function(name) {
        var finalName = safeName(name, null, fallback);
        return Reflect.construct(Original, [finalName], Safe);
      };
      Object.setPrototypeOf(Safe, Original);
      Safe.prototype = Original.prototype;
      Safe.__nmm_v0144_safe_ctor = true;
      ns[key] = Safe;
      return true;
    } catch (e) {
      return false;
    }
  }

  function patchLoaderClass(Ctor) {
    if (!Ctor || !Ctor.prototype) return false;
    var proto = Ctor.prototype;
    if (proto.__nmm_v0144_loader_patched) return true;

    function wrapRegionLike(method, prefix) {
      var original = proto[method];
      if (typeof original !== 'function') return;
      proto[method] = function (skin, name, path) {
        var args = Array.prototype.slice.call(arguments);
        var fixedPath = (path == null || path === '') ? (name || '') : path;
        var fixedName = safeName(name, fixedPath, prefix);
        args[1] = fixedName;
        args[2] = fixedPath || fixedName;
        try {
          return original.apply(this, args);
        } catch (err) {
          var msg = String((err && err.message) || err || '');
          if (!/Region not found|Attachment name must not be null/i.test(msg)) throw err;
          var vs = variants(args[2]);
          for (var i = 0; i < vs.length; i++) {
            var retryArgs = args.slice();
            retryArgs[1] = safeName(fixedName, vs[i], prefix);
            retryArgs[2] = vs[i];
            try { return original.apply(this, retryArgs); } catch (e) {}
          }
          throw err;
        }
      };
    }

    function wrapNameOnly(method, prefix) {
      var original = proto[method];
      if (typeof original !== 'function') return;
      proto[method] = function (skin, name) {
        var args = Array.prototype.slice.call(arguments);
        args[1] = safeName(name, null, prefix);
        return original.apply(this, args);
      };
    }

    wrapRegionLike('newRegionAttachment', 'region');
    wrapRegionLike('newMeshAttachment', 'mesh');
    wrapNameOnly('newBoundingBoxAttachment', 'bbox');
    wrapNameOnly('newPathAttachment', 'path');
    wrapNameOnly('newPointAttachment', 'point');
    wrapNameOnly('newClippingAttachment', 'clip');
    proto.__nmm_v0144_loader_patched = true;
    return true;
  }

  function collectNamespaces() {
    var out = [];
    function add(x) { if (x && out.indexOf(x) < 0) out.push(x); }
    add(window.spine); add(window.spine && window.spine.core);
    add(window.spine38); add(window.spine41);
    add(window.pixi_spine); add(window.pixi_spine && window.pixi_spine.core);
    add(window.pixi_spine && window.pixi_spine.base);
    add(window.pixi_spine && window.pixi_spine.spine38);
    add(window.pixi_spine && window.pixi_spine.spine41);
    add(window.PIXI && window.PIXI.spine);
    add(window.PIXI && window.PIXI.spine && window.PIXI.spine.core);
    add(window.PIXI && window.PIXI.spine && window.PIXI.spine.base);
    add(window.PIXI && window.PIXI.spine && window.PIXI.spine.spine38);
    add(window.PIXI && window.PIXI.spine && window.PIXI.spine.spine41);
    return out;
  }

  window.__nmmPatchSpineAtlasSequences = function () {
    var ok = false;
    var ns = collectNamespaces();
    for (var i = 0; i < ns.length; i++) {
      try {
        ok = patchTextureAtlasClass(ns[i].TextureAtlas) || ok;
        ok = patchLoaderClass(ns[i].AtlasAttachmentLoader) || ok;
        ok = patchAttachmentCtor(ns[i], 'RegionAttachment', 'region') || ok;
        ok = patchAttachmentCtor(ns[i], 'MeshAttachment', 'mesh') || ok;
        ok = patchAttachmentCtor(ns[i], 'BoundingBoxAttachment', 'bbox') || ok;
        ok = patchAttachmentCtor(ns[i], 'PathAttachment', 'path') || ok;
        ok = patchAttachmentCtor(ns[i], 'PointAttachment', 'point') || ok;
        ok = patchAttachmentCtor(ns[i], 'ClippingAttachment', 'clip') || ok;
      } catch (e) {}
    }
    return ok;
  };

  var tries = 0;
  var timer = setInterval(function () {
    tries++;
    if (window.__nmmPatchSpineAtlasSequences() || tries > 600) clearInterval(timer);
  }, 20);
})();
// --- end NMM v0.14.4 --------------------------------------------------------



// --- NMM v0.14.5 Spine AttachmentNullFix -------------------------------
(function(){
  if (window.__NMM_V0145_ATTACHMENT_NULLFIX__) return;
  window.__NMM_V0145_ATTACHMENT_NULLFIX__ = true;
  var seq = 0;
  function safeName(name, path, prefix){
    var n = (name == null || name === '') ? (path || '') : name;
    if (n == null || n === '') n = (prefix || 'attachment') + '_auto_' + (++seq);
    return String(n);
  }
  function vars(name){
    var s = String(name == null ? '' : name), out=[];
    function add(v){ if(v && v!==s && out.indexOf(v)<0) out.push(v); }
    add(s.replace(/\d+$/,''));
    add(s.replace(/[_-]?\d+$/,''));
    add(s.replace(/([a-z_]+)[0-9]+$/i,'$1'));
    return out;
  }
  function findRegion(atlas, name){
    if(!atlas) return null;
    var r = null;
    try { if (typeof atlas.findRegion === 'function') r = atlas.findRegion(name); } catch(e) {}
    if(r) return r;
    var v = vars(name);
    for(var i=0;i<v.length;i++){ try { r = atlas.findRegion(v[i]); if(r) return r; } catch(e){} }
    var regs = atlas.regions || [];
    for(var j=0;j<regs.length;j++){
      if(regs[j] && (regs[j].name === name || v.indexOf(regs[j].name)>=0)) return regs[j];
    }
    return null;
  }
  function namespaces(){
    var a=[]; function add(x){ if(x && a.indexOf(x)<0) a.push(x); }
    add(window.spine); add(window.spine&&window.spine.core); add(window.spine38); add(window.spine41);
    add(window.pixi_spine); add(window.pixi_spine&&window.pixi_spine.core); add(window.pixi_spine&&window.pixi_spine.base); add(window.pixi_spine&&window.pixi_spine.spine38); add(window.pixi_spine&&window.pixi_spine.spine41);
    add(window.PIXI&&window.PIXI.spine); add(window.PIXI&&window.PIXI.spine&&window.PIXI.spine.core); add(window.PIXI&&window.PIXI.spine&&window.PIXI.spine.base); add(window.PIXI&&window.PIXI.spine&&window.PIXI.spine.spine38); add(window.PIXI&&window.PIXI.spine&&window.PIXI.spine.spine41);
    return a;
  }
  function ctor(name){
    var ns = namespaces();
    for(var i=0;i<ns.length;i++){ if(typeof ns[i][name] === 'function') return ns[i][name]; }
    return null;
  }
  function setRegion(att, reg, path){
    try { if (att.setRegion) att.setRegion(reg); else att.region = reg; } catch(e) { try { att.region = reg; } catch(_){} }
    try { att.rendererObject = reg; } catch(e) {}
    try { if(path) att.path = String(path); } catch(e) {}
    return att;
  }
  function patchAtlas(C){
    if(!C || !C.prototype || C.prototype.__nmm_v0145) return false;
    var old = C.prototype.findRegion; if(typeof old !== 'function') return false;
    C.prototype.findRegion = function(name){
      var r = null; try { r = old.call(this, name); } catch(e) {}
      if(r) return r;
      var v = vars(name);
      for(var i=0;i<v.length;i++){ try { r = old.call(this, v[i]); if(r) return r; } catch(e){} }
      var regs = this.regions || [];
      for(var j=0;j<regs.length;j++) if(regs[j] && v.indexOf(regs[j].name)>=0) return regs[j];
      return null;
    };
    C.prototype.__nmm_v0145 = true; return true;
  }
  function patchLoaderProto(C){
    if(!C || !C.prototype || C.prototype.__nmm_v0145_loader) return false;
    C.prototype.newRegionAttachment = function(skin, name, path, sequence){
      var p = path || name; var n = safeName(name, p, 'region');
      var reg = findRegion(this.atlas || this.textureAtlas || this._atlas, p) || findRegion(this.atlas || this.textureAtlas || this._atlas, n);
      if(!reg) throw new Error('Region not found in atlas: ' + p + ' (sequence: ' + name + ')');
      var RC = ctor('RegionAttachment'); if(!RC) throw new Error('RegionAttachment class not available');
      var a = new RC(n); if(sequence) try{ a.sequence = sequence; }catch(e){}
      return setRegion(a, reg, p);
    };
    C.prototype.newMeshAttachment = function(skin, name, path, sequence){
      var p = path || name; var n = safeName(name, p, 'mesh');
      var reg = findRegion(this.atlas || this.textureAtlas || this._atlas, p) || findRegion(this.atlas || this.textureAtlas || this._atlas, n);
      var MC = ctor('MeshAttachment') || (window.__nmmV0146MeshFallback && window.__nmmV0146MeshFallback() && ctor('MeshAttachment')) || ctor('RegionAttachment');
      var a = new MC(n); if(reg) setRegion(a, reg, p); if(sequence) try{ a.sequence = sequence; }catch(e){}
      return a;
    };
    [['newBoundingBoxAttachment','BoundingBoxAttachment','bbox'],['newPathAttachment','PathAttachment','path'],['newPointAttachment','PointAttachment','point'],['newClippingAttachment','ClippingAttachment','clip']].forEach(function(x){
      C.prototype[x[0]] = function(skin, name){ var K = ctor(x[1]); if(!K) throw new Error(x[1]+' class not available'); return new K(safeName(name, null, x[2])); };
    });
    C.prototype.__nmm_v0145_loader = true; return true;
  }
  function patchParser(C){
    if(!C || !C.prototype || C.prototype.__nmm_v0145_parser) return false;
    var old = C.prototype.readAttachment;
    if(typeof old === 'function'){
      C.prototype.readAttachment = function(){
        var args = Array.prototype.slice.call(arguments);
        if(args.length > 3 && (args[3] == null || args[3] === '')) args[3] = 'auto_attachment_' + (++seq);
        return old.apply(this, args);
      };
    }
    C.prototype.__nmm_v0145_parser = true; return true;
  }
  function patchAll(){
    var ok=false, ns=namespaces();
    for(var i=0;i<ns.length;i++){
      try{ ok = patchAtlas(ns[i].TextureAtlas) || ok; }catch(e){}
      try{ ok = patchLoaderProto(ns[i].AtlasAttachmentLoader) || ok; }catch(e){}
      try { window.__nmmV0146MeshFallback && window.__nmmV0146MeshFallback(); } catch(e) {}
      try{ ok = patchParser(ns[i].SkeletonBinary) || ok; }catch(e){}
      try { window.__nmmV0146MeshFallback && window.__nmmV0146MeshFallback(); } catch(e) {}
      try{ ok = patchParser(ns[i].SkeletonJson) || ok; }catch(e){}
    }
    return ok;
  }
  window.__nmmPatchSpineAtlasSequences = function(){ return patchAll(); };
  window.__nmmPatchSpineAttachmentNulls = patchAll;
  window.__nmmHardenAttachmentLoader = function(loader, atlas){
    patchAll();
    if(!loader) return false;
    try{ if(atlas && !loader.atlas) loader.atlas = atlas; }catch(e){}
    var L = loader.constructor; patchLoaderProto(L);
    return true;
  };
  var t=0, timer=setInterval(function(){ t++; if(patchAll() || t>600) clearInterval(timer); },20);
})();
// --- end NMM v0.14.5 ---------------------------------------------------



// --- NMM v0.14.6 MeshAttachment fallback patch --------------------------
(function(){
  if (window.__NMM_V0146_MESH_FALLBACK__) return;
  window.__NMM_V0146_MESH_FALLBACK__ = true;
  var seq = 0;
  function nsList(){
    var out=[]; function add(x){ if(x && out.indexOf(x)<0) out.push(x); }
    add(window.spine); add(window.spine&&window.spine.core); add(window.spine38); add(window.spine41);
    add(window.pixi_spine); add(window.pixi_spine&&window.pixi_spine.core); add(window.pixi_spine&&window.pixi_spine.base); add(window.pixi_spine&&window.pixi_spine.spine38); add(window.pixi_spine&&window.pixi_spine.spine41);
    add(window.PIXI&&window.PIXI.spine); add(window.PIXI&&window.PIXI.spine&&window.PIXI.spine.core); add(window.PIXI&&window.PIXI.spine&&window.PIXI.spine.base); add(window.PIXI&&window.PIXI.spine&&window.PIXI.spine.spine38); add(window.PIXI&&window.PIXI.spine&&window.PIXI.spine.spine41);
    return out;
  }
  function ctor(name){
    var ns=nsList();
    for(var i=0;i<ns.length;i++) if(typeof ns[i][name] === 'function') return ns[i][name];
    return null;
  }
  function safeName(name,path,prefix){
    var n = (name == null || name === '') ? (path || '') : name;
    if(n == null || n === '') n = (prefix || 'attachment') + '_auto_' + (++seq);
    return String(n);
  }
  function variants(name){
    var s=String(name == null ? '' : name), out=[];
    function add(v){ if(v && v!==s && out.indexOf(v)<0) out.push(v); }
    add(s.replace(/\d+$/,''));
    add(s.replace(/[_-]?\d+$/,''));
    add(s.replace(/([a-z_]+)[0-9]+$/i,'$1'));
    add(s.replace(/t\d+$/,'t'));
    return out;
  }
  function findRegion(atlas, name){
    if(!atlas) return null;
    var r=null;
    try{ if(typeof atlas.findRegion==='function') r=atlas.findRegion(name); }catch(e){}
    if(r) return r;
    var vs=variants(name);
    for(var i=0;i<vs.length;i++){ try{ r=atlas.findRegion(vs[i]); if(r) return r; }catch(e){} }
    var regs=atlas.regions||[];
    for(var j=0;j<regs.length;j++){
      if(!regs[j]) continue;
      if(regs[j].name===name || vs.indexOf(regs[j].name)>=0) return regs[j];
    }
    return null;
  }
  function setRegion(att, reg, path){
    if(!att) return att;
    try{ att.region = reg || att.region || null; }catch(e){}
    try{ att.rendererObject = reg || att.rendererObject || null; }catch(e){}
    try{ if(path) att.path = String(path); }catch(e){}
    try{ if(reg && att.setRegion) att.setRegion(reg); }catch(e){}
    try{ if(att.updateUVs) att.updateUVs(); }catch(e){}
    return att;
  }
  function makeMeshPolyfill(){
    var existing = ctor('MeshAttachment');
    if(existing) return existing;
    var RC = ctor('RegionAttachment');
    function MeshAttachment(name){
      this.name = safeName(name, null, 'mesh');
      this.path = this.name;
      this.region = null;
      this.rendererObject = null;
      this.regionUVs = [];
      this.uvs = [];
      this.triangles = [];
      this.vertices = [];
      this.bones = null;
      this.worldVerticesLength = 0;
      this.hullLength = 0;
      this.edges = [];
      this.width = 0;
      this.height = 0;
      this.parentMesh = null;
      this.inheritDeform = false;
      this.color = { r:1, g:1, b:1, a:1 };
    }
    if(RC && RC.prototype){
      MeshAttachment.prototype = Object.create(RC.prototype);
      MeshAttachment.prototype.constructor = MeshAttachment;
    }
    MeshAttachment.prototype.setRegion = function(region){ this.region=region; this.rendererObject=region; };
    MeshAttachment.prototype.updateUVs = function(){
      if(this.uvs && this.regionUVs && this.regionUVs.length && this.uvs.length !== this.regionUVs.length){
        this.uvs = Array.prototype.slice.call(this.regionUVs);
      }
    };
    MeshAttachment.prototype.applyDeform = function(){ return true; };
    MeshAttachment.prototype.computeWorldVertices = function(){ return; };
    MeshAttachment.prototype.copy = function(){
      var m = new MeshAttachment(this.name);
      for(var k in this){ try{ m[k]=Array.isArray(this[k]) ? this[k].slice() : this[k]; }catch(e){} }
      return m;
    };
    var ns=nsList();
    for(var i=0;i<ns.length;i++){ try{ if(!ns[i].MeshAttachment) ns[i].MeshAttachment = MeshAttachment; }catch(e){} }
    return MeshAttachment;
  }
  function patchLoader(C){
    if(!C || !C.prototype || C.prototype.__nmm_v0146_meshfallback) return false;
    var p=C.prototype;
    p.newMeshAttachment = function(skin, name, path, sequence){
      var atlas = this.atlas || this.textureAtlas || this._atlas;
      var pth = path || name;
      var n = safeName(name, pth, 'mesh');
      var MC = makeMeshPolyfill();
      var att = new MC(n);
      var reg = findRegion(atlas, pth) || findRegion(atlas, n);
      setRegion(att, reg, pth || n);
      if(sequence) try{ att.sequence = sequence; }catch(e){}
      return att;
    };
    var oldRegion = p.newRegionAttachment;
    p.newRegionAttachment = function(skin, name, path, sequence){
      var atlas = this.atlas || this.textureAtlas || this._atlas;
      var pth = path || name;
      var n = safeName(name, pth, 'region');
      var RC = ctor('RegionAttachment');
      if(RC){
        var a = new RC(n);
        var reg = findRegion(atlas, pth) || findRegion(atlas, n);
        if(!reg && oldRegion) return oldRegion.apply(this, arguments);
        setRegion(a, reg, pth || n);
        if(sequence) try{ a.sequence = sequence; }catch(e){}
        return a;
      }
      return oldRegion.apply(this, arguments);
    };
    p.__nmm_v0146_meshfallback=true;
    return true;
  }
  function patchParser(C){
    if(!C || !C.prototype || C.prototype.__nmm_v0146_parser) return false;
    var old=C.prototype.readAttachment;
    if(typeof old==='function'){
      C.prototype.readAttachment=function(){
        makeMeshPolyfill();
        var args=Array.prototype.slice.call(arguments);
        for(var i=0;i<args.length;i++){
          if(i>0 && (args[i]===null || args[i]==='')) args[i]='auto_attachment_'+(++seq);
        }
        return old.apply(this,args);
      };
    }
    C.prototype.__nmm_v0146_parser=true;
    return true;
  }
  function patchAll(){
    makeMeshPolyfill();
    var ok=false, ns=nsList();
    for(var i=0;i<ns.length;i++){
      try{ ok=patchLoader(ns[i].AtlasAttachmentLoader)||ok; }catch(e){}
      try{ ok=patchParser(ns[i].SkeletonBinary)||ok; }catch(e){}
      try{ ok=patchParser(ns[i].SkeletonJson)||ok; }catch(e){}
    }
    return ok;
  }
  window.__nmmV0146MeshFallback = patchAll;
  var t=0, timer=setInterval(function(){ t++; if(patchAll() || t>800) clearInterval(timer); },20);
})();
// --- end NMM v0.14.6 ---------------------------------------------------




// --- NMM v0.14.7 Runtime Diagnostic SIMPLE ---------------------------------
(function () {
  if (window.__NMM_V0147_RUNTIME_DIAG_SIMPLE__) return;
  window.__NMM_V0147_RUNTIME_DIAG_SIMPLE__ = true;
  window.__nmmDiagErrors = window.__nmmDiagErrors || [];

  function errText(err) {
    try {
      if (!err) return '';
      if (err.message) return err.message;
      if (err.reason && err.reason.message) return err.reason.message;
      return String(err);
    } catch(e) { return 'error converting error'; }
  }
  function pushErr(type, err) {
    try {
      window.__nmmDiagErrors.push({
        time: new Date().toISOString(),
        type: type,
        message: errText(err),
        stack: String((err && err.stack) || (err && err.error && err.error.stack) || '').slice(0, 1500)
      });
      if (window.__nmmDiagErrors.length > 30) window.__nmmDiagErrors.shift();
    } catch(e) {}
  }
  window.addEventListener('error', function(e){ pushErr('window.error', e.error || e.message || e); });
  window.addEventListener('unhandledrejection', function(e){ pushErr('unhandledrejection', e.reason || e); });

  function add(arr, label, obj) {
    if (obj && arr.every(function(x){ return x.obj !== obj; })) arr.push({label: label, obj: obj});
  }
  function namespaces() {
    var P = window.PIXI, a = [];
    add(a, 'window.spine', window.spine);
    add(a, 'window.spine.core', window.spine && window.spine.core);
    add(a, 'window.spine38', window.spine38);
    add(a, 'window.spine41', window.spine41);
    add(a, 'window.pixi_spine', window.pixi_spine);
    add(a, 'window.pixi_spine.core', window.pixi_spine && window.pixi_spine.core);
    add(a, 'window.pixi_spine.base', window.pixi_spine && window.pixi_spine.base);
    add(a, 'window.pixi_spine.spine37', window.pixi_spine && window.pixi_spine.spine37);
    add(a, 'window.pixi_spine.spine38', window.pixi_spine && window.pixi_spine.spine38);
    add(a, 'window.pixi_spine.spine40', window.pixi_spine && window.pixi_spine.spine40);
    add(a, 'window.pixi_spine.spine41', window.pixi_spine && window.pixi_spine.spine41);
    add(a, 'PIXI.spine', P && P.spine);
    add(a, 'PIXI.spine.core', P && P.spine && P.spine.core);
    add(a, 'PIXI.spine.base', P && P.spine && P.spine.base);
    add(a, 'PIXI.spine.spine37', P && P.spine && P.spine.spine37);
    add(a, 'PIXI.spine.spine38', P && P.spine && P.spine.spine38);
    add(a, 'PIXI.spine.spine40', P && P.spine && P.spine.spine40);
    add(a, 'PIXI.spine.spine41', P && P.spine && P.spine.spine41);
    return a;
  }
  var classes = [
    'TextureAtlas','TextureAtlasPage','TextureAtlasRegion','AtlasAttachmentLoader',
    'SkeletonBinary','SkeletonJson','Skeleton','Spine','Skin','Slot','SlotData','Bone','BoneData',
    'RegionAttachment','MeshAttachment','PointAttachment','BoundingBoxAttachment','PathAttachment','ClippingAttachment',
    'Attachment','AttachmentType','Sequence','SequenceMode','Animation','AnimationState','AnimationStateData',
    'IkConstraint','TransformConstraint','PathConstraint','Event','EventData','Color','Vector2','Utils','BinaryInput'
  ];
  function classLine(ns) {
    var ok = [], missing = [];
    classes.forEach(function(k){
      var v = ns && ns[k];
      ((typeof v === 'function' || (typeof v === 'object' && v !== null)) ? ok : missing).push(k);
    });
    return {ok: ok, missing: missing};
  }
  function scripts() {
    try {
      return Array.prototype.slice.call(document.scripts).map(function(s){ return s.getAttribute('src') || '[inline]'; }).filter(Boolean);
    } catch(e) { return []; }
  }
  function previewText() {
    try {
      var best = '';
      Array.prototype.slice.call(document.querySelectorAll('div,section,main,article')).forEach(function(el){
        var t = el.innerText || '';
        if ((t.indexOf('No se pudo armar') >= 0 || t.indexOf('DEBUG v0.14') >= 0) && (best === '' || t.length < best.length)) best = t;
      });
      return (best || (document.body && document.body.innerText) || '').replace(/\s+/g, ' ').slice(0, 2500);
    } catch(e) { return ''; }
  }
  function diag() {
    var P = window.PIXI;
    var ns = namespaces();
    var lines = [];
    lines.push('NMM RUNTIME DIAGNOSTIC v0.15.2');
    lines.push('PIXI=' + (!!P) + (P && P.VERSION ? ' version=' + P.VERSION : ''));
    lines.push('href=' + location.href);
    lines.push('userAgent=' + navigator.userAgent);
    lines.push('scripts=' + scripts().join(' | '));
    lines.push('namespaces=' + ns.map(function(x){ return x.label; }).join(', '));
    ns.forEach(function(x){
      var m = classLine(x.obj);
      lines.push('[' + x.label + '] OK=' + m.ok.join(','));
      lines.push('[' + x.label + '] MISSING=' + m.missing.join(','));
    });
    if (window.__nmmDiagErrors && window.__nmmDiagErrors.length) lines.push('ERRORS=' + JSON.stringify(window.__nmmDiagErrors.slice(-10)));
    lines.push('VISIBLE_PREVIEW=' + previewText());
    return lines.join('\n');
  }
  window.__nmmRuntimeDiagnostic = diag;

  function findHost() {
    var candidates = ['#previewContent', '#previewModal', '.preview-content', '.preview-modal', '.modal-content'];
    for (var i=0;i<candidates.length;i++) {
      var el = document.querySelector(candidates[i]);
      if (el) return el;
    }
    var nodes = Array.prototype.slice.call(document.querySelectorAll('div,section,main,article'));
    var found = null;
    nodes.forEach(function(el){
      if (found) return;
      var t = el.innerText || '';
      if (t.indexOf('No se pudo armar') >= 0 || t.indexOf('DEBUG v0.14') >= 0 || t.indexOf('Mostrando textura fallback') >= 0) found = el;
    });
    return found || document.body;
  }
  function inject() {
    try {
      var t = (document.body && document.body.innerText) || '';
      if (t.indexOf('No se pudo armar') < 0 && t.indexOf('DEBUG v0.14') < 0 && t.indexOf('Mostrando textura fallback') < 0) return;
      var host = findHost();
      if (!host) return;
      var wrap = document.getElementById('nmm-runtime-diagnostic-wrap');
      var box;
      if (!wrap) {
        wrap = document.createElement('div');
        wrap.id = 'nmm-runtime-diagnostic-wrap';
        wrap.style.cssText = 'margin:12px;padding:12px;border:1px solid #facc15;border-radius:8px;background:#0b1220;color:#e5e7eb;font:12px/1.35 Consolas,monospace;white-space:pre-wrap;max-height:380px;overflow:auto;';
        var title = document.createElement('div');
        title.textContent = 'DIAGNÓSTICO RUNTIME v0.15.2 — copiar y enviar este bloque completo';
        title.style.cssText = 'font-weight:bold;color:#facc15;margin-bottom:8px;';
        var btn = document.createElement('button');
        btn.textContent = 'Copiar diagnóstico';
        btn.style.cssText = 'margin-bottom:8px;padding:6px 10px;cursor:pointer;';
        box = document.createElement('pre');
        box.id = 'nmm-runtime-diagnostic-box';
        box.style.cssText = 'margin:0;white-space:pre-wrap;';
        btn.onclick = function(){ try { navigator.clipboard.writeText(box.textContent); btn.textContent = 'Copiado'; } catch(e) { alert(box.textContent); } };
        wrap.appendChild(title); wrap.appendChild(btn); wrap.appendChild(box);
        host.appendChild(wrap);
      }
      box = document.getElementById('nmm-runtime-diagnostic-box');
      if (box) box.textContent = diag();
    } catch(e) {}
  }
  setInterval(inject, 1000);
  setTimeout(inject, 1200);
  setTimeout(inject, 3000);
})();
// --- end NMM v0.14.7 --------------------------------------------------------




// --- NMM v0.14.8 Visible Diagnostic Top Button -----------------------------
(function () {
  if (window.__NMM_V0148_DIAG_TOP__) return;
  window.__NMM_V0148_DIAG_TOP__ = true;

  function diagText() {
    try {
      if (typeof window.__nmmRuntimeDiagnostic === 'function') {
        return window.__nmmRuntimeDiagnostic();
      }
    } catch (e) {}
    try {
      return 'NMM RUNTIME DIAGNOSTIC v0.15.2\n' + ((document.body && document.body.innerText) || '').slice(0, 8000);
    } catch (e) {
      return 'NMM RUNTIME DIAGNOSTIC v0.15.2\nNo pude leer diagnóstico: ' + String(e);
    }
  }

  function copy(txt, btn) {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(txt).then(function () {
          if (btn) btn.textContent = 'Diagnóstico copiado';
        }).catch(function () {
          window.prompt('Copia este diagnóstico completo:', txt);
        });
      } else {
        window.prompt('Copia este diagnóstico completo:', txt);
      }
    } catch (e) {
      window.prompt('Copia este diagnóstico completo:', txt);
    }
  }

  function ensureTopButton() {
    try {
      var btn = document.getElementById('nmm-diag-top-copy-button');
      if (!btn) {
        btn = document.createElement('button');
        btn.id = 'nmm-diag-top-copy-button';
        btn.textContent = 'Copiar diagnóstico';
        btn.style.cssText = [
          'position:fixed',
          'top:70px',
          'right:82px',
          'z-index:2147483647',
          'padding:10px 14px',
          'border-radius:10px',
          'border:2px solid #facc15',
          'background:#facc15',
          'color:#111827',
          'font-weight:900',
          'font-family:Segoe UI,Arial,sans-serif',
          'font-size:13px',
          'cursor:pointer',
          'box-shadow:0 6px 24px rgba(0,0,0,.45)'
        ].join(';');
        btn.onclick = function () { copy(diagText(), btn); };
        document.body.appendChild(btn);
      }

      var host = document.querySelector('#previewContent') ||
                 document.querySelector('.preview-content') ||
                 document.querySelector('#previewModal .modal-content') ||
                 document.querySelector('.modal-content');
      if (host && !document.getElementById('nmm-diag-top-panel')) {
        var panel = document.createElement('div');
        panel.id = 'nmm-diag-top-panel';
        panel.style.cssText = 'margin:10px 12px;padding:10px;border:2px solid #facc15;border-radius:10px;background:#0f172a;color:#e5e7eb;font:12px/1.35 Consolas,monospace;white-space:pre-wrap;max-height:240px;overflow:auto;position:relative;z-index:999999;';

        var title = document.createElement('div');
        title.textContent = 'DIAGNÓSTICO RUNTIME v0.15.2 — botón visible arriba a la derecha';
        title.style.cssText = 'font-weight:800;color:#facc15;margin-bottom:8px;font-family:Segoe UI,Arial,sans-serif;';

        var localBtn = document.createElement('button');
        localBtn.textContent = 'Copiar diagnóstico';
        localBtn.style.cssText = 'padding:7px 12px;margin:0 8px 8px 0;cursor:pointer;border-radius:7px;border:1px solid #94a3b8;background:#e5e7eb;color:#111827;font-weight:800;';
        localBtn.onclick = function () { copy(diagText(), localBtn); };

        var promptBtn = document.createElement('button');
        promptBtn.textContent = 'Abrir cuadro para copiar';
        promptBtn.style.cssText = 'padding:7px 12px;margin:0 0 8px 0;cursor:pointer;border-radius:7px;border:1px solid #94a3b8;background:#e5e7eb;color:#111827;font-weight:800;';
        promptBtn.onclick = function () { window.prompt('Copia este diagnóstico completo:', diagText()); };

        var pre = document.createElement('pre');
        pre.id = 'nmm-diag-top-text';
        pre.style.cssText = 'margin:0;white-space:pre-wrap;max-height:160px;overflow:auto;';
        pre.textContent = diagText();

        panel.appendChild(title);
        panel.appendChild(localBtn);
        panel.appendChild(promptBtn);
        panel.appendChild(pre);
        host.insertBefore(panel, host.firstChild);
      }

      var pre2 = document.getElementById('nmm-diag-top-text');
      if (pre2) pre2.textContent = diagText();
    } catch (e) {}
  }

  setInterval(ensureTopButton, 700);
  setTimeout(ensureTopButton, 100);
  setTimeout(ensureTopButton, 800);
  setTimeout(ensureTopButton, 1800);
})();
// --- end NMM v0.14.8 -------------------------------------------------------



// --- NMM v0.14.9 Runtime Attachment Compatibility Polyfill -----------------
(function () {
  if (window.__NMM_V0149_RUNTIME_COMPAT__) return;
  window.__NMM_V0149_RUNTIME_COMPAT__ = true;

  function makeColor(ns) {
    if (ns && typeof ns.Color === 'function') return new ns.Color(1, 1, 1, 1);
    return { r: 1, g: 1, b: 1, a: 1, setFromColor: function(c){ if(c){this.r=c.r;this.g=c.g;this.b=c.b;this.a=c.a;} } };
  }

  function nameOf(name, path, fallback) {
    var n = name;
    if (n == null || n === '') n = path;
    if (n == null || n === '') n = fallback || 'attachment';
    return String(n);
  }

  function sequenceVariants(name) {
    var s = String(name == null ? '' : name);
    var out = [];
    function add(v) { if (v && v !== s && out.indexOf(v) < 0) out.push(v); }
    add(s.replace(/\d+$/, ''));
    add(s.replace(/[_-]?\d+$/, ''));
    add(s.replace(/t\d+$/, 't'));
    add(s.replace(/([a-z_]+)[0-9]+$/i, '$1'));
    return out;
  }

  function installOn(ns, label) {
    if (!ns || ns.__nmm_v0149_done) return false;

    if (!ns.AttachmentType) {
      ns.AttachmentType = { Region: 0, BoundingBox: 1, Mesh: 2, LinkedMesh: 3, Path: 4, Point: 5, Clipping: 6 };
    }

    if (!ns.Attachment) {
      ns.Attachment = function Attachment(name) { this.name = nameOf(name, null, 'attachment'); };
    }

    function Attachment(name) { this.name = nameOf(name, null, 'attachment'); }

    function VertexAttachment(name) {
      Attachment.call(this, name);
      this.id = (window.__nmm_v0149_va_id = (window.__nmm_v0149_va_id || 0) + 1);
      this.bones = null;
      this.vertices = [];
      this.worldVerticesLength = 0;
      this.timelineAttachment = this;
    }
    VertexAttachment.prototype.computeWorldVertices = function(slot, start, count, worldVertices, offset, stride) {
      worldVertices = worldVertices || [];
      stride = stride || 2;
      offset = offset || 0;
      for (var i = 0; i < count; i += 2) {
        worldVertices[offset] = 0;
        worldVertices[offset + 1] = 0;
        offset += stride;
      }
      return worldVertices;
    };
    if (!ns.VertexAttachment) ns.VertexAttachment = VertexAttachment;

    if (!ns.PointAttachment) {
      ns.PointAttachment = function PointAttachment(name) {
        Attachment.call(this, name);
        this.type = ns.AttachmentType.Point;
        this.x = 0; this.y = 0; this.rotation = 0; this.color = makeColor(ns);
      };
      ns.PointAttachment.prototype.computeWorldPosition = function(bone, point) {
        point = point || { x: 0, y: 0 };
        var x = this.x || 0, y = this.y || 0;
        if (bone && typeof bone.localToWorld === 'function') return bone.localToWorld({x:x,y:y});
        if (bone) {
          point.x = x * (bone.a || 1) + y * (bone.b || 0) + (bone.worldX || bone.x || 0);
          point.y = x * (bone.c || 0) + y * (bone.d || 1) + (bone.worldY || bone.y || 0);
        } else { point.x = x; point.y = y; }
        return point;
      };
      ns.PointAttachment.prototype.computeWorldRotation = function(bone) { return this.rotation || 0; };
    }

    if (!ns.BoundingBoxAttachment) {
      ns.BoundingBoxAttachment = function BoundingBoxAttachment(name) {
        VertexAttachment.call(this, name);
        this.type = ns.AttachmentType.BoundingBox;
        this.color = makeColor(ns);
      };
      ns.BoundingBoxAttachment.prototype = Object.create(VertexAttachment.prototype);
      ns.BoundingBoxAttachment.prototype.constructor = ns.BoundingBoxAttachment;
    }

    if (!ns.PathAttachment) {
      ns.PathAttachment = function PathAttachment(name) {
        VertexAttachment.call(this, name);
        this.type = ns.AttachmentType.Path;
        this.lengths = [];
        this.closed = false;
        this.constantSpeed = false;
        this.color = makeColor(ns);
      };
      ns.PathAttachment.prototype = Object.create(VertexAttachment.prototype);
      ns.PathAttachment.prototype.constructor = ns.PathAttachment;
    }

    if (!ns.ClippingAttachment) {
      ns.ClippingAttachment = function ClippingAttachment(name) {
        VertexAttachment.call(this, name);
        this.type = ns.AttachmentType.Clipping;
        this.endSlot = null;
        this.color = makeColor(ns);
      };
      ns.ClippingAttachment.prototype = Object.create(VertexAttachment.prototype);
      ns.ClippingAttachment.prototype.constructor = ns.ClippingAttachment;
    }

    if (!ns.RegionAttachment) {
      ns.RegionAttachment = function RegionAttachment(name) {
        Attachment.call(this, name);
        this.type = ns.AttachmentType.Region;
        this.path = this.name;
        this.x = 0; this.y = 0; this.scaleX = 1; this.scaleY = 1; this.rotation = 0;
        this.width = 0; this.height = 0; this.color = makeColor(ns);
        this.region = null; this.offset = [0,0,0,0,0,0,0,0]; this.uvs = [0,0,1,0,1,1,0,1];
      };
      ns.RegionAttachment.prototype.updateOffset = function() {};
      ns.RegionAttachment.prototype.setRegion = function(region) { this.region = region; };
      ns.RegionAttachment.prototype.computeWorldVertices = function(bone, worldVertices, offset, stride) {
        worldVertices = worldVertices || [];
        stride = stride || 2;
        offset = offset || 0;
        for (var i = 0; i < 4; i++) { worldVertices[offset] = 0; worldVertices[offset + 1] = 0; offset += stride; }
        return worldVertices;
      };
    }

    if (!ns.SequenceMode) ns.SequenceMode = { hold: 0, once: 1, loop: 2, pingpong: 3, onceReverse: 4, loopReverse: 5, pingpongReverse: 6 };
    if (!ns.Sequence) {
      ns.Sequence = function Sequence(count) { this.id = 0; this.regions = new Array(count || 0); this.start = 0; this.digits = 0; this.setupIndex = 0; };
      ns.Sequence.prototype.apply = function(slot, attachment) { return attachment; };
      ns.Sequence.prototype.getPath = function(basePath, index) { return String(basePath || '') + String(index || ''); };
    }

    if (!ns.AtlasAttachmentLoader) {
      ns.AtlasAttachmentLoader = function AtlasAttachmentLoader(atlas) { this.atlas = atlas; };
      ns.AtlasAttachmentLoader.prototype._find = function(path) {
        if (!this.atlas || typeof this.atlas.findRegion !== 'function') return null;
        var r = this.atlas.findRegion(path);
        if (r) return r;
        var vs = sequenceVariants(path);
        for (var i=0;i<vs.length;i++) { r = this.atlas.findRegion(vs[i]); if (r) return r; }
        return null;
      };
      ns.AtlasAttachmentLoader.prototype.newRegionAttachment = function(skin, name, path) {
        var n = nameOf(name, path, 'region');
        var p = nameOf(path, name, n);
        var a = new ns.RegionAttachment(n);
        a.path = p;
        a.region = this._find(p) || this._find(n);
        return a;
      };
      ns.AtlasAttachmentLoader.prototype.newMeshAttachment = function(skin, name, path) {
        var n = nameOf(name, path, 'mesh');
        var p = nameOf(path, name, n);
        var C = ns.MeshAttachment || ns.RegionAttachment;
        var a = new C(n);
        a.path = p;
        a.region = this._find(p) || this._find(n);
        return a;
      };
      try { window.__nmmV0150PatchRuntime && window.__nmmV0150PatchRuntime(); } catch(e) {}
      ns.AtlasAttachmentLoader.prototype.newBoundingBoxAttachment = function(skin, name) { return new ns.BoundingBoxAttachment(nameOf(name, null, 'bbox')); };
      try { window.__nmmV0150PatchRuntime && window.__nmmV0150PatchRuntime(); } catch(e) {}
      ns.AtlasAttachmentLoader.prototype.newPathAttachment = function(skin, name) { return new ns.PathAttachment(nameOf(name, null, 'path')); };
      try { window.__nmmV0150PatchRuntime && window.__nmmV0150PatchRuntime(); } catch(e) {}
      ns.AtlasAttachmentLoader.prototype.newPointAttachment = function(skin, name) { return new ns.PointAttachment(nameOf(name, null, 'point')); };
      try { window.__nmmV0150PatchRuntime && window.__nmmV0150PatchRuntime(); } catch(e) {}
      ns.AtlasAttachmentLoader.prototype.newClippingAttachment = function(skin, name) { return new ns.ClippingAttachment(nameOf(name, null, 'clip')); };
    }

    // Alias names used by different pixi-spine builds.
    if (!ns.AttachmentType.Point && ns.AttachmentType.point != null) ns.AttachmentType.Point = ns.AttachmentType.point;
    ns.__nmm_v0149_done = true;
    return true;
  }

  function patchAtlas(ns) {
    if (!ns || !ns.TextureAtlas || !ns.TextureAtlas.prototype) return false;
    var p = ns.TextureAtlas.prototype;
    if (p.__nmm_v0149_findRegion) return true;
    var original = p.findRegion;
    if (typeof original !== 'function') return false;
    p.findRegion = function(name) {
      var r = original.call(this, name);
      if (r) return r;
      var vs = sequenceVariants(name);
      for (var i=0;i<vs.length;i++) { try { r = original.call(this, vs[i]); if (r) return r; } catch(e){} }
      return null;
    };
    p.__nmm_v0149_findRegion = true;
    return true;
  }

  function namespaces() {
    var out = [];
    function add(x) { if (x && out.indexOf(x) < 0) out.push(x); }
    add(window.pixi_spine);
    add(window.pixi_spine && window.pixi_spine.core);
    add(window.PIXI && window.PIXI.spine);
    add(window.PIXI && window.PIXI.spine && window.PIXI.spine.core);
    add(window.spine);
    add(window.spine && window.spine.core);
    add(window.spine38);
    add(window.spine41);
    return out;
  }

  window.__nmmInstallRuntimeCompat = function() {
    var ok = false;
    var ns = namespaces();
    for (var i=0;i<ns.length;i++) {
      try { ok = installOn(ns[i], 'ns'+i) || ok; } catch(e) { console.warn('NMM v0.14.9 installOn failed', e); }
      try { ok = patchAtlas(ns[i]) || ok; } catch(e) { console.warn('NMM v0.14.9 patchAtlas failed', e); }
    }
    try { window.__nmmPatchSpineAtlasSequences && window.__nmmPatchSpineAtlasSequences(); } catch(e) {}
    return ok;
  };

  var tries = 0;
  var timer = setInterval(function(){
    tries++;
    if (window.__nmmInstallRuntimeCompat() || tries > 600) clearInterval(timer);
  }, 20);
  setTimeout(window.__nmmInstallRuntimeCompat, 10);
  setTimeout(window.__nmmInstallRuntimeCompat, 200);
  setTimeout(window.__nmmInstallRuntimeCompat, 800);
})();
// --- end NMM v0.14.9 -------------------------------------------------------



// --- NMM v0.15.2 Attachment Safe Constructor Patch -------------------------
(function () {
  if (window.__NMM_V0150_ATTACHMENT_SAFE__) return;
  window.__NMM_V0150_ATTACHMENT_SAFE__ = true;

  function safeName(name, path, fallback) {
    var n = name;
    if (n == null || n === '') n = path;
    if (n == null || n === '') n = fallback || 'attachment';
    return String(n);
  }

  function seqVariants(name) {
    var s = String(name == null ? '' : name);
    var out = [];
    function add(v) { if (v && v !== s && out.indexOf(v) < 0) out.push(v); }
    add(s.replace(/\d+$/, ''));
    add(s.replace(/[_-]?\d+$/, ''));
    add(s.replace(/t\d+$/, 't'));
    add(s.replace(/([a-z_]+)[0-9]+$/i, '$1'));
    return out;
  }

  function copyStatics(dst, src) {
    try {
      Object.getOwnPropertyNames(src).forEach(function(k) {
        if (k === 'length' || k === 'name' || k === 'prototype') return;
        try { Object.defineProperty(dst, k, Object.getOwnPropertyDescriptor(src, k)); } catch(e) {}
      });
    } catch(e) {}
  }

  function makeFallbackAttachment(ns, key, name) {
    var obj = { name: safeName(name, null, key || 'attachment'), type: key || 'Attachment' };
    obj.path = obj.name;
    obj.color = ns && typeof ns.Color === 'function' ? new ns.Color(1,1,1,1) : {r:1,g:1,b:1,a:1};
    obj.region = null;
    obj.bones = null;
    obj.vertices = [];
    obj.worldVerticesLength = 0;
    obj.timelineAttachment = obj;
    obj.lengths = [];
    obj.closed = false;
    obj.constantSpeed = false;
    obj.endSlot = null;
    obj.updateOffset = function(){};
    obj.setRegion = function(region){ this.region = region; };
    obj.computeWorldVertices = function(slot, start, count, out, offset, stride){
      out = out || []; offset = offset || 0; stride = stride || 2; count = count || 8;
      for (var i=0; i<count; i+=2) { out[offset] = 0; out[offset+1] = 0; offset += stride; }
      return out;
    };
    obj.computeWorldPosition = function(bone, point){ point = point || {x:0,y:0}; point.x = this.x || 0; point.y = this.y || 0; return point; };
    obj.computeWorldRotation = function(){ return this.rotation || 0; };
    return obj;
  }

  function wrapCtor(ns, key) {
    if (!ns || typeof ns[key] !== 'function') return false;
    var Orig = ns[key];
    if (Orig.__nmm_v0150_wrapped) return true;

    function WrappedAttachment(name) {
      var args = Array.prototype.slice.call(arguments);
      args[0] = safeName(args[0], args[1], key);
      try {
        return Reflect.construct(Orig, args, WrappedAttachment);
      } catch (err) {
        var msg = String((err && err.message) || err || '');
        if (/Attachment name must not be null|name must not be null|Cannot read properties of null/i.test(msg)) {
          try {
            return Reflect.construct(Orig, [safeName(args[0], args[1], key)], WrappedAttachment);
          } catch(e2) {
            return makeFallbackAttachment(ns, key, args[0]);
          }
        }
        throw err;
      }
    }
    try { Object.setPrototypeOf(WrappedAttachment, Orig); } catch(e) {}
    try { WrappedAttachment.prototype = Orig.prototype; } catch(e) {}
    try { WrappedAttachment.prototype.constructor = WrappedAttachment; } catch(e) {}
    copyStatics(WrappedAttachment, Orig);
    WrappedAttachment.__nmm_v0150_wrapped = true;
    WrappedAttachment.__nmm_v0150_original = Orig;
    ns[key] = WrappedAttachment;
    return true;
  }

  function ensureFallbackClasses(ns) {
    if (!ns) return false;
    if (!ns.AttachmentType) ns.AttachmentType = { Region:0, BoundingBox:1, Mesh:2, LinkedMesh:3, Path:4, Point:5, Clipping:6 };
    if (!ns.Color) ns.Color = function(r,g,b,a){ this.r=r==null?1:r; this.g=g==null?1:g; this.b=b==null?1:b; this.a=a==null?1:a; };

    function simple(key) {
      if (!ns[key]) ns[key] = function(name){ return makeFallbackAttachment(ns, key, safeName(name, null, key)); };
    }
    ['Attachment','RegionAttachment','MeshAttachment','PointAttachment','BoundingBoxAttachment','PathAttachment','ClippingAttachment'].forEach(simple);

    if (!ns.SequenceMode) ns.SequenceMode = { hold:0, once:1, loop:2, pingpong:3, onceReverse:4, loopReverse:5, pingpongReverse:6 };
    if (!ns.Sequence) ns.Sequence = function(count){ this.id=0; this.regions=new Array(count||0); this.start=0; this.digits=0; this.setupIndex=0; };
    if (ns.Sequence && ns.Sequence.prototype && !ns.Sequence.prototype.getPath) {
      ns.Sequence.prototype.getPath = function(basePath, index){ return String(basePath || '') + String(index || ''); };
    }
    return true;
  }

  function patchAtlas(ns) {
    if (!ns || !ns.TextureAtlas || !ns.TextureAtlas.prototype) return false;
    var p = ns.TextureAtlas.prototype;
    if (p.__nmm_v0150_findRegion) return true;
    var orig = p.findRegion;
    if (typeof orig !== 'function') return false;
    p.findRegion = function(name) {
      var r = orig.call(this, name);
      if (r) return r;
      var vars = seqVariants(name);
      for (var i=0; i<vars.length; i++) { try { r = orig.call(this, vars[i]); if (r) return r; } catch(e) {} }
      return null;
    };
    p.__nmm_v0150_findRegion = true;
    return true;
  }

  function patchLoader(ns) {
    if (!ns) return false;
    if (!ns.AtlasAttachmentLoader) {
      ns.AtlasAttachmentLoader = function(atlas){ this.atlas = atlas; };
    }
    var p = ns.AtlasAttachmentLoader.prototype;
    if (!p || p.__nmm_v0150_loader) return true;

    function find(atlas, name) {
      if (!atlas || typeof atlas.findRegion !== 'function') return null;
      var r = atlas.findRegion(name);
      if (r) return r;
      var vars = seqVariants(name);
      for (var i=0; i<vars.length; i++) { try { r = atlas.findRegion(vars[i]); if (r) return r; } catch(e) {} }
      return null;
    }

    p.newRegionAttachment = function(skin, name, path) {
      var n = safeName(name, path, 'region');
      var pp = safeName(path, name, n);
      var a = new ns.RegionAttachment(n);
      a.path = pp;
      a.region = find(this.atlas, pp) || find(this.atlas, n);
      if (typeof a.setRegion === 'function' && a.region) { try { a.setRegion(a.region); } catch(e) {} }
      return a;
    };
    p.newMeshAttachment = function(skin, name, path) {
      var n = safeName(name, path, 'mesh');
      var pp = safeName(path, name, n);
      var a = new ns.MeshAttachment(n);
      a.path = pp;
      a.region = find(this.atlas, pp) || find(this.atlas, n);
      if (typeof a.setRegion === 'function' && a.region) { try { a.setRegion(a.region); } catch(e) {} }
      return a;
    };
    p.newBoundingBoxAttachment = function(skin, name) { return new ns.BoundingBoxAttachment(safeName(name, null, 'bbox')); };
    p.newPathAttachment = function(skin, name) { return new ns.PathAttachment(safeName(name, null, 'path')); };
    p.newPointAttachment = function(skin, name) { return new ns.PointAttachment(safeName(name, null, 'point')); };
    p.newClippingAttachment = function(skin, name) { return new ns.ClippingAttachment(safeName(name, null, 'clip')); };
    p.__nmm_v0150_loader = true;
    return true;
  }

  function namespaces() {
    var out = [];
    function add(x) { if (x && out.indexOf(x) < 0) out.push(x); }
    add(window.pixi_spine);
    add(window.pixi_spine && window.pixi_spine.core);
    add(window.PIXI && window.PIXI.spine);
    add(window.PIXI && window.PIXI.spine && window.PIXI.spine.core);
    add(window.spine);
    add(window.spine && window.spine.core);
    add(window.spine38);
    add(window.spine41);
    return out;
  }

  window.__nmmV0150PatchRuntime = function(){
    var ok = false;
    var ns = namespaces();
    for (var i=0; i<ns.length; i++) {
      var n = ns[i];
      try { ok = ensureFallbackClasses(n) || ok; } catch(e) {}
      try { ['Attachment','RegionAttachment','MeshAttachment','PointAttachment','BoundingBoxAttachment','PathAttachment','ClippingAttachment'].forEach(function(k){ ok = wrapCtor(n,k) || ok; }); } catch(e) {}
      try { ok = patchAtlas(n) || ok; } catch(e) {}
      try { ok = patchLoader(n) || ok; } catch(e) {}
    }
    try { window.__nmmInstallRuntimeCompat && window.__nmmInstallRuntimeCompat(); } catch(e) {}
    try { window.__nmmPatchSpineAtlasSequences && window.__nmmPatchSpineAtlasSequences(); } catch(e) {}
    return ok;
  };

  // Captura stack para el próximo fallo.
  window.__nmmLastRuntimeErrorStack = '';
  window.addEventListener('error', function(e){ try { window.__nmmLastRuntimeErrorStack = (e.error && e.error.stack) || e.message || ''; } catch(x) {} });
  window.addEventListener('unhandledrejection', function(e){ try { window.__nmmLastRuntimeErrorStack = (e.reason && e.reason.stack) || String(e.reason || ''); } catch(x) {} });

  var tries = 0;
  var timer = setInterval(function(){ tries++; if (window.__nmmV0150PatchRuntime() || tries > 800) clearInterval(timer); }, 10);
  setTimeout(window.__nmmV0150PatchRuntime, 1);
  setTimeout(window.__nmmV0150PatchRuntime, 50);
  setTimeout(window.__nmmV0150PatchRuntime, 200);
  setTimeout(window.__nmmV0150PatchRuntime, 600);
})();
// --- end NMM v0.15.2 -------------------------------------------------------


(function(){try{var old=window.__nmmRuntimeDiagnostic;if(typeof old==='function'){window.__nmmRuntimeDiagnostic=function(){var t=old();try{t+='\nLAST_RUNTIME_STACK='+(window.__nmmLastRuntimeErrorStack||'');}catch(e){}return t;};}}catch(e){}})();

// NMM v0.15.2 marker: vendor attachment constructor throw patched
window.__NMM_VENDOR_ATTACHMENT_THROW_PATCH__ = true;


// --- NMM v0.15.2 RegionFallback patch ------------------------------
(function(){
  if (window.__NMM_V0152_REGIONFALLBACK__) return;
  window.__NMM_V0152_REGIONFALLBACK__ = true;
  window.__NMM_REGION_FALLBACK_LOG = [];
  function log(x){ try{ window.__NMM_REGION_FALLBACK_LOG.push(String(x)); if(window.__NMM_REGION_FALLBACK_LOG.length>80) window.__NMM_REGION_FALLBACK_LOG.shift(); }catch(e){} }
  function s(v){ if(v===null||v===undefined) return ''; v=String(v); if(v==='undefined'||v==='null'||v==='[object Object]') return ''; return v.trim(); }
  function trim(v){ v=s(v); return v.replace(/0{8,}\d{1,4}$/,'').replace(/\d{16,}$/,'').replace(/_?\d{8,}$/,''); }
  function listNames(){ var out=[]; for(var i=0;i<arguments.length;i++){ var x=s(arguments[i]); if(!x) continue; out.push(x); var t=trim(x); if(t&&t!==x) out.push(t); if(x.indexOf('/')>=0) out.push(x.split('/').pop()); if(x.indexOf('.')>=0) out.push(x.replace(/\.[^.]+$/,'')); } ['body_t','body','head_t','face_t','hair_t','weapon_t','effect_t'].forEach(function(x){out.push(x)}); var seen={}, u=[]; out.forEach(function(x){x=s(x); if(x&&!seen[x]){seen[x]=1;u.push(x)}}); return u; }
  function regions(atlas){ var a=[]; try{ if(atlas&&Array.isArray(atlas.regions)) a=a.concat(atlas.regions); if(atlas) Object.keys(atlas).forEach(function(k){var v=atlas[k]; if(Array.isArray(v)) v.forEach(function(r){ if(r&&(r.name||r.texture||r.page)) a.push(r); });}); }catch(e){} var seen=[], o=[]; a.forEach(function(r){if(r&&seen.indexOf(r)<0){seen.push(r);o.push(r)}}); return o; }
  function first(atlas){ var a=regions(atlas); for(var i=0;i<a.length;i++) if(a[i]&&a[i].name) return a[i]; return a[0]||null; }
  function loose(atlas){ var wanted=listNames.apply(null, Array.prototype.slice.call(arguments,1)); var rs=regions(atlas); for(var c=0;c<wanted.length;c++){ var w=wanted[c].toLowerCase(); for(var i=0;i<rs.length;i++){ var n=s(rs[i]&&rs[i].name); if(!n) continue; if(n.toLowerCase()===w || trim(n).toLowerCase()===trim(w).toLowerCase()) return rs[i]; } } return null; }
  function safeName(name,path,seq,region){ return s(name)||s(path)||s(seq&&(seq.name||seq.basePath||seq.path||seq.prefix))||s(region&&region.name)||'__nmm_attachment_auto'; }
  function getAtlas(loader){ return loader && (loader.atlas||loader.textureAtlas||loader._atlas||loader._textureAtlas); }
  function pickRegion(atlas,name,path,seq){ var r=loose(atlas,path,name,seq&&(seq.name||seq.basePath||seq.path||seq.prefix))||first(atlas); log('pickRegion name='+s(name)+' path='+s(path)+' => '+s(r&&r.name)); return r; }
  function patchNS(ns){
    if(!ns) return;
    ['Attachment','RegionAttachment','MeshAttachment','PointAttachment','BoundingBoxAttachment','PathAttachment','ClippingAttachment'].forEach(function(k){ var C=ns[k]; if(!C||C.__nmm152) return; try{ var W=function(name){ return new (Function.prototype.bind.call(C,null,s(name)||'__nmm_attachment_auto'))(); }; W.prototype=C.prototype; Object.keys(C).forEach(function(p){try{W[p]=C[p]}catch(e){}}); W.__nmm152=true; ns[k]=W; }catch(e){} });
    if(ns.TextureAtlas&&ns.TextureAtlas.prototype&&!ns.TextureAtlas.prototype.__nmm152){ var old=ns.TextureAtlas.prototype.findRegion; ns.TextureAtlas.prototype.findRegion=function(name){ var c=listNames(name); for(var i=0;i<c.length;i++){ try{ var r=old&&old.call(this,c[i]); if(r) return r; }catch(e){} var rr=loose(this,c[i]); if(rr) return rr; } var f=first(this); if(f) { log('findRegion fallback '+s(name)+' => '+s(f.name)); return f; } return null; }; ns.TextureAtlas.prototype.__nmm152=true; }
    if(ns.AtlasAttachmentLoader&&ns.AtlasAttachmentLoader.prototype&&!ns.AtlasAttachmentLoader.prototype.__nmm152){ var L=ns.AtlasAttachmentLoader.prototype; L.newRegionAttachment=function(skin,name,path,sequence){ var atlas=getAtlas(this), r=pickRegion(atlas,name,path,sequence), nm=safeName(name,path,sequence,r), p=s(path)||s(name)||s(r&&r.name)||'body_t'; var a=ns.RegionAttachment?new ns.RegionAttachment(nm):{name:nm}; a.name=a.name||nm; a.path=p; a.region=r; if(sequence) a.sequence=sequence; if(a.setRegion&&r) try{a.setRegion(r)}catch(e){} return a; }; L.newMeshAttachment=function(skin,name,path,sequence){ var atlas=getAtlas(this), r=pickRegion(atlas,name,path,sequence), nm=safeName(name,path,sequence,r), p=s(path)||s(name)||s(r&&r.name)||'body_t'; var a=ns.MeshAttachment?new ns.MeshAttachment(nm):{name:nm}; a.name=a.name||nm; a.path=p; a.region=r; if(sequence) a.sequence=sequence; if(a.setRegion&&r) try{a.setRegion(r)}catch(e){} return a; }; [['newBoundingBoxAttachment','BoundingBoxAttachment'],['newPathAttachment','PathAttachment'],['newPointAttachment','PointAttachment'],['newClippingAttachment','ClippingAttachment']].forEach(function(x){L[x[0]]=function(skin,name){var nm=safeName(name,x[1]); var C=ns[x[1]]; var a=C?new C(nm):{name:nm}; a.name=a.name||nm; return a;};}); L.__nmm152=true; }
  }
  function run(){ try{ [window.pixi_spine,window.spine,window.spine38,window.spine41,window.PIXI&&window.PIXI.spine].filter(Boolean).forEach(patchNS); }catch(e){ window.__NMM_LAST_RUNTIME_STACK=(e&&e.stack)||String(e); } }
  run(); var n=0, t=setInterval(function(){run(); if(++n>300) clearInterval(t);},50);
  var oldDiag=window.__nmmRuntimeDiagnostic; window.__nmmRuntimeDiagnostic=function(){ var out=oldDiag?oldDiag():'NMM RUNTIME DIAGNOSTIC v0.15.2'; out=String(out).replace(/v0\.15\.1/g,'v0.15.2'); try{out+='\nREGION_FALLBACK_LOG='+window.__NMM_REGION_FALLBACK_LOG.join(' || ')}catch(e){} return out; };
})();
// --- end NMM v0.15.2 ----------------------------------------------


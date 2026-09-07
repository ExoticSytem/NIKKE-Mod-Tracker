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
    brand_sub:'BIBLIOTECA DE MODS', nav_label:'NAVEGACIÓN', nav_characters:'Personajes', nav_mods:'Mods', nav_conflicts:'Conflictos', settings_label:'AJUSTES', nav_settings:'Configuración',
    scanned_folder:'CARPETA ESCANEADA', scan_now:'Escanear ahora', refresh:'Actualizar', ready:'Listo', scanning:'Escaneando...', loading:'Cargando...', selecting:'Seleccionando...', deleting:'Eliminando...', loading_image:'Cargando imagen...', updating_catalog:'Buscando nuevos personajes...',
    page_characters:'Personajes', page_characters_sub:'Cada ID + Ver se trata como una skin/personaje independiente', page_mods:'Mods', page_mods_sub:'Archivos detectados en tu carpeta, sin activar ni desactivar nada', page_conflicts:'Conflictos', page_conflicts_sub:'Destinos duplicados por ID + Ver + acción', page_settings:'Configuración', page_settings_sub:'Carpetas, catálogo, idioma e imágenes',
    search_character:'Buscar personaje, ID o versión...', sort_id_asc:'ID: menor a mayor', sort_id_desc:'ID: mayor a menor', sort_name_asc:'Nombre: A-Z', sort_name_desc:'Nombre: Z-A', sort_mods_desc:'Más mods primero', sort_conflicts_first:'Conflictos primero',
    filter_all:'Todos', filter_with_mods:'Con mods', filter_without_mods:'Sin mods', filter_conflicts:'Conflictos', type_all:'Todos', type_npc_extra:'Solo NPC / Extra', type_non_npc:'Ocultar NPC / Extra', tag_filter_all:'Todas las etiquetas', tag_filter_untagged:'Sin etiquetas', variants:'personajes / variantes', no_results:'No hay resultados', no_results_hint:'Prueba otro filtro o selecciona la carpeta donde guardas tus mods.',
    search_mod:'Buscar mod, personaje o autor...', all_actions:'Todas las acciones', only_conflicts:'Solo conflictos', action_aim:'Aim', action_cover:'Cover', action_standing:'Standing',
    send_selected_trash:'Enviar seleccionados a Papelera', send_n_trash:'Enviar {n} a Papelera', col_mod:'Mod', col_character:'Personaje', col_target:'ID / Ver', col_action:'Acción', col_status:'Estado',
    author_detected:'Autor detectado', not_in_catalog:'No está en catálogo', conflict:'Conflicto', show_in_explorer:'Mostrar en Explorador', preview_mod:'Vista previa experimental', preview_loading:'Extrayendo textura real del mod...', preview_title:'Preview Alpha', preview_raw_note:'Esta primera versión muestra la textura real extraída del bundle. Todavía no reconstruye la animación Spine.', preview_failed:'No se pudo generar la vista previa: {error}', preview_source:'Archivo del bundle', preview_texture:'Textura', preview_detected:'Detectado', preview_cached:'Caché', send_to_trash:'Enviar a Papelera', no_mods_filter:'No hay mods para este filtro',
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
    author_detected:'Detected author', not_in_catalog:'Not in catalog', conflict:'Conflict', show_in_explorer:'Show in Explorer', preview_mod:'Experimental preview', preview_loading:'Extracting the real mod texture...', preview_title:'Preview Alpha', preview_raw_note:'This first version displays the real texture extracted from the bundle. It does not reconstruct the Spine animation yet.', preview_failed:'Could not generate preview: {error}', preview_source:'Bundle file', preview_texture:'Texture', preview_detected:'Detected', preview_cached:'Cache', send_to_trash:'Send to Recycle Bin', no_mods_filter:'No mods match this filter',
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

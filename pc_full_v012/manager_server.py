from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List

PORT = 8136
MOD_RE = re.compile(r"^c(?P<id>\d{3,4})_(?P<ver>\d{2})_(?P<action>standing|aim|cover)(?:_(?P<rest>.*))?$", re.I)
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
CONFIG_FILE = DATA / "config.json"
META_FILE = DATA / "metadata.json"
LOCAL_CATALOG = ROOT / "catalog" / "base_catalog.json"
REMOTE_CATALOG = "https://raw.githubusercontent.com/ExoticSytem/NIKKE-Mod-Tracker/main/catalog/base_catalog.json"
IMAGE_BASE = "https://raw.githubusercontent.com/ExoticSytem/NIKKE-Mod-Tracker/main/assets/characters/library"


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def config() -> Dict[str, Any]:
    c = read_json(CONFIG_FILE, {})
    if not isinstance(c, dict):
        c = {}
    c.setdefault("language", "es")
    c.setdefault("modsPath", "")
    return c


def metadata() -> Dict[str, Any]:
    m = read_json(META_FILE, {})
    if not isinstance(m, dict):
        m = {}
    m.setdefault("characters", {})
    return m


def load_catalog(online: bool = False) -> Dict[str, Any]:
    if online:
        try:
            req = urllib.request.Request(REMOTE_CATALOG, headers={"User-Agent": "NIKKE-Mod-Manager/0.12"})
            with urllib.request.urlopen(req, timeout=8) as r:
                raw = r.read().decode("utf-8")
            obj = json.loads(raw)
            if isinstance(obj, dict) and obj.get("characters"):
                try:
                    LOCAL_CATALOG.parent.mkdir(parents=True, exist_ok=True)
                    LOCAL_CATALOG.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass
                return obj
        except Exception:
            pass
    obj = read_json(LOCAL_CATALOG, {"version": "offline", "characters": []})
    return obj if isinstance(obj, dict) else {"version": "offline", "characters": []}


def parse_name(name: str) -> Dict[str, str] | None:
    m = MOD_RE.match(name)
    if not m:
        return None
    d = {k: (v or "") for k, v in m.groupdict().items()}
    d["action"] = d["action"].lower()
    return d


def author_from_rest(rest: str) -> str:
    if not rest:
        return ""
    # Convention seen in the user's collection: Na0h_Summer-Anis-Nude
    first = re.split(r"[_\- ]+", rest.strip(), maxsplit=1)[0]
    if 1 <= len(first) <= 40 and not first.lower().startswith(("nude", "skin", "mod")):
        return first
    return ""


def scan_mods() -> List[Dict[str, Any]]:
    root_s = str(config().get("modsPath") or "").strip()
    if not root_s:
        return []
    root = Path(root_s)
    if not root.is_dir():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        entries = sorted(root.iterdir(), key=lambda p: p.name.lower())
    except Exception:
        return []
    for p in entries:
        info = parse_name(p.name)
        if not info:
            continue
        rest = info.get("rest", "")
        rows.append({
            "id": info["id"],
            "ver": info["ver"],
            "key": f"{info['id']}_{info['ver']}",
            "action": info["action"],
            "name": rest.replace("_", " ") if rest else p.name,
            "rawName": p.name,
            "author": author_from_rest(rest),
            "path": str(p.resolve()),
            "isDir": p.is_dir(),
            "size": p.stat().st_size if p.is_file() else 0,
        })
    return rows


def inventory(refresh_catalog: bool = False) -> Dict[str, Any]:
    cat = load_catalog(refresh_catalog)
    mods = scan_mods()
    by_key: Dict[str, List[Dict[str, Any]]] = {}
    for m in mods:
        by_key.setdefault(m["key"], []).append(m)
    meta = metadata().get("characters", {})
    chars = []
    for c in cat.get("characters", []):
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id", ""))
        ver = str(c.get("version", c.get("ver", "")))
        key = str(c.get("key") or f"{cid}_{ver}")
        cm = by_key.get(key, [])
        action_counts = {a: sum(1 for x in cm if x["action"] == a) for a in ("standing", "aim", "cover")}
        conflicts = [a for a, n in action_counts.items() if n >= 2]
        user = meta.get(key, {}) if isinstance(meta, dict) else {}
        chars.append({
            "id": cid,
            "ver": ver,
            "key": key,
            "name": c.get("name", key),
            "npcExtra": bool(c.get("npcExtra", False)),
            "mods": cm,
            "counts": action_counts,
            "conflicts": conflicts,
            "hasMods": bool(cm),
            "tags": user.get("tags", []) if isinstance(user, dict) else [],
            "notes": user.get("notes", "") if isinstance(user, dict) else "",
            "image": f"{IMAGE_BASE}/c{cid}_{ver}.webp",
        })
    # Unknown mod IDs remain visible rather than disappearing.
    known = {c["key"] for c in chars}
    for key, cm in by_key.items():
        if key in known:
            continue
        cid, ver = key.split("_", 1)
        action_counts = {a: sum(1 for x in cm if x["action"] == a) for a in ("standing", "aim", "cover")}
        user = meta.get(key, {}) if isinstance(meta, dict) else {}
        chars.append({
            "id": cid, "ver": ver, "key": key, "name": f"Unknown {key}", "npcExtra": False,
            "mods": cm, "counts": action_counts,
            "conflicts": [a for a, n in action_counts.items() if n >= 2],
            "hasMods": True,
            "tags": user.get("tags", []) if isinstance(user, dict) else [],
            "notes": user.get("notes", "") if isinstance(user, dict) else "",
            "image": f"{IMAGE_BASE}/c{cid}_{ver}.webp",
        })
    chars.sort(key=lambda x: (int(x["id"]) if str(x["id"]).isdigit() else 99999, x["ver"]))
    return {
        "catalogVersion": cat.get("version", ""),
        "modsPath": config().get("modsPath", ""),
        "language": config().get("language", "es"),
        "characters": chars,
        "modCount": len(mods),
        "characterModCount": sum(1 for x in chars if x["hasMods"]),
        "conflictCount": sum(len(x["conflicts"]) for x in chars),
    }


def pick_folder() -> str:
    try:
        import tkinter as tk
        from tkinter import filedialog
        r = tk.Tk(); r.withdraw(); r.attributes("-topmost", True)
        initial = config().get("modsPath") or str(Path.home())
        p = filedialog.askdirectory(title="Selecciona la carpeta donde están los mods de NIKKE", initialdir=initial)
        r.destroy()
        return p or ""
    except Exception:
        return ""


def local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close(); return ip
    except Exception:
        return "127.0.0.1"


HTML = r'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NIKKE Mod Manager v0.12</title>
<style>
:root{--bg:#090c12;--panel:#111824;--panel2:#151e2c;--line:#2a3749;--text:#edf1f7;--muted:#929eb0;--yellow:#ffc83d;--red:#ff6676;--green:#57d99b;--blue:#6ea8ff}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 10% 0,#162137 0,#090c12 35%);color:var(--text);font-family:Inter,Segoe UI,Arial,sans-serif}.wrap{max-width:1450px;margin:auto;padding:24px}.top{display:flex;align-items:center;gap:16px;justify-content:space-between;flex-wrap:wrap}.brand{font-size:28px;font-weight:900;letter-spacing:1px}.brand b{color:var(--yellow);font-size:13px;margin-left:10px}.stats{color:var(--muted);font-size:14px}.actions{display:flex;gap:8px}.btn{border:1px solid var(--line);background:var(--panel);color:var(--text);padding:11px 14px;border-radius:12px;cursor:pointer;font-weight:650}.btn:hover{border-color:#53647b}.btn.yellow{background:var(--yellow);color:#17130a;border-color:var(--yellow)}.toolbar{display:grid;grid-template-columns:minmax(250px,1fr) 170px 170px;gap:10px;margin:20px 0 10px}.toolbar input,.toolbar select,.modal input,.modal textarea{width:100%;background:var(--panel);border:1px solid var(--line);color:var(--text);border-radius:12px;padding:12px}.chips{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 18px}.chip{padding:9px 13px;border:1px solid var(--line);border-radius:999px;color:#cbd3df;cursor:pointer;background:#101722}.chip.active{background:var(--yellow);color:#17130a;border-color:var(--yellow);font-weight:800}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(285px,1fr));gap:12px}.card{background:linear-gradient(160deg,var(--panel2),#0e141e);border:1px solid var(--line);border-radius:16px;overflow:hidden;cursor:pointer;min-height:210px;display:grid;grid-template-columns:105px 1fr}.card:hover{transform:translateY(-1px);border-color:#53647b}.pic{background:#080b10;display:flex;align-items:center;justify-content:center;overflow:hidden}.pic img{width:100%;height:100%;object-fit:cover}.body{padding:14px}.name{font-size:17px;font-weight:800;line-height:1.2}.id{font-size:12px;color:var(--muted);margin-top:5px}.badge{display:inline-block;margin-top:8px;padding:4px 7px;border-radius:7px;font-size:11px;background:#1b2637;color:#cbd5e3}.badge.npc{background:#352b19;color:#ffd873}.acts{display:flex;gap:6px;flex-wrap:wrap;margin-top:12px}.act{font-size:11px;border:1px solid var(--line);border-radius:7px;padding:5px 7px}.act.on{border-color:#356f57;color:#7ce8b2}.act.conf{border-color:#8d3e49;color:#ff8c98}.empty{padding:70px;text-align:center;color:var(--muted)}.modalbg{position:fixed;inset:0;background:#000a;display:none;align-items:center;justify-content:center;padding:22px;z-index:20}.modalbg.show{display:flex}.modal{background:#101824;border:1px solid #3a4a61;border-radius:18px;width:min(1000px,96vw);max-height:92vh;overflow:auto}.mhead{padding:18px 20px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between}.mcontent{display:grid;grid-template-columns:230px 1fr;gap:18px;padding:20px}.mimg{width:100%;height:330px;object-fit:contain;background:#080b10;border-radius:12px}.modrow{border:1px solid var(--line);background:#0d141f;padding:10px;border-radius:10px;margin:8px 0;display:flex;gap:10px;align-items:center;justify-content:space-between}.modrow .small{font-size:12px;color:var(--muted);word-break:break-all}.preview{background:#1c3048;border-color:#3a6592}.warn{color:#ff9aa5;font-weight:750}.first{position:fixed;inset:0;background:#080b11f2;display:none;z-index:50;align-items:center;justify-content:center}.first.show{display:flex}.firstbox{width:min(620px,92vw);background:#111824;border:1px solid #35445a;border-radius:18px;padding:28px}.langs{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:18px}.pathline{display:flex;gap:8px;margin-top:16px}.pathline input{flex:1}.footer{color:#6f7d90;text-align:center;padding:35px 0;font-size:12px}@media(max-width:750px){.toolbar{grid-template-columns:1fr}.mcontent{grid-template-columns:1fr}.mimg{height:260px}}
</style></head><body>
<div class="first" id="first"><div class="firstbox"><h1 id="fTitle">NIKKE Mod Manager</h1><p id="fDesc">Primera configuración: elige idioma y la carpeta donde están tus mods.</p><div class="langs"><button class="btn yellow" onclick="setLang('es')">Español</button><button class="btn" onclick="setLang('en')">English</button></div><div class="pathline"><input id="firstPath" readonly placeholder="Carpeta de mods"><button class="btn" onclick="pickFolder(true)">📁</button></div><button style="width:100%;margin-top:12px" class="btn yellow" onclick="finishFirst()">Continuar</button></div></div>
<div class="wrap"><div class="top"><div><div class="brand">NIKKE <b>MOD MANAGER · v0.12 PREVIEW BETA</b></div><div class="stats" id="stats"></div></div><div class="actions"><button class="btn" onclick="refresh(true)" title="Actualizar catálogo y mods">↻ Actualizar</button><button class="btn" onclick="pickFolder(false)">📁 Mods</button><button class="btn" onclick="toggleLang()">ES / EN</button></div></div>
<div class="toolbar"><input id="q" placeholder="Buscar nombre, ID o mod..." oninput="render()"><select id="sort" onchange="render()"><option value="id">ID ↑</option><option value="name">Nombre</option><option value="mods">Más mods</option></select><select id="tagFilter" onchange="render()"><option value="">Todas las etiquetas</option></select></div>
<div class="chips"><button class="chip active" data-f="all">Todos</button><button class="chip" data-f="with">Con mods</button><button class="chip" data-f="without">Sin mods</button><button class="chip" data-f="conflicts">Conflictos</button><button class="chip" data-f="npc">NPC / Extra</button></div>
<div id="grid" class="grid"></div><div class="footer">Proyecto personal · Inspirado en BD2ModManager · Preview propio experimental</div></div>
<div class="modalbg" id="modal"><div class="modal"><div class="mhead"><div><div class="name" id="mn"></div><div class="id" id="mid"></div></div><button class="btn" onclick="closeModal()">✕</button></div><div class="mcontent"><div><img id="mi" class="mimg"><div id="mbadge"></div></div><div><h3 id="mmodsTitle">Mods</h3><div id="mods"></div><h3 id="tagsTitle">Etiquetas</h3><input id="tags" placeholder="Favorito, Revisado, ..."><h3 id="notesTitle">Notas</h3><textarea id="notes" rows="4"></textarea><button class="btn yellow" style="margin-top:10px" onclick="saveMeta()" id="saveBtn">Guardar</button></div></div></div></div>
<script>
let inv={characters:[]}, filter='all', current=null, lang='es';
const T={es:{first:'Primera configuración: elige idioma y la carpeta donde están tus mods.',continue:'Continuar',search:'Buscar nombre, ID o mod...',mods:'Mods',tags:'Etiquetas',notes:'Notas',save:'Guardar',all:'Todos',with:'Con mods',without:'Sin mods',conflicts:'Conflictos',npc:'NPC / Extra',preview:'👁 Vista previa',nomods:'Sin mods',stats:(a,b,c)=>`${a} personajes con mods · ${b} mods · ${c} conflictos`},en:{first:'First setup: choose language and your NIKKE mods folder.',continue:'Continue',search:'Search name, ID or mod...',mods:'Mods',tags:'Tags',notes:'Notes',save:'Save',all:'All',with:'With mods',without:'Without mods',conflicts:'Conflicts',npc:'NPC / Extra',preview:'👁 Preview',nomods:'No mods',stats:(a,b,c)=>`${a} characters with mods · ${b} mods · ${c} conflicts`}};
function tx(k){return T[lang][k]||k}function esc(s){return String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function api(url,opt){let r=await fetch(url,opt); if(!r.ok) throw new Error(await r.text()); return await r.json()}
async function load(){inv=await api('/api/inventory');lang=inv.language||'es';applyText();if(!inv.modsPath)document.getElementById('first').classList.add('show');buildTags();render()}
function applyText(){document.getElementById('fDesc').textContent=tx('first');document.querySelector('#firstbox button');document.getElementById('q').placeholder=tx('search');document.getElementById('mmodsTitle').textContent=tx('mods');document.getElementById('tagsTitle').textContent=tx('tags');document.getElementById('notesTitle').textContent=tx('notes');document.getElementById('saveBtn').textContent=tx('save');let ks=['all','with','without','conflicts','npc'];document.querySelectorAll('.chip').forEach((x,i)=>x.textContent=tx(ks[i]));}
function buildTags(){let tags=[...new Set(inv.characters.flatMap(c=>c.tags||[]))].sort();let s=document.getElementById('tagFilter'),v=s.value;s.innerHTML='<option value="">'+(lang==='es'?'Todas las etiquetas':'All tags')+'</option>'+tags.map(t=>`<option>${esc(t)}</option>`).join('');s.value=v}
function render(){let q=document.getElementById('q').value.toLowerCase().trim(),tag=document.getElementById('tagFilter').value;let a=inv.characters.filter(c=>{if(filter==='with'&&!c.hasMods)return false;if(filter==='without'&&c.hasMods)return false;if(filter==='conflicts'&&!c.conflicts.length)return false;if(filter==='npc'&&!c.npcExtra)return false;if(tag&&!(c.tags||[]).includes(tag))return false;if(q){let hay=[c.name,c.id,c.ver,...c.mods.map(m=>m.rawName)].join(' ').toLowerCase();if(!hay.includes(q))return false}return true});let sort=document.getElementById('sort').value;if(sort==='name')a.sort((x,y)=>x.name.localeCompare(y.name));if(sort==='mods')a.sort((x,y)=>y.mods.length-x.mods.length);let g=document.getElementById('grid');g.innerHTML=a.map(c=>{let badge=c.npcExtra?'<span class="badge npc">NPC / Extra</span>':'';let acts=['standing','aim','cover'].filter(x=>!c.npcExtra||x==='standing').map(x=>{let n=c.counts[x]||0,cl=n>=2?' conf':n?' on':'';return `<span class="act${cl}">${x[0].toUpperCase()+x.slice(1)} · ${n}</span>`}).join('');return `<div class="card" onclick="openCard('${c.key}')"><div class="pic"><img loading="lazy" src="${c.image}" onerror="this.style.opacity=.15"></div><div class="body"><div class="name">${esc(c.name)}</div><div class="id">ID ${esc(c.id)} · Ver ${esc(c.ver)}</div>${badge}<div class="acts">${acts}</div>${c.conflicts.length?`<div class="warn" style="margin-top:8px">⚠ ${esc(c.conflicts.join(', '))}</div>`:''}</div></div>`}).join('')||`<div class="empty">${tx('nomods')}</div>`;document.getElementById('stats').textContent=tx('stats')(inv.characterModCount,inv.modCount,inv.conflictCount)}
function openCard(key){current=inv.characters.find(c=>c.key===key);if(!current)return;document.getElementById('mn').textContent=current.name;document.getElementById('mid').textContent=`ID ${current.id} · Ver ${current.ver}`;document.getElementById('mi').src=current.image;document.getElementById('mbadge').innerHTML=current.npcExtra?'<span class="badge npc">NPC / Extra</span>':'';let el=document.getElementById('mods');if(!current.mods.length)el.innerHTML='<div class="empty" style="padding:25px">'+tx('nomods')+'</div>';else el.innerHTML=current.mods.map(m=>`<div class="modrow"><div><b>${esc(m.rawName)}</b><div class="small">${esc(m.action)}${m.author?' · '+esc(m.author):''}<br>${esc(m.path)}</div></div><button class="btn preview" onclick="event.stopPropagation();preview('${encodeURIComponent(m.path)}')">${tx('preview')}</button></div>`).join('');document.getElementById('tags').value=(current.tags||[]).join(', ');document.getElementById('notes').value=current.notes||'';document.getElementById('modal').classList.add('show')}
function closeModal(){document.getElementById('modal').classList.remove('show')}function preview(p){window.open('http://127.0.0.1:8137/viewer?path='+p,'nikkePreview','width=1250,height=900')}
async function saveMeta(){if(!current)return;let tags=document.getElementById('tags').value.split(',').map(x=>x.trim()).filter(Boolean),notes=document.getElementById('notes').value;await api('/api/meta',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:current.key,tags,notes})});await refresh(false);closeModal()}
async function refresh(online){inv=await api('/api/inventory?online='+(online?'1':'0'));buildTags();render()}
async function pickFolder(first){let r=await api('/api/pick-folder',{method:'POST'});if(r.path){if(first)document.getElementById('firstPath').value=r.path;else{await api('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({modsPath:r.path})});await refresh(false)}}}
async function setLang(l){lang=l;applyText();await api('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({language:l})})}async function toggleLang(){await setLang(lang==='es'?'en':'es');await refresh(false)}
async function finishFirst(){let p=document.getElementById('firstPath').value;if(!p){alert(lang==='es'?'Selecciona la carpeta de mods.':'Select the mods folder.');return}await api('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({modsPath:p,language:lang})});document.getElementById('first').classList.remove('show');await refresh(false)}
document.querySelectorAll('.chip').forEach(x=>x.onclick=()=>{document.querySelectorAll('.chip').forEach(y=>y.classList.remove('active'));x.classList.add('active');filter=x.dataset.f;render()});document.getElementById('modal').addEventListener('click',e=>{if(e.target.id==='modal')closeModal()});load().catch(e=>document.getElementById('grid').innerHTML='<div class="empty">'+esc(e.message)+'</div>');
</script></body></html>'''


class Handler(BaseHTTPRequestHandler):
    server_version = "NIKKEModManager/0.12"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def send_bytes(self, data: bytes, ctype: str = "application/json; charset=utf-8", status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, obj: Any, status: int = 200) -> None:
        self.send_bytes(json.dumps(obj, ensure_ascii=False).encode("utf-8"), status=status)

    def read_json(self) -> Dict[str, Any]:
        try:
            n = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
        except Exception:
            return {}

    def do_GET(self) -> None:
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        try:
            if u.path == "/":
                self.send_bytes(HTML.encode("utf-8"), "text/html; charset=utf-8")
            elif u.path == "/api/inventory":
                self.send_json(inventory(q.get("online", ["0"])[0] == "1"))
            elif u.path == "/api/health":
                self.send_json({"ok": True, "version": "0.12", "ip": local_ip()})
            else:
                self.send_json({"error": "not found"}, 404)
        except Exception as exc:
            self.send_json({"error": str(exc)}, 500)

    def do_POST(self) -> None:
        u = urllib.parse.urlparse(self.path)
        try:
            if u.path == "/api/pick-folder":
                self.send_json({"path": pick_folder()})
                return
            if u.path == "/api/config":
                body = self.read_json(); c = config()
                for k in ("modsPath", "language"):
                    if k in body:
                        c[k] = body[k]
                write_json(CONFIG_FILE, c)
                self.send_json({"ok": True, "config": c})
                return
            if u.path == "/api/meta":
                body = self.read_json(); key = str(body.get("key", ""))
                if not key:
                    self.send_json({"error": "missing key"}, 400); return
                m = metadata(); chars = m.setdefault("characters", {})
                chars[key] = {"tags": list(dict.fromkeys(body.get("tags", []))), "notes": str(body.get("notes", "")), "updatedAt": time.time()}
                write_json(META_FILE, m)
                self.send_json({"ok": True})
                return
            self.send_json({"error": "not found"}, 404)
        except Exception as exc:
            self.send_json({"error": str(exc)}, 500)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--no-browser", action="store_true")
    ns = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", ns.port), Handler)
    url = f"http://127.0.0.1:{ns.port}/"
    if not ns.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"NIKKE Mod Manager v0.12: {url}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

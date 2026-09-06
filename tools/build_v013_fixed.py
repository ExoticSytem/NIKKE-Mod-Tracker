from __future__ import annotations

import build_v013 as old


def fixed_patch_preview(src: str) -> str:
    text = old.patch_preview(src)

    replacements = {
        "function stopDemo(){if(demoTimer){clearInterval(demoTimer);demoTimer=null;}const b=$('#demoAuto');if(b)b.textContent='🎬 Demo Auto';}":
        "function stopDemo(){{if(demoTimer){{clearInterval(demoTimer);demoTimer=null;}}const b=$('#demoAuto');if(b)b.textContent='🎬 Demo Auto';}}",
        "function animationNames(){return [...$('#anim').options].map(o=>o.value).filter(Boolean);}":
        "function animationNames(){{return [...$('#anim').options].map(o=>o.value).filter(Boolean);}}",
        "function playHint(hints){if(!model)return;stopDemo();const names=animationNames();let chosen='';for(const h of hints){chosen=names.find(n=>n.toLowerCase()===h)||names.find(n=>n.toLowerCase().includes(h));if(chosen)break;}chosen=chosen||names[0]||'';if(!chosen)return;$('#anim').value=chosen;$('#loop').checked=true;model.state.setAnimation(0,chosen,true);}":
        "function playHint(hints){{if(!model)return;stopDemo();const names=animationNames();let chosen='';for(const h of hints){{chosen=names.find(n=>n.toLowerCase()===h)||names.find(n=>n.toLowerCase().includes(h));if(chosen)break;}}chosen=chosen||names[0]||'';if(!chosen)return;$('#anim').value=chosen;$('#loop').checked=true;model.state.setAnimation(0,chosen,true);}}",
        "function demoStep(){if(!model)return;const names=animationNames();if(!names.length)return;const n=names[demoIndex%names.length];demoIndex++;$('#anim').value=n;model.state.setAnimation(0,n,false);}":
        "function demoStep(){{if(!model)return;const names=animationNames();if(!names.length)return;const n=names[demoIndex%names.length];demoIndex++;$('#anim').value=n;model.state.setAnimation(0,n,false);}}",
        "function toggleAutoDemo(){if(!model)return;if(demoTimer){stopDemo();return;}demoIndex=0;demoStep();demoTimer=setInterval(demoStep,4200);$('#demoAuto').textContent='■ Detener Demo';}":
        "function toggleAutoDemo(){{if(!model)return;if(demoTimer){{stopDemo();return;}}demoIndex=0;demoStep();demoTimer=setInterval(demoStep,4200);$('#demoAuto').textContent='■ Detener Demo';}}",
        "sel.onchange=()=>{stopDemo();model.state.setAnimation(0,sel.value,$('#loop').checked);};":
        "sel.onchange=()=>{{stopDemo();model.state.setAnimation(0,sel.value,$('#loop').checked);}};",
    }

    for before, after in replacements.items():
        if before not in text:
            raise RuntimeError(f"No se encontró bloque JS esperado: {before[:45]}")
        text = text.replace(before, after, 1)
    return text


old.patch_preview = fixed_patch_preview
old.build()

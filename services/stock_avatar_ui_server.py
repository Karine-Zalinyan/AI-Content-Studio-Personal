"""Browser server extension for the free Stock + Avatar assembly flow."""

from __future__ import annotations

import json
import uuid
from http import HTTPStatus
from http.server import ThreadingHTTPServer

from config.settings import settings
from services.avatar_browser_service import AvatarBrowserService
from services.deployment_health_service import DeploymentHealthService
from services.stock_avatar_browser_api import StockAvatarBrowserRequestAdapter
from services.stock_avatar_browser_controller import StockAvatarBrowserController
from services.stock_avatar_web_service import StockAvatarWebService
from web_ui import HISTORY, HTML as BASE_HTML
from web_ui import StudioHandler

HEALTH = DeploymentHealthService(settings.output_dir)
AVATARS = AvatarBrowserService(settings.output_dir / "avatars.json")


def _stock_avatar_html() -> str:
    panel = """
<div class=\"avatar-library\"><h2>Avatar Library</h2>
<div class=\"avatar-meta\">Create a reusable canonical Avatar and use its visual reference in your stock videos.</div>
<form id=\"avatar-create\">
<label for=\"avatar-name\">Avatar name</label>
<input id=\"avatar-name\" type=\"text\" maxlength=\"120\" placeholder=\"Example: Lumi\" required>
<label for=\"avatar-appearance\">Appearance</label>
<input id=\"avatar-appearance\" type=\"text\" placeholder=\"Cream-white fur, amber eyes…\">
<label for=\"avatar-visual-reference\">Visual reference URL</label>
<input id=\"avatar-visual-reference\" type=\"url\" placeholder=\"https://…\" required>
<button id=\"avatar-create-button\" class=\"secondary\" type=\"submit\">Create Avatar</button>
</form><div id=\"avatar-status\" class=\"status\">Your saved Avatars will appear here.</div>
<div id=\"avatar-list\" class=\"avatar-list\"></div></div>
<div class=\"stock-assemble\"><h2>Assemble from Stock + Avatar</h2>
<label for=\"avatar-reference\">Selected Avatar visual reference</label>
<input id=\"avatar-reference\" type=\"url\" placeholder=\"Choose an Avatar above or paste https://…\">
<div class=\"stock-meta\">Select up to 6 portrait clips, then assemble a vertical 9:16 MP4.</div>
<button id=\"assemble-stock-avatar\" class=\"secondary\" type=\"button\">Assemble 9:16 video</button>
<div id=\"assemble-status\" class=\"status\">No assembly started.</div></div>
<script>
const assembleButton=document.getElementById('assemble-stock-avatar');
const avatarInput=document.getElementById('avatar-reference');
const assembleStatus=document.getElementById('assemble-status');
const avatarForm=document.getElementById('avatar-create');
const avatarCreateButton=document.getElementById('avatar-create-button');
const avatarStatus=document.getElementById('avatar-status');
const avatarList=document.getElementById('avatar-list');
let selectedStockClips=[];
function toggleStockSelection(clip, checked){
  const key=String(clip.id||clip.preview_url||clip.source_url||'');
  if(checked){
    if(selectedStockClips.length>=6){assembleStatus.className='status error';assembleStatus.textContent='Maximum 6 clips.';return;}
    if(!selectedStockClips.some(x=>String(x.id||x.preview_url||x.source_url||'')===key))selectedStockClips.push(clip);
  }else selectedStockClips=selectedStockClips.filter(x=>String(x.id||x.preview_url||x.source_url||'')!==key);
  assembleStatus.className='status';assembleStatus.textContent=selectedStockClips.length+' clip(s) selected.';
}
function renderAvatars(rows){
  avatarList.innerHTML=rows.length?rows.map(x=>`<div class=\"avatar-item\"><div class=\"avatar-copy\"><div class=\"avatar-name\">${escapeHtml(x.name)}</div><div class=\"avatar-meta\">${escapeHtml(x.appearance||'Canonical Avatar')}</div></div><button class=\"avatar-use secondary\" data-reference=\"${escapeHtml(x.visual_reference)}\" type=\"button\">Use Avatar</button></div>`).join(''):'<div class=\"avatar-empty\">No Avatars yet. Create your first one.</div>';
  [...document.querySelectorAll('.avatar-use')].forEach(el=>el.addEventListener('click',()=>{avatarInput.value=el.dataset.reference||'';avatarStatus.className='status ok';avatarStatus.textContent='Avatar selected for the next assembly.';}));
}
async function loadAvatars(){
  try{const r=await fetch('/api/avatars');const d=await r.json();if(!r.ok)throw new Error(d.error||'Unable to load Avatars');renderAvatars(d.avatars||[]);}catch(err){avatarStatus.className='status error';avatarStatus.textContent=err.message;}
}
avatarForm.addEventListener('submit',async e=>{
  e.preventDefault();avatarCreateButton.disabled=true;avatarStatus.className='status';avatarStatus.textContent='Saving Avatar…';
  try{const r=await fetch('/api/avatars',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:document.getElementById('avatar-name').value,appearance:document.getElementById('avatar-appearance').value,visual_reference:document.getElementById('avatar-visual-reference').value})});const d=await r.json();if(!r.ok)throw new Error(d.error||'Unable to create Avatar');avatarInput.value=d.avatar.visual_reference;avatarStatus.className='status ok';avatarStatus.textContent='Avatar created and selected.';avatarForm.reset();await loadAvatars();}catch(err){avatarStatus.className='status error';avatarStatus.textContent=err.message;}finally{avatarCreateButton.disabled=false;}
});
const originalRenderStockResults=renderStockResults;
renderStockResults=function(rows){
  stockResults.innerHTML=rows.length?rows.map((x,i)=>{
    const thumb=x.thumbnail_url?`<img class=\"stock-thumb\" src=\"${escapeHtml(x.thumbnail_url)}\" alt=\"Stock preview thumbnail\">`:'<div class=\"stock-thumb\"></div>';
    const preview=x.preview_url?`<a href=\"${escapeHtml(x.preview_url)}\" target=\"_blank\" rel=\"noopener noreferrer\">Preview clip</a>`:'';
    const source=x.source_url?`<a href=\"${escapeHtml(x.source_url)}\" target=\"_blank\" rel=\"noopener noreferrer\">Open source</a>`:'';
    const checked=selectedStockClips.some(y=>String(y.id||y.preview_url||y.source_url||'')===String(x.id||x.preview_url||x.source_url||''));
    return `<div class=\"stock-item\">${thumb}<div class=\"stock-copy\"><div class=\"stock-title\">${escapeHtml(x.title||x.id||'Stock video')}</div><div class=\"stock-meta\">${escapeHtml(stockMeta(x))}</div><label><input type=\"checkbox\" class=\"stock-select\" data-index=\"${i}\" ${checked?'checked':''}> Select for assembly</label><div class=\"stock-links\">${preview}${source}</div></div></div>`
  }).join(''):'<div class=\"stock-empty\">No portrait clips found for that search.</div>';
  [...document.querySelectorAll('.stock-select')].forEach(el=>el.addEventListener('change',()=>toggleStockSelection(rows[Number(el.dataset.index)],el.checked)));
};
assembleButton.addEventListener('click',async()=>{
  if(!selectedStockClips.length){assembleStatus.className='status error';assembleStatus.textContent='Select at least one stock clip.';return;}
  const topicValue=topic.value.trim();
  if(!topicValue){assembleStatus.className='status error';assembleStatus.textContent='Enter a video topic first.';return;}
  assembleButton.disabled=true;assembleStatus.className='status';assembleStatus.textContent='Assembling 9:16 MP4…';
  try{
    const r=await fetch('/api/stock-avatar/assemble',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({topic:topicValue,stock_clips:selectedStockClips,avatar_reference:avatarInput.value.trim()||null})});
    const d=await r.json();if(!r.ok)throw new Error(d.error||'Assembly failed');
    assembleStatus.className='status ok';assembleStatus.textContent='Done — 9:16 MP4 ready.';
    const videoUrl='/output/'+d.output_path.split('/').map(encodeURIComponent).join('/');
    preview.innerHTML='<video controls playsinline src="'+videoUrl+'"></video>';
    exportLink.href=videoUrl;exportLink.style.display='block';loadHistory();
  }catch(err){assembleStatus.className='status error';assembleStatus.textContent=err.message;}
  finally{assembleButton.disabled=false;}
});
loadAvatars();
</script>
"""
    return BASE_HTML.replace("</body>", panel + "</body>", 1)


HTML = _stock_avatar_html()


class StockAvatarStudioHandler(StudioHandler):
    """Extend the existing MVP handler without replacing its generation pipeline."""

    def do_GET(self) -> None:
        if self.path == "/":
            self._send(HTML.encode(), "text/html; charset=utf-8")
            return
        if self.path == "/health":
            payload = HEALTH.status()
            status = HTTPStatus.OK if payload["status"] == "ok" else HTTPStatus.SERVICE_UNAVAILABLE
            self._send(json.dumps(payload).encode(), "application/json", status)
            return
        if self.path == "/api/avatars":
            self._send(json.dumps({"avatars": AVATARS.list()}).encode(), "application/json")
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path == "/api/avatars":
            length = int(self.headers.get("Content-Length", "0"))
            if length > 10000:
                self._send(b'{"error":"Request too large"}', "application/json", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
                return
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                avatar = AVATARS.create(
                    name=payload.get("name", ""),
                    appearance=payload.get("appearance", ""),
                    visual_reference=payload.get("visual_reference", ""),
                )
                self._send(json.dumps({"avatar": avatar}).encode(), "application/json", HTTPStatus.CREATED)
            except (ValueError, json.JSONDecodeError) as exc:
                self._send(json.dumps({"error": str(exc)}).encode(), "application/json", HTTPStatus.BAD_REQUEST)
            return
        if self.path != "/api/stock-avatar/assemble":
            super().do_POST()
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length > 20000:
            self._send(b'{"error":"Request too large"}', "application/json", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            request = StockAvatarBrowserRequestAdapter.parse({**payload, "output_path": "pending.mp4"})
            output_path = settings.output_dir / "stock_avatar" / f"{uuid.uuid4().hex}.mp4"
            controller = StockAvatarBrowserController(
                history=HISTORY,
                assembly=StockAvatarWebService(),
                output_root=settings.output_dir,
            )
            result = controller.assemble(
                topic=request["topic"],
                stock_clips=request["stock_clips"],
                avatar_reference=request["avatar_reference"],
                output_path=output_path,
            )
            self._send(json.dumps(result).encode(), "application/json", HTTPStatus.OK)
        except (ValueError, json.JSONDecodeError) as exc:
            self._send(json.dumps({"error": str(exc)}).encode(), "application/json", HTTPStatus.BAD_REQUEST)
        except (RuntimeError, OSError) as exc:
            self._send(json.dumps({"error": str(exc)}).encode(), "application/json", HTTPStatus.INTERNAL_SERVER_ERROR)


def serve_stock_avatar(host: str = "0.0.0.0", port: int = 8787) -> None:
    """Serve the existing MVP UI with the Stock + Avatar assembly controls."""
    settings.ensure_dirs()
    server = ThreadingHTTPServer((host, port), StockAvatarStudioHandler)
    try:
        server.serve_forever()
    finally:
        server.server_close()

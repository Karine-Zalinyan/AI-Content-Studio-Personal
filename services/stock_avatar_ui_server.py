"""Browser server extension for the free Stock + Avatar assembly flow."""

from __future__ import annotations

import json
import uuid
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

from config.settings import settings
from services.stock_avatar_browser_api import StockAvatarBrowserRequestAdapter
from services.stock_avatar_browser_controller import StockAvatarBrowserController
from services.stock_avatar_web_service import StockAvatarWebService
from web_ui import HTML as BASE_HTML
from web_ui import StudioHandler


def _stock_avatar_html() -> str:
    panel = """
<div class=\"stock-assemble\"><h2>Assemble from Stock + Avatar</h2>
<label for=\"avatar-reference\">Avatar reference URL (optional)</label>
<input id=\"avatar-reference\" type=\"url\" placeholder=\"https://…\">
<div class=\"stock-meta\">Select up to 6 clips above, then assemble a vertical 9:16 MP4.</div>
<button id=\"assemble-stock-avatar\" class=\"secondary\" type=\"button\">Assemble 9:16 video</button>
<div id=\"assemble-status\" class=\"status\">No assembly started.</div></div>
<script>
const assembleButton=document.getElementById('assemble-stock-avatar');
const avatarInput=document.getElementById('avatar-reference');
const assembleStatus=document.getElementById('assemble-status');
let selectedStockClips=[];
function toggleStockSelection(clip, checked){
  const key=String(clip.id||clip.preview_url||clip.source_url||'');
  if(checked){
    if(selectedStockClips.length>=6){assembleStatus.className='status error';assembleStatus.textContent='Maximum 6 clips.';return false;}
    if(!selectedStockClips.some(x=>String(x.id||x.preview_url||x.source_url||'')===key))selectedStockClips.push(clip);
  }else selectedStockClips=selectedStockClips.filter(x=>String(x.id||x.preview_url||x.source_url||'')!==key);
  assembleStatus.className='status';assembleStatus.textContent=selectedStockClips.length+' clip(s) selected.';
  return true;
}
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
    const videoUrl='/output/'+encodeURIComponent(d.output_path).replaceAll('%2F','/');
    preview.innerHTML='<video controls playsinline src="'+videoUrl+'"></video>';
    exportLink.href=videoUrl;exportLink.style.display='block';loadHistory();
  }catch(err){assembleStatus.className='status error';assembleStatus.textContent=err.message;}
  finally{assembleButton.disabled=false;}
});
</script>
"""
    return BASE_HTML.replace("</section>", panel + "</section>", 1)


HTML = _stock_avatar_html()


class StockAvatarStudioHandler(StudioHandler):
    """Extend the existing MVP handler without replacing its generation pipeline."""

    def do_GET(self) -> None:
        if self.path == "/":
            self._send(HTML.encode(), "text/html; charset=utf-8")
            return
        super().do_GET()

    def do_POST(self) -> None:
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
                history=__import__("web_ui", fromlist=["HISTORY"]).HISTORY,
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
        except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
            self._send(json.dumps({"error": str(exc)}).encode(), "application/json", HTTPStatus.BAD_REQUEST)


def serve_stock_avatar(host: str = "0.0.0.0", port: int = 8787) -> None:
    """Serve the existing MVP UI with the Stock + Avatar assembly controls."""
    settings.ensure_dirs()
    server = ThreadingHTTPServer((host, port), StockAvatarStudioHandler)
    try:
        server.serve_forever()
    finally:
        server.server_close()

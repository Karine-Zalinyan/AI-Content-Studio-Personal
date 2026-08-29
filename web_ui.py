"""Minimal browser UI for the Social Content Studio MVP."""
from __future__ import annotations

import json
import mimetypes
import threading
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from config.settings import settings
from models.project import Project
from services.generation_pipeline_service import GenerationPipelineService
from services.generation_planner_service import GenerationPlanner
from services.project_history_service import ProjectHistoryService
from services.project_history_web_service import ProjectHistoryWebService
from services.stock_video_service import StockVideoSearchService
from services.storyboard_context_service import StoryboardContextService

HOST = "127.0.0.1"
PORT = 8787
HISTORY = ProjectHistoryService(settings.output_dir / "studio.db")
HISTORY_WEB = ProjectHistoryWebService(HISTORY, settings.output_dir)
STOCK_VIDEOS = StockVideoSearchService()


class JobStore:
    """Small in-memory job store for live browser polling."""
    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, object]] = {}
        self._lock = threading.Lock()

    def create(self, durable_job_id: str) -> str:
        job_id = uuid.uuid4().hex
        with self._lock:
            self._jobs[job_id] = {"status": "queued", "error": "", "video": "", "durable_job_id": durable_job_id}
        return job_id

    def update(self, job_id: str, **values: object) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(values)

    def get(self, job_id: str) -> dict[str, object] | None:
        with self._lock:
            value = self._jobs.get(job_id)
            return dict(value) if value else None


JOBS = JobStore()

HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Content Studio</title>
<style>
:root{color-scheme:dark;--bg:#090a0f;--panel:#12141c;--panel2:#171a24;--line:#292d3a;--text:#f5f7fb;--muted:#9298a8;--accent:#9b6cff}
*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(circle at 70% 10%,#20163d 0,transparent 32%),var(--bg);color:var(--text);font:15px/1.5 Inter,system-ui,sans-serif}.shell{max-width:1180px;margin:auto;padding:28px}.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:32px}.brand{font-weight:700;font-size:18px}.brand span{color:var(--accent)}.badge{color:var(--muted);font-size:13px}.grid{display:grid;grid-template-columns:minmax(0,1.15fr) 360px;gap:28px;align-items:start}.card{background:rgba(18,20,28,.9);border:1px solid var(--line);border-radius:20px;padding:26px;box-shadow:0 20px 70px rgba(0,0,0,.22)}h1{font-size:38px;line-height:1.08;margin:0 0 12px;letter-spacing:-.03em}h2{font-size:18px;margin:0 0 14px}.sub{color:var(--muted);margin:0 0 28px}label{display:block;color:#cfd3df;font-size:13px;margin:20px 0 8px}textarea,input{width:100%;border:1px solid var(--line);background:var(--panel2);color:var(--text);border-radius:12px;padding:13px 14px;font:inherit;outline:none}textarea{min-height:118px;resize:vertical}textarea:focus,input:focus{border-color:var(--accent)}button{width:100%;margin-top:22px;border:0;border-radius:12px;padding:14px 18px;color:#fff;background:linear-gradient(135deg,#8c5cf6,#b278ff);font-weight:700;cursor:pointer;font-size:15px}button:disabled{opacity:.55;cursor:wait}.secondary{background:var(--panel2);border:1px solid var(--line);margin-top:12px}.preview{aspect-ratio:9/16;max-height:610px;margin:auto;border:1px solid var(--line);border-radius:18px;background:#08090d;display:flex;align-items:center;justify-content:center;overflow:hidden}.preview video{width:100%;height:100%;object-fit:contain;background:#000}.empty{text-align:center;color:var(--muted);padding:34px 20px}.empty strong{display:block;color:#e7e9ef;margin-bottom:6px}.status{margin-top:18px;min-height:24px;color:var(--muted);font-size:13px}.status.ok{color:#a7e8c2}.status.error{color:#ff9d9d}.export{display:none;margin-top:14px;color:#cfc6ff;text-decoration:none;text-align:center;padding:11px;border:1px solid var(--line);border-radius:11px}.history,.stock{margin-top:28px}.history-list,.stock-results{display:grid;gap:10px}.history-item,.stock-item{display:flex;justify-content:space-between;gap:12px;align-items:center;background:var(--panel2);border:1px solid var(--line);border-radius:12px;padding:12px 14px}.history-topic{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.history-meta,.stock-meta,.stock-empty{color:var(--muted);font-size:12px}.history-item a,.stock-links a{color:#cfc6ff;text-decoration:none;white-space:nowrap}.stock-copy{min-width:0;flex:1}.stock-title{font-weight:600;margin-bottom:4px}.stock-thumb{width:108px;min-width:108px;aspect-ratio:9/16;border-radius:10px;object-fit:cover;background:#0d1018;border:1px solid var(--line)}.stock-links{display:flex;gap:12px;flex-wrap:wrap;margin-top:8px}.meta{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:18px}.meta div{background:var(--panel2);border-radius:12px;padding:12px;color:var(--muted);font-size:12px}.meta b{display:block;color:var(--text);font-size:14px;margin-top:3px}@media(max-width:820px){.shell{padding:18px}.grid{grid-template-columns:1fr}h1{font-size:31px}.stock-item{align-items:flex-start}.stock-thumb{width:88px;min-width:88px}}
</style></head>
<body><div class="shell"><div class="top"><div class="brand"><span>✦</span> AI CONTENT STUDIO</div><div class="badge">MVP · Social Content</div></div>
<div class="grid"><section class="card"><h1>Create your next video.</h1><p class="sub">Start with one idea. The existing Studio pipeline turns it into a vertical 9:16 MP4.</p>
<form id="create"><label for="topic">What should the video be about?</label><textarea id="topic" placeholder="Example: A child helps a tired courier carry heavy boxes..." required></textarea><button id="generate" type="submit">✦ Generate video</button></form><div id="status" class="status">Ready when you are.</div>
<div class="stock"><h2>Free Stock Video Search</h2><div id="stock-search"><label for="stock-query">Find portrait clips for Shorts or YouTube</label><input id="stock-query" type="text" placeholder="Example: aerial city at night"><button id="stock-submit" class="secondary" type="button">Search free stock video</button></div><div id="stock-status" class="status">Search Pexels for reusable portrait clips.</div><div id="stock-results" class="stock-results"><div class="stock-empty">No clips searched yet.</div></div></div>
<div class="history"><h2>Recent Projects</h2><div id="history" class="history-list"><div class="history-meta">Loading history…</div></div></div></section>
<aside class="card"><div id="preview" class="preview"><div class="empty"><strong>Your preview</strong>Generated video will appear here.</div></div><div class="meta"><div>Pipeline<b>Storyboard → Generation → Export</b></div><div>Output<b>9:16 MP4</b></div></div><a id="export" class="export" href="#" download>Export MP4</a></aside></div></div>
<script>
const form=document.getElementById('create'),topic=document.getElementById('topic'),button=document.getElementById('generate'),status=document.getElementById('status'),preview=document.getElementById('preview'),exportLink=document.getElementById('export'),historyBox=document.getElementById('history'),stockQuery=document.getElementById('stock-query'),stockButton=document.getElementById('stock-submit'),stockStatus=document.getElementById('stock-status'),stockResults=document.getElementById('stock-results');
async function loadHistory(){const r=await fetch('/api/history');const rows=await r.json();historyBox.innerHTML=rows.length?rows.map(x=>{const action=x.video_url?`<a href="${x.video_url}" target="_blank">Open MP4</a>`:'';return `<div class="history-item"><div><div class="history-topic">${escapeHtml(x.topic)}</div><div class="history-meta">${x.status} · ${x.updated_at}</div></div>${action}</div>`}).join(''):'<div class="history-meta">No projects yet.</div>'}
function escapeHtml(v){return String(v).replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\\':'&#39;'}[c]))}
function stockMeta(x){const parts=[];if(x.duration_seconds)parts.push(x.duration_seconds+'s');if(x.orientation)parts.push(x.orientation);if(x.width&&x.height)parts.push(x.width+'×'+x.height);return parts.join(' · ')||'Metadata unavailable'}
function renderStockResults(rows){stockResults.innerHTML=rows.length?rows.map(x=>{const thumb=x.thumbnail_url?`<img class="stock-thumb" src="${escapeHtml(x.thumbnail_url)}" alt="Stock preview thumbnail">`:'<div class="stock-thumb"></div>';const preview=x.preview_url?`<a href="${escapeHtml(x.preview_url)}" target="_blank" rel="noopener noreferrer">Preview clip</a>`:'';const source=x.source_url?`<a href="${escapeHtml(x.source_url)}" target="_blank" rel="noopener noreferrer">Open source</a>`:'';return `<div class="stock-item">${thumb}<div class="stock-copy"><div class="stock-title">${escapeHtml(x.title||x.id||'Stock video')}</div><div class="stock-meta">${escapeHtml(stockMeta(x))}</div><div class="stock-links">${preview}${source}</div></div></div>`}).join(''):'<div class="stock-empty">No portrait clips found for that search.</div>'}
form.addEventListener('submit',async e=>{e.preventDefault();button.disabled=true;status.className='status';status.textContent='Starting generation…';exportLink.style.display='none';try{const body=new URLSearchParams({topic:topic.value});const r=await fetch('/generate',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body});const d=await r.json();if(!r.ok)throw new Error(d.error||'Unable to start generation');poll(d.job_id)}catch(err){status.className='status error';status.textContent=err.message;button.disabled=false}});
async function searchStock(){stockButton.disabled=true;stockStatus.className='status';stockStatus.textContent='Searching free stock clips…';try{const query=stockQuery.value.trim();const r=await fetch('/api/stock-videos?query='+encodeURIComponent(query));const d=await r.json();if(!r.ok)throw new Error(d.error||'Unable to search stock videos');renderStockResults(d.results||[]);stockStatus.className='status ok';stockStatus.textContent=d.results&&d.results.length?'Found free stock clips from Pexels.':'No free stock clips found.'}catch(err){stockStatus.className='status error';stockStatus.textContent=err.message;stockResults.innerHTML='<div class="stock-empty">Stock search is unavailable right now.</div>'}finally{stockButton.disabled=false}}
stockButton.addEventListener('click',searchStock);
stockQuery.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();searchStock()}});
async function poll(id){const r=await fetch('/api/jobs/'+id);const d=await r.json();if(d.status==='queued')status.textContent='Queued…';else if(d.status==='generating')status.textContent='Generating your scenes…';else if(d.status==='done'){status.className='status ok';status.textContent='Done — your 9:16 video is ready.';button.disabled=false;preview.innerHTML='<video controls playsinline src="'+d.video_url+'"></video>';exportLink.href=d.video_url;exportLink.style.display='block';loadHistory();return}else if(d.status==='failed'){status.className='status error';status.textContent='Generation failed: '+d.error;button.disabled=false;loadHistory();return}setTimeout(()=>poll(id),1000)}
loadHistory();
</script></body></html>"""


def _run_generation(job_id: str, durable_job_id: str, project_id: str, topic: str) -> None:
    try:
        JOBS.update(job_id, status="generating")
        HISTORY.update_job(durable_job_id, status="generating")
        project = Project(topic=topic)
        storyboard = StoryboardContextService().create(project)
        plan = GenerationPlanner().create(storyboard)
        result = GenerationPipelineService(output_dir=settings.output_dir).run(plan)
        video_path = Path(result.video.file_path or "").resolve()
        output_root = settings.output_dir.resolve()
        relative = video_path.relative_to(output_root)
        metadata = dict(result.video.metadata or {})
        HISTORY.update_job(durable_job_id, status="done", output_path=str(relative), output_metadata=metadata)
        JOBS.update(job_id, status="done", video=str(relative))
    except Exception as exc:
        HISTORY.update_job(durable_job_id, status="failed", error_message=str(exc))
        JOBS.update(job_id, status="failed", error=str(exc))


class StudioHandler(BaseHTTPRequestHandler):
    server_version="AIContentStudio/0.2"
    def _send(self, body:bytes, content_type:str, status:int=HTTPStatus.OK)->None:
        self.send_response(status);self.send_header("Content-Type",content_type);self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self)->None:
        parsed=urlparse(self.path)
        if parsed.path=="/": self._send(HTML.encode(),"text/html; charset=utf-8");return
        if parsed.path=="/api/history": self._send(json.dumps(HISTORY_WEB.recent()).encode(),"application/json");return
        if parsed.path=="/api/stock-videos":
            query = parse_qs(parsed.query).get("query", [""])[0].strip()
            if not query:
                self._send(b'{"error":"Query cannot be empty"}',"application/json",400);return
            try:
                results = STOCK_VIDEOS.search(query, orientation="portrait")
            except Exception:
                self._send(b'{"error":"Stock video search unavailable"}',"application/json",502);return
            self._send(json.dumps({"results": results}).encode(),"application/json");return
        if parsed.path.startswith("/api/jobs/"):
            job=JOBS.get(parsed.path.rsplit("/",1)[-1])
            if job is None:self._send(b'{"error":"Job not found"}',"application/json",404);return
            if job.get("video"):job["video_url"]="/output/"+str(job["video"])
            self._send(json.dumps(job).encode(),"application/json");return
        if parsed.path.startswith("/output/"):
            relative=parsed.path.removeprefix("/output/");root=settings.output_dir.resolve();candidate=(root/relative).resolve()
            try:candidate.relative_to(root)
            except ValueError:self._send(b"Forbidden","text/plain; charset=utf-8",403);return
            if not candidate.is_file():self._send(b"Not found","text/plain; charset=utf-8",404);return
            self._send(candidate.read_bytes(),mimetypes.guess_type(candidate.name)[0] or "application/octet-stream");return
        self._send(b"Not found","text/plain; charset=utf-8",404)
    def do_POST(self)->None:
        if self.path!="/generate":self._send(b"Not found","text/plain; charset=utf-8",404);return
        length=int(self.headers.get("Content-Length","0"))
        if length>20000:self._send(b'{"error":"Request too large"}',"application/json",413);return
        topic=parse_qs(self.rfile.read(length).decode("utf-8")).get("topic",[""])[0].strip()
        if not topic:self._send(b'{"error":"Topic cannot be empty"}',"application/json",400);return
        project_id=HISTORY.create_project(topic);durable_job_id=HISTORY.create_job(project_id);job_id=JOBS.create(durable_job_id)
        threading.Thread(target=_run_generation,args=(job_id,durable_job_id,project_id,topic),daemon=True).start()
        self._send(json.dumps({"job_id":job_id}).encode(),"application/json",202)
    def log_message(self,format:str,*args:object)->None:return


def serve(host:str=HOST,port:int=PORT)->None:
    settings.ensure_dirs();server=ThreadingHTTPServer((host,port),StudioHandler);print(f"AI Content Studio running at http://{host}:{port}")
    try:server.serve_forever()
    except KeyboardInterrupt:print("\nStopping AI Content Studio.")
    finally:server.server_close()

if __name__=="__main__":serve()

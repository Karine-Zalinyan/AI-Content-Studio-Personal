"""Minimal browser UI for the Social Content Studio MVP.

Run with::

    python web_ui.py

The UI is intentionally thin: it creates a Project, builds the existing
StoryboardContext/GenerationPlan, and delegates generation/export to the
existing GenerationPipelineService. No provider or domain logic lives here.
"""

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
from services.storyboard_context_service import StoryboardContextService


HOST = "127.0.0.1"
PORT = 8787


class JobStore:
    """Small in-memory job store for the MVP browser session."""

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, object]] = {}
        self._lock = threading.Lock()

    def create(self) -> str:
        job_id = uuid.uuid4().hex
        with self._lock:
            self._jobs[job_id] = {"status": "queued", "error": "", "video": ""}
        return job_id

    def update(self, job_id: str, **values: object) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(values)

    def get(self, job_id: str) -> dict[str, object] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None


JOBS = JobStore()


HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Content Studio</title>
<style>
:root { color-scheme: dark; --bg:#090a0f; --panel:#12141c; --panel2:#171a24; --line:#292d3a; --text:#f5f7fb; --muted:#9298a8; --accent:#9b6cff; }
* { box-sizing:border-box; }
body { margin:0; min-height:100vh; background:radial-gradient(circle at 70% 10%, #20163d 0, transparent 32%), var(--bg); color:var(--text); font:15px/1.5 Inter, ui-sans-serif, system-ui, -apple-system, sans-serif; }
.shell { max-width:1180px; margin:0 auto; padding:28px; }
.top { display:flex; justify-content:space-between; align-items:center; margin-bottom:42px; }
.brand { font-weight:700; letter-spacing:.02em; font-size:18px; }
.brand span { color:var(--accent); }
.badge { color:var(--muted); font-size:13px; }
.grid { display:grid; grid-template-columns:minmax(0,1.15fr) 360px; gap:28px; align-items:start; }
.card { background:rgba(18,20,28,.88); border:1px solid var(--line); border-radius:20px; padding:26px; box-shadow:0 20px 70px rgba(0,0,0,.22); }
h1 { font-size:38px; line-height:1.08; margin:0 0 12px; letter-spacing:-.03em; }
.sub { color:var(--muted); margin:0 0 28px; }
label { display:block; color:#cfd3df; font-size:13px; margin:20px 0 8px; }
textarea, select { width:100%; border:1px solid var(--line); background:var(--panel2); color:var(--text); border-radius:12px; padding:13px 14px; font:inherit; outline:none; }
textarea { min-height:118px; resize:vertical; }
textarea:focus, select:focus { border-color:var(--accent); }
button { width:100%; margin-top:22px; border:0; border-radius:12px; padding:14px 18px; color:white; background:linear-gradient(135deg,#8c5cf6,#b278ff); font-weight:700; cursor:pointer; font-size:15px; }
button:disabled { opacity:.55; cursor:wait; }
.preview { aspect-ratio:9/16; max-height:610px; margin:auto; border:1px solid var(--line); border-radius:18px; background:#08090d; display:flex; align-items:center; justify-content:center; overflow:hidden; }
.preview video { width:100%; height:100%; object-fit:contain; background:#000; }
.empty { text-align:center; color:var(--muted); padding:34px 20px; }
.empty strong { display:block; color:#e7e9ef; margin-bottom:6px; }
.status { margin-top:18px; min-height:24px; color:var(--muted); font-size:13px; }
.status.ok { color:#a7e8c2; } .status.error { color:#ff9d9d; }
.export { display:none; margin-top:14px; color:#cfc6ff; text-decoration:none; text-align:center; padding:11px; border:1px solid var(--line); border-radius:11px; }
.meta { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:18px; }
.meta div { background:var(--panel2); border-radius:12px; padding:12px; color:var(--muted); font-size:12px; }
.meta b { display:block; color:var(--text); font-size:14px; margin-top:3px; }
@media (max-width:820px) { .shell{padding:18px}.grid{grid-template-columns:1fr} .preview{max-height:70vh} h1{font-size:31px} }
</style>
</head>
<body>
<div class="shell">
  <div class="top"><div class="brand"><span>✦</span> AI CONTENT STUDIO</div><div class="badge">MVP · Social Content</div></div>
  <div class="grid">
    <section class="card">
      <h1>Create your next video.</h1>
      <p class="sub">Start with one idea. The existing Studio pipeline turns it into a vertical 9:16 MP4.</p>
      <form id="create">
        <label for="topic">What should the video be about?</label>
        <textarea id="topic" name="topic" placeholder="Example: A child helps a tired courier carry heavy boxes..." required></textarea>
        <label for="format">Format</label>
        <select id="format" disabled><option>9:16 · TikTok / Reels / Shorts</option></select>
        <button id="generate" type="submit">✦ Generate video</button>
      </form>
      <div id="status" class="status">Ready when you are.</div>
    </section>
    <aside class="card">
      <div id="preview" class="preview"><div class="empty"><strong>Your preview</strong>Generated video will appear here.</div></div>
      <div class="meta"><div>Pipeline<b>Storyboard → Generation → Export</b></div><div>Output<b>9:16 MP4</b></div></div>
      <a id="export" class="export" href="#" download>Export MP4</a>
    </aside>
  </div>
</div>
<script>
const form=document.getElementById('create'), topic=document.getElementById('topic'), button=document.getElementById('generate'), status=document.getElementById('status'), preview=document.getElementById('preview'), exportLink=document.getElementById('export');
form.addEventListener('submit', async (e)=>{
  e.preventDefault();
  button.disabled=true; status.className='status'; status.textContent='Starting generation…'; exportLink.style.display='none';
  try {
    const body=new URLSearchParams({topic:topic.value});
    const res=await fetch('/generate',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body});
    const data=await res.json(); if(!res.ok) throw new Error(data.error||'Unable to start generation');
    poll(data.job_id);
  } catch(err) { status.className='status error'; status.textContent=err.message; button.disabled=false; }
});
async function poll(id){
  const res=await fetch('/api/jobs/'+id); const data=await res.json();
  if(data.status==='queued'){status.textContent='Queued…';}
  else if(data.status==='generating'){status.textContent='Generating your scenes…';}
  else if(data.status==='done'){
    status.className='status ok'; status.textContent='Done — your 9:16 video is ready.'; button.disabled=false;
    preview.innerHTML='<video controls playsinline src="'+data.video_url+'"></video>';
    exportLink.href=data.video_url; exportLink.style.display='block'; return;
  } else if(data.status==='failed'){
    status.className='status error'; status.textContent='Generation failed: '+data.error; button.disabled=false; return;
  }
  setTimeout(()=>poll(id),1000);
}
</script>
</body>
</html>"""


def _run_generation(job_id: str, topic: str) -> None:
    try:
        JOBS.update(job_id, status="generating")
        project = Project(topic=topic)
        storyboard = StoryboardContextService().create(project)
        plan = GenerationPlanner().create(storyboard)
        pipeline = GenerationPipelineService(output_dir=settings.output_dir)
        result = pipeline.run(plan)
        video_path = Path(result.video.file_path or "").resolve()
        output_root = settings.output_dir.resolve()
        video_path.relative_to(output_root)
        JOBS.update(job_id, status="done", video=str(video_path.relative_to(output_root)))
    except Exception as exc:  # pragma: no cover - exercised by browser/provider failures
        JOBS.update(job_id, status="failed", error=str(exc))


class StudioHandler(BaseHTTPRequestHandler):
    server_version = "AIContentStudio/0.1"

    def _send(self, body: bytes, content_type: str, status: int = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send(HTML.encode(), "text/html; charset=utf-8")
            return
        if parsed.path.startswith("/api/jobs/"):
            job_id = parsed.path.rsplit("/", 1)[-1]
            job = JOBS.get(job_id)
            if job is None:
                self._send(b'{"error":"Job not found"}', "application/json", HTTPStatus.NOT_FOUND)
                return
            if job.get("video"):
                job["video_url"] = "/output/" + str(job["video"])
            self._send(json.dumps(job).encode(), "application/json")
            return
        if parsed.path.startswith("/output/"):
            relative = parsed.path.removeprefix("/output/")
            root = settings.output_dir.resolve()
            candidate = (root / relative).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                self._send(b"Forbidden", "text/plain; charset=utf-8", HTTPStatus.FORBIDDEN)
                return
            if not candidate.is_file():
                self._send(b"Not found", "text/plain; charset=utf-8", HTTPStatus.NOT_FOUND)
                return
            data = candidate.read_bytes()
            mime = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
            self._send(data, mime)
            return
        self._send(b"Not found", "text/plain; charset=utf-8", HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/generate":
            self._send(b"Not found", "text/plain; charset=utf-8", HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length > 20_000:
            self._send(b'{"error":"Request too large"}', "application/json", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return
        body = self.rfile.read(length).decode("utf-8")
        topic = parse_qs(body).get("topic", [""])[0].strip()
        if not topic:
            self._send(b'{"error":"Topic cannot be empty"}', "application/json", HTTPStatus.BAD_REQUEST)
            return
        job_id = JOBS.create()
        threading.Thread(target=_run_generation, args=(job_id, topic), daemon=True).start()
        self._send(json.dumps({"job_id": job_id}).encode(), "application/json", HTTPStatus.ACCEPTED)

    def log_message(self, format: str, *args: object) -> None:
        return


def serve(host: str = HOST, port: int = PORT) -> None:
    """Start the local MVP browser server."""
    settings.ensure_dirs()
    server = ThreadingHTTPServer((host, port), StudioHandler)
    print(f"AI Content Studio running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping AI Content Studio.")
    finally:
        server.server_close()


if __name__ == "__main__":
    serve()

"""Web UI + JSON API (stdlib only). Run: python -m jobhunt"""
import json
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import generator, pdf, providers, scraper, settings, tracker

UI = (Path(__file__).parent / "ui.html").read_text()
MODES = ("in-person", "remote", "hybrid")


def apply_dir():
    return settings.settings_path().parent / "applications"


def run_search(body):
    cv = body.get("cv", "").strip()
    if not cv:
        raise ValueError("A CV is required.")
    mode = body.get("mode", "remote")
    if mode not in MODES:
        raise ValueError("Invalid work mode.")
    jobs = scraper.find_jobs(cv, body.get("location", ""), mode)
    tracker.record(jobs, mode, body.get("location", ""))
    return jobs


def run_generate(body):
    job = body["job"]
    if not all(isinstance(job.get(k), str) for k in ("title", "company", "location", "description", "url")):
        raise ValueError("Invalid job.")
    provider = providers.get_provider(settings.load())
    result = generator.tailor(provider, body.get("cv", ""), body.get("cover_letter", ""), job)
    result["url"] = job["url"]
    if body.get("auto_apply"):
        d = apply_dir()
        d.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9]+", "-", (job["company"] + "-" + job["title"]).lower())[:60].strip("-")
        p = d / f"{int(time.time())}-{slug}.txt"
        p.write_text(f"Apply at: {job['url']}\n\n{result['cv']}\n\n{generator.MARK}\n\n{result['cover_letter']}\n")
        result["saved_to"] = str(p)
        p.with_name(p.stem + "-cv.pdf").write_bytes(pdf.text_to_pdf(result["cv"]))
        p.with_name(p.stem + "-cover-letter.pdf").write_bytes(pdf.text_to_pdf(result["cover_letter"]))
    return result


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj, ctype="application/json", headers=None):
        data = obj if isinstance(obj, bytes) else obj.encode() if isinstance(obj, str) else json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/":
            self._send(200, UI, "text/html; charset=utf-8")
        elif self.path == "/jobs.csv":
            p = tracker.csv_path()
            data = p.read_text(encoding="utf-8") if p.exists() else ",".join(tracker.FIELDS) + "\n"
            self._send(200, data, "text/csv; charset=utf-8",
                       {"Content-Disposition": 'attachment; filename="jobs.csv"'})
        elif self.path == "/api/settings":
            self._send(200, {"settings": settings.public(settings.load()),
                             "local": providers.detect_local(),
                             "online": [{"name": c.name, "label": c.label, "default_model": c.default_model}
                                        for c in providers.ONLINE]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n > 5_000_000:
                raise ValueError("Request too large.")
            raw = self.rfile.read(n)
            if self.path == "/api/pdf-to-text":
                self._send(200, {"text": pdf.pdf_to_text(raw)})
                return
            body = json.loads(raw or b"{}")
            if self.path == "/api/text-to-pdf":
                self._send(200, pdf.text_to_pdf(str(body.get("text", ""))), "application/pdf")
                return
            if self.path == "/api/settings":
                self._send(200, settings.public(settings.save(body)))
            elif self.path == "/api/search":
                self._send(200, {"jobs": run_search(body)})
            elif self.path == "/api/generate":
                self._send(200, run_generate(body))
            else:
                self._send(404, {"error": "not found"})
        except Exception as e:
            self._send(400, {"error": str(e)})

    def log_message(self, *a):
        pass


def main(host="127.0.0.1", port=8765):
    print(f"JobHuntAI running at http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()

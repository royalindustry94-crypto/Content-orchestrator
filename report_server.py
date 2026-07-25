"""Download server for the M3 audit report Word document."""
from http.server import HTTPServer, BaseHTTPRequestHandler
import os, urllib.parse

DOCX_FILE = "Audit_Report_M3_Content_Orchestrator.docx"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

INDEX_HTML = (
    "<!DOCTYPE html>"
    "<html lang='en'><head><meta charset='UTF-8'>"
    "<meta name='viewport' content='width=device-width,initial-scale=1'>"
    "<title>Download Audit Report</title>"
    "<style>"
    "*{box-sizing:border-box;margin:0;padding:0}"
    "body{font-family:system-ui,sans-serif;background:#f0f4f9;"
    "display:flex;align-items:center;justify-content:center;min-height:100vh}"
    ".card{background:#fff;border-radius:16px;"
    "box-shadow:0 6px 32px rgba(0,0,0,.12);"
    "padding:48px 40px;max-width:420px;width:90%;text-align:center}"
    "h1{font-size:20px;color:#0f3460;margin-bottom:8px;font-weight:700}"
    "p{color:#555;font-size:13px;margin-bottom:32px;line-height:1.5}"
    "a.btn{display:block;background:#0f3460;color:#fff;text-decoration:none;"
    "padding:16px 24px;border-radius:10px;font-size:16px;font-weight:700}"
    ".note{margin-top:16px;font-size:11px;color:#999}"
    "</style></head><body>"
    "<div class='card'>"
    "<h1>M3 Comprehensive Audit Report</h1>"
    "<p>Content Orchestrator - 24 sections, all findings, full evidence.</p>"
    "<a class='btn' href='/download'>Download Word Document (.docx)</a>"
    "<p class='note'>Audit_Report_M3_Content_Orchestrator.docx</p>"
    "</div></body></html>"
).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        if path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(INDEX_HTML)))
            self.end_headers()
            self.wfile.write(INDEX_HTML)

        elif path == "/download":
            fpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), DOCX_FILE)
            try:
                with open(fpath, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", DOCX_MIME)
                self.send_header("Content-Disposition",
                                 'attachment; filename="Audit_Report_M3_Content_Orchestrator.docx"')
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(data)
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"File not found")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Serving on port {port}", flush=True)
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

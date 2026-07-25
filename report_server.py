"""Serves the CEO report files for download."""
from http.server import HTTPServer, BaseHTTPRequestHandler
import os, urllib.parse

FILES = {
    "/report.html":  ("CEO_Report_M3_Audit.html",                          "text/html"),
    "/report.docx":  ("CEO_Report_Content_Orchestrator_M3_Audit.docx",     "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        if path == "/":
            # Show the report directly in the browser
            path = "/report.html"
            FILES["/report.html"] = ("CEO_Report_M3_Audit.html", "text/html")
            fname, mime = FILES[path]
            fpath = os.path.join(os.path.dirname(__file__), fname)
            try:
                with open(fpath, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except FileNotFoundError:
                self.send_error(404)
            return

        if path in FILES:
            fname, mime = FILES[path]
            fpath = os.path.join(os.path.dirname(__file__), fname)
            try:
                with open(fpath, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except FileNotFoundError:
                self.send_error(404)
        else:
            self.send_error(404)

    def _index(self):
        body = (
            "<!DOCTYPE html>"
            "<html><head><meta charset=UTF-8>"
            "<style>"
            "body{font-family:system-ui,sans-serif;display:flex;flex-direction:column;"
            "align-items:center;justify-content:center;min-height:100vh;background:#f4f6f9;margin:0}"
            ".card{background:#fff;border-radius:12px;box-shadow:0 4px 24px rgba(0,0,0,.10);"
            "padding:48px 56px;text-align:center;max-width:480px;width:90%}"
            "h1{color:#1A3A5C;font-size:22px;margin-bottom:8px}"
            "p{color:#555;font-size:14px;margin-bottom:32px}"
            "a.btn{display:block;background:#1A3A5C;color:#fff;text-decoration:none;"
            "padding:14px 28px;border-radius:8px;font-weight:600;font-size:15px;"
            "margin-bottom:12px}"
            "a.btn.secondary{background:#2E6DA4}"
            ".note{font-size:11px;color:#888;margin-top:20px}"
            "</style></head>"
            "<body><div class='card'>"
            "<h1>CEO Report - M3 Audit</h1>"
            "<p>Click a button to download the report.</p>"
            "<a class='btn' href='/report.html'>Download HTML Report</a>"
            "<a class='btn secondary' href='/report.docx'>Download Word (.docx)</a>"
            "<p class='note'>To save HTML as PDF: open in browser, then Ctrl+P, Save as PDF</p>"
            "</div></body></html>"
        ).encode("utf-8")
        body = body  # already bytes
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    port = 5000
    print(f"Serving on port {port}", flush=True)
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

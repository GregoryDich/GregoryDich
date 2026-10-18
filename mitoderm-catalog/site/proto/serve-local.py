#!/usr/bin/env python3
"""Serves site/proto locally the way the prototypes are hosted. The pages are <body> fragments (the host adds the
document shell, and qa/verify-live.cjs does the same), so an .html file without a doctype is wrapped on the fly with
the doctype, UTF-8 and the viewport; img/ and seq/ are served as they are.
usage: python3 serve-local.py [port=8000]  →  http://localhost:8000/vtech-live.html, http://localhost:8000/exocell-mask-3d.html"""
import http.server, os, sys

HEAD = b'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>'
ROOT = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def do_GET(self):
        path = self.translate_path(self.path)
        if not path.endswith('.html') or not os.path.isfile(path):
            return super().do_GET()
        body = open(path, 'rb').read()
        if not body.lstrip()[:9].lower().startswith(b'<!doctype'):
            body = HEAD + body + b'</body></html>'
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f'http://localhost:{port}/vtech-live.html  ·  http://localhost:{port}/exocell-mask-3d.html')
    http.server.ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()

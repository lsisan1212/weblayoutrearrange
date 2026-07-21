#!/usr/bin/env python3
import http.server
import urllib.request
import urllib.parse
import ssl
import socketserver
import os
import traceback
import sys
from datetime import datetime

PORT = 8765
ROOT = os.path.dirname(os.path.abspath(__file__))
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


class ThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """支援並發請求的伺服器"""
    allow_reuse_address = True
    daemon_threads = True


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        ts = datetime.now().strftime('%H:%M:%S')

        if parsed.path == '/proxy':
            qs = urllib.parse.parse_qs(parsed.query)
            target = qs.get('url', [None])[0]
            if not target:
                self.send_error(400, 'missing url')
                print(f"[{ts}] /proxy  ERROR: 缺少 url 參數", flush=True)
                return

            print(f"[{ts}] /proxy  fetch {target[:80]}...", flush=True)
            try:
                req = urllib.request.Request(
                    target,
                    headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
                )
                with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
                    data = r.read()
                    ctype = r.headers.get('Content-Type', 'text/html; charset=utf-8')
                    final_url = r.geturl()
                print(f"[{ts}] /proxy  OK {r.status}  {len(data):,} bytes  (final: {final_url[:70]})", flush=True)
                self.send_response(200)
                self.send_header('Content-Type', ctype)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                print(f"[{ts}] /proxy  FAIL: {e}", flush=True)
                traceback.print_exc(file=sys.stderr)
                msg = ('proxy error: ' + str(e)).encode('utf-8')
                self.send_response(502)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Content-Length', str(len(msg)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(msg)
        else:
            path = self.path.rstrip('?')
            print(f"[{ts}] {path}")
            super().do_GET()


if __name__ == '__main__':
    os.chdir(ROOT)
    print("=" * 50, flush=True)
    print(f"  Web Wrapper Proxy Server", flush=True)
    print(f"  serving: http://127.0.0.1:{PORT}/", flush=True)
    print(f"  root:    {ROOT}", flush=True)
    print("  (keep this Terminal open; press Ctrl+C to stop)", flush=True)
    print("=" * 50, flush=True)
    with ThreadingServer(("127.0.0.1", PORT), Handler) as httpd:
        httpd.serve_forever()

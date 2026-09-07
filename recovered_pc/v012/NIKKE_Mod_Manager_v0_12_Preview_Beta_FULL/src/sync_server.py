from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Any
from urllib.parse import urlparse, parse_qs


class MobileSyncServer:
    """Tiny LAN-only HTTP API used to pair the Windows library with Android.

    The server does not expose mod files. It only exchanges a compact inventory
    snapshot plus tag metadata, and every request requires a random token.
    """

    def __init__(
        self,
        token: str,
        snapshot_provider: Callable[[], dict[str, Any]],
        tag_merge_callback: Callable[[dict[str, Any]], dict[str, Any]],
        on_sync: Callable[[], None] | None = None,
    ) -> None:
        self.token = token
        self.snapshot_provider = snapshot_provider
        self.tag_merge_callback = tag_merge_callback
        self.on_sync = on_sync
        self.httpd: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.host = '0.0.0.0'
        self.port = 0

    def start(self, preferred_port: int = 8765) -> int:
        if self.httpd is not None:
            return self.port

        owner = self

        class Handler(BaseHTTPRequestHandler):
            server_version = 'NIKKEModTrackerSync/1.0'

            def log_message(self, fmt: str, *args) -> None:
                return

            def _cors(self) -> None:
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-NIKKE-Token')
                self.send_header('Cache-Control', 'no-store')

            def _send_json(self, status: int, payload: dict[str, Any]) -> None:
                raw = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
                self.send_response(status)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(raw)))
                self._cors()
                self.end_headers()
                self.wfile.write(raw)

            def _authorized(self) -> bool:
                parsed = urlparse(self.path)
                query_token = (parse_qs(parsed.query).get('token') or [''])[0]
                header_token = self.headers.get('X-NIKKE-Token', '')
                return bool(owner.token) and (query_token == owner.token or header_token == owner.token)

            def do_OPTIONS(self) -> None:  # noqa: N802
                self.send_response(204)
                self._cors()
                self.end_headers()

            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path == '/v1/ping':
                    if not self._authorized():
                        self._send_json(403, {'ok': False, 'error': 'unauthorized'})
                        return
                    self._send_json(200, {'ok': True, 'protocol': 1})
                    return
                if parsed.path != '/v1/snapshot':
                    self._send_json(404, {'ok': False, 'error': 'not_found'})
                    return
                if not self._authorized():
                    self._send_json(403, {'ok': False, 'error': 'unauthorized'})
                    return
                try:
                    payload = owner.snapshot_provider()
                    if owner.on_sync:
                        owner.on_sync()
                    self._send_json(200, payload)
                except Exception as exc:
                    self._send_json(500, {'ok': False, 'error': str(exc)})

            def do_POST(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path != '/v1/sync':
                    self._send_json(404, {'ok': False, 'error': 'not_found'})
                    return
                if not self._authorized():
                    self._send_json(403, {'ok': False, 'error': 'unauthorized'})
                    return
                try:
                    length = min(int(self.headers.get('Content-Length', '0') or 0), 2_000_000)
                    body = self.rfile.read(length) if length else b'{}'
                    incoming = json.loads(body.decode('utf-8'))
                    tags = incoming.get('tags', {}) if isinstance(incoming, dict) else {}
                    owner.tag_merge_callback(tags if isinstance(tags, dict) else {})
                    if owner.on_sync:
                        owner.on_sync()
                    self._send_json(200, owner.snapshot_provider())
                except Exception as exc:
                    self._send_json(400, {'ok': False, 'error': str(exc)})

        last_error: Exception | None = None
        for port in range(preferred_port, preferred_port + 35):
            try:
                self.httpd = ThreadingHTTPServer((self.host, port), Handler)
                self.port = port
                break
            except OSError as exc:
                last_error = exc
                self.httpd = None
        if self.httpd is None:
            raise last_error or OSError('No available LAN sync port')
        self.httpd.daemon_threads = True
        self.thread = threading.Thread(target=self.httpd.serve_forever, name='nikke-mobile-sync', daemon=True)
        self.thread.start()
        return self.port

    def stop(self) -> None:
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
        self.httpd = None
        self.thread = None
        self.port = 0

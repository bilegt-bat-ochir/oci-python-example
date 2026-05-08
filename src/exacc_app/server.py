from __future__ import annotations

from configparser import ConfigParser
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

from .dashboard import render_dashboard
from .models import Inventory
from .oci_gateway import OCIAppError, OCIInventoryClient
from .sample_data import sample_inventory


def list_oci_profiles(config_file: str = "~/.oci/config") -> list[str]:
    config_path = Path(config_file).expanduser()
    if not config_path.exists():
        raise OCIAppError(f"OCI config file was not found at {config_file}.")

    parser = ConfigParser()
    parser.optionxform = str
    parser.read(config_path)

    profiles: list[str] = []
    if parser.defaults():
        profiles.append("DEFAULT")
    profiles.extend(parser.sections())
    return sorted(set(profiles), key=lambda item: (item != "DEFAULT", item.lower()))


def serve_inventory_dashboard(
    inventory: Inventory, *, host: str = "127.0.0.1", port: int = 8000
) -> None:
    html = render_dashboard(inventory).encode("utf-8")
    payload = json.dumps(inventory.to_dict(), ensure_ascii=True, indent=2).encode("utf-8")

    class DashboardHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path in {"/", "/index.html"}:
                self._send(200, "text/html; charset=utf-8", html)
                return
            if parsed.path == "/inventory.json":
                self._send(200, "application/json; charset=utf-8", payload)
                return
            if parsed.path == "/api/profiles":
                self._handle_profiles(parsed.query)
                return
            self._send(404, "text/plain; charset=utf-8", b"Not found")

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/inventory":
                self._handle_inventory_load()
                return
            self._send_json(404, {"error": "Not found"})

        def log_message(self, format: str, *args: object) -> None:
            return

        def _handle_profiles(self, query: str) -> None:
            params = parse_qs(query)
            config_file = params.get("config_file", ["~/.oci/config"])[0]
            try:
                profiles = list_oci_profiles(config_file)
            except OCIAppError as exc:
                self._send_json(400, {"error": str(exc), "profiles": []})
                return
            self._send_json(200, {"profiles": profiles})

        def _handle_inventory_load(self) -> None:
            try:
                data = self._read_json()
                if data.get("sample"):
                    loaded = sample_inventory()
                else:
                    profile = str(data.get("profile", "")).strip()
                    if not profile:
                        raise OCIAppError("OCI profile is required.")
                    client = OCIInventoryClient(
                        profile=profile,
                        config_file=str(data.get("config_file") or "~/.oci/config"),
                        all_regions=bool(data.get("all_regions")),
                    )
                    loaded = client.fetch_inventory()
            except OCIAppError as exc:
                self._send_json(400, {"error": str(exc)})
                return
            except Exception as exc:
                self._send_json(500, {"error": f"Could not load inventory: {exc}"})
                return
            self._send_json(200, loaded.to_dict())

        def _read_json(self) -> Dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length <= 0:
                return {}
            body = self.rfile.read(length)
            return json.loads(body.decode("utf-8"))

        def _send_json(self, status: int, data: Dict[str, Any]) -> None:
            body = json.dumps(data, ensure_ascii=True).encode("utf-8")
            self._send(status, "application/json; charset=utf-8", body)

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"Serving ExaCC dashboard at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped dashboard server")
    finally:
        server.server_close()

"""Persistent Background 2026 F1 Championship Server (HTTP + 20Hz SSE + Team Principal REST API)."""

from __future__ import annotations
import argparse
import json
import mimetypes
import os
import socket
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from sim.championship import ChampionshipWorld

PUBLIC_DIR = Path(__file__).resolve().parent / "public"


class F1HTTPServer(ThreadingHTTPServer):
    # Windows SO_REUSEADDR permits several old simulations to bind the same
    # port and serve different track data. Own the port exclusively instead.
    allow_reuse_address = os.name != 'nt'

    def server_bind(self):
        if os.name == 'nt':
            self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()


class SimulationBroadcaster:
    """Runs the perpetual 20Hz physics & championship loop even when zero browsers are open."""

    def __init__(self, world: ChampionshipWorld):
        self.world = world
        self.cond = threading.Condition()
        self.latest_frame_id: int = 0
        self.latest_json: str = "{}"
        self.running: bool = True
        self.thread = threading.Thread(target=self._run_loop, name="F1SimEngine", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        with self.cond:
            self.cond.notify_all()

    def _run_loop(self) -> None:
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.winmm.timeBeginPeriod(1)
            except Exception:
                pass

        target_dt = 0.05  # 20 Hz physics & broadcast tick
        next_tick_time = time.perf_counter()
        try:
            while self.running:
                now = time.perf_counter()
                if now - next_tick_time > 0.5:
                    next_tick_time = now

                try:
                    self.world.step(target_dt)
                    payload = self.world.build_live_tick_payload()
                    encoded = json.dumps(payload, separators=(",", ":"))
                    with self.cond:
                        self.latest_frame_id += 1
                        self.latest_json = encoded
                        self.cond.notify_all()
                except Exception as exc:
                    sys.stderr.write(f"[F1SimEngine Error] {exc}\n")

                next_tick_time += target_dt
                sleep_for = next_tick_time - time.perf_counter()
                if sleep_for > 0.001:
                    time.sleep(sleep_for)
                else:
                    time.sleep(0.001)
        finally:
            if sys.platform == "win32":
                try:
                    import ctypes
                    ctypes.windll.winmm.timeEndPeriod(1)
                except Exception:
                    pass


class F1RequestHandler(BaseHTTPRequestHandler):
    world: ChampionshipWorld
    broadcaster: SimulationBroadcaster

    def log_message(self, format: str, *args) -> None:
        # Keep console clean (suppress noisy 20Hz/asset logs)
        return

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        # Geographic scenery makes the initial state substantially larger than
        # a live tick. Bound each socket write so it drains in manageable blocks.
        for offset in range(0, len(body), 32768):
            self.wfile.write(body[offset:offset + 32768])

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/stream":
            self._handle_sse()
            return
        if path == "/api/state":
            self._send_json(self.world.build_full_state_payload())
            return
        if path == "/api/tick":
            self._send_json(self.world.build_live_tick_payload())
            return
        if path == "/api/hall_of_fame":
            self._send_json(self.world.get_hall_of_fame_data())
            return

        # Serve static files from public/
        rel = "index.html" if path in ("/", "") else path.lstrip("/")
        target = (PUBLIC_DIR / rel).resolve()
        if not str(target).startswith(str(PUBLIC_DIR.resolve())) or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        ctype, _ = mimetypes.guess_type(str(target))
        if target.suffix == ".js":
            ctype = "application/javascript; charset=utf-8"
        elif target.suffix == ".css":
            ctype = "text/css; charset=utf-8"
        elif target.suffix == ".html":
            ctype = "text/html; charset=utf-8"

        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def _handle_sse(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        last_sent_id = -1
        try:
            while self.broadcaster.running:
                with self.broadcaster.cond:
                    if self.broadcaster.latest_frame_id == last_sent_id:
                        self.broadcaster.cond.wait(timeout=1.0)
                    frame_id = self.broadcaster.latest_frame_id
                    payload = self.broadcaster.latest_json

                if frame_id != last_sent_id:
                    last_sent_id = frame_id
                    chunk = f"data: {payload}\n\n".encode("utf-8")
                    self.wfile.write(chunk)
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            return

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            body = self._read_json_body()
        except Exception:
            self._send_json({"ok": False, "error": "Invalid JSON body."}, 400)
            return

        if path == "/api/select_team":
            res = self.world.select_team(str(body.get("team_id", "")))
        elif path == "/api/upgrade":
            res = self.world.buy_upgrade(str(body.get("dept", "")))
        elif path == "/api/evaluate_trade":
            res = self.world.evaluate_trade(
                str(body.get("my_driver_id", "")),
                str(body.get("target_driver_id", "")),
                float(body.get("cash_offer_m", 0.0)),
            )
        elif path == "/api/execute_trade":
            res = self.world.execute_trade(
                str(body.get("my_driver_id", "")),
                str(body.get("target_driver_id", "")),
                float(body.get("cash_offer_m", 0.0)),
            )
        elif path == "/api/sign_free_agent":
            res = self.world.sign_free_agent(
                str(body.get("release_driver_id", "")),
                str(body.get("free_agent_id", "")),
            )
        elif path == "/api/select_sponsor":
            res = self.world.select_sponsor(str(body.get("sponsor_id", "")))
        elif path == "/api/set_starting_compound":
            res = self.world.set_starting_compound(
                str(body.get("driver_id", "")),
                str(body.get("compound", "")),
            )
        elif path == "/api/pit_wall":
            driver_id = str(body.get("driver_id", ""))
            res = self.world.pit_wall_command(driver_id, body)
        elif path == "/api/speed":
            res = self.world.set_sim_speed(float(body.get("speed", 1.0)))
        elif path == "/api/skip":
            res = self.world.skip_session()
        elif path == "/api/reset":
            team_id = str(body.get("team_id", "williams"))
            start_year = int(body.get("year", body.get("start_year", 2026)))
            res = self.world.reset_career(team_id, start_year=start_year)
        else:
            self._send_json({"ok": False, "error": "Unknown API endpoint."}, 404)
            return

        self._send_json(res, 200 if res.get("ok") else 400)


def main() -> None:
    parser = argparse.ArgumentParser(description="2026 F1 2D Perpetual Championship Simulator Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Bind port (default: 8080)")
    args = parser.parse_args()

    # Bind before loading/saving a career or starting the simulation thread.
    # A duplicate launch must leave the running game and its save untouched.
    try:
        httpd = F1HTTPServer((args.host, args.port), F1RequestHandler)
    except OSError as err:
        # WinError 10048 on Windows, errno 98 (EADDRINUSE) on Linux, errno 48 on macOS
        if getattr(err, "winerror", None) == 10048 or err.errno in (10048, 98, 48):
            print(f"\n==================================================================")
            print(f"  [SERVER LAUNCH ERROR] Port {args.port} is already in use!")
            print(f"==================================================================")
            print(f"  • A server instance is already running at: http://{args.host}:{args.port}")
            print(f"  • To run on an alternative port:")
            print(f"      python server.py --port {args.port + 1}")
            print(f"  • To stop the existing background server process on Windows:")
            print(f"      Stop-Process -Id (Get-NetTCPConnection -LocalPort {args.port}).OwningProcess -Force")
            print(f"==================================================================\n")
            sys.exit(1)
        raise
    os.makedirs(PUBLIC_DIR, exist_ok=True)
    world = ChampionshipWorld()
    broadcaster = SimulationBroadcaster(world)
    broadcaster.start()

    F1RequestHandler.world = world
    F1RequestHandler.broadcaster = broadcaster

    url = f"http://{args.host}:{args.port}"
    print(f"==================================================================")
    print(f"  F1 2026 PERPETUAL 2D CHAMPIONSHIP & TEAM PRINCIPAL SIMULATOR")
    print(f"  Live Server Running Continuously at: {url}")
    print(f"  Season {world.season_year} • Round {world.current_round}/24 ({world.current_track.name})")
    print(f"  State auto-saved to: {world.save_path}")
    print(f"==================================================================")
    sys.stdout.flush()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nSaving championship state and shutting down...")
    finally:
        broadcaster.stop()
        world._save_state()
        httpd.server_close()


if __name__ == "__main__":
    main()


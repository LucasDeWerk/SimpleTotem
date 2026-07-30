"""
SimpleTotem Launcher
Sobe backend → aguarda responder → sobe frontend.
Se qualquer um dos dois encerrar, o outro é encerrado e o launcher fecha.
"""
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path


def _install_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _wait_backend(url: str, timeout: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.4)
    return False


def _encerrar_proc(proc: subprocess.Popen, nome: str) -> None:
    if proc.poll() is not None:
        return
    print(f"[launcher] Encerrando {nome}...", flush=True)
    proc.terminate()
    try:
        proc.wait(timeout=6)
    except subprocess.TimeoutExpired:
        proc.kill()


def main() -> int:
    base        = _install_dir()
    backend_bin = base / "SimpleTotem-backend"
    frontend_bin = base / "SimpleTotem-ui" / "simple-totem"
    log_path    = base / "dados" / "backend.log"

    # ── Backend ───────────────────────────────────────────────────────────────
    if not backend_bin.exists():
        print(f"[launcher] ERRO: backend não encontrado em {backend_bin}", flush=True)
        return 1

    log_file = open(log_path, "a")
    backend_proc = subprocess.Popen(
        [str(backend_bin)],
        stdout=log_file,
        stderr=log_file,
    )
    print(f"[launcher] Backend iniciado (PID {backend_proc.pid})", flush=True)

    if not _wait_backend("http://localhost:8000/empresa/status", timeout=20):
        print("[launcher] Backend não respondeu em 20s — continuando mesmo assim", flush=True)
    else:
        print("[launcher] Backend pronto", flush=True)

    # ── Frontend ──────────────────────────────────────────────────────────────
    if not frontend_bin.exists():
        print(f"[launcher] ERRO: frontend não encontrado em {frontend_bin}", flush=True)
        _encerrar_proc(backend_proc, "Backend")
        return 1

    frontend_proc = subprocess.Popen([str(frontend_bin)], env=os.environ.copy())
    print(f"[launcher] Frontend iniciado (PID {frontend_proc.pid})", flush=True)

    # ── Monitoramento bidirecional ────────────────────────────────────────────
    # Qualquer processo que morrer primeiro dispara o encerramento do outro.
    done  = threading.Event()
    morto = [None]   # nome do processo que saiu primeiro

    def _watch(proc: subprocess.Popen, nome: str) -> None:
        proc.wait()
        if not done.is_set():
            morto[0] = nome
            done.set()

    threading.Thread(target=_watch, args=(backend_proc,  "Backend"),  daemon=True).start()
    threading.Thread(target=_watch, args=(frontend_proc, "Frontend"), daemon=True).start()

    def _sigterm(signum, frame):
        done.set()

    signal.signal(signal.SIGTERM, _sigterm)
    signal.signal(signal.SIGINT,  _sigterm)

    done.wait()

    if morto[0]:
        print(f"[launcher] {morto[0]} encerrou — encerrando o outro...", flush=True)

    _encerrar_proc(frontend_proc, "Frontend")
    _encerrar_proc(backend_proc,  "Backend")

    print("[launcher] Encerrado.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
